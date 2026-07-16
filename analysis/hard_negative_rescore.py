"""Hard-negative (Hamming-1) rescore of the v2 campaign's EXISTING learned models.

Evaluation-only remediation (no ILASP training): for every completed row of the
committed Experiment-1 record (data/exp1_v2/results/*/results_*.csv) this script
scores the row's already-learned program (LEARNED_MODEL_FILENAME, on disk under
artifacts/final_synthetic_v2/train_output/) on an ADVERSARIAL negative surface:
oracle-verified Hamming-1 perturbations of held-out true extensions, instead of
the campaign's sampled non-extension negatives.

Method
------
1. For each (semantics, fold) the row's exact complete-information test split is
   reconstructed with the campaign's own code paths (build_grouped_folds +
   build_grouped_balanced_test from arglas.train_test) and pinned seeds
   (test_sampling_seed=20260312, K=5, 100 items per class), which this script
   verifies reproduce the committed TP_FULL/FP_FULL/TN_FULL/FN_FULL exactly
   (--verify).
2. From each of the 100 held-out POSITIVE test labellings (true extensions on
   unseen frameworks) one Hamming-1 negative is built with the flip_one mutation
   (arglas.generate_ilasp_task.build_synthetic_negative) and kept only if the
   ground-truth stack rejects it (run_ground_truth_with_api returns no model --
   the SAME adjudicator that classifies negatives on the campaign surface, i.e.
   the eval-time equivalent of generate_extensions.verify_extension). Flips that
   are still legal labellings (e.g. removing one argument from an admissible set)
   are counted and skipped, so the hard-negative set carries zero label noise.
   One hard negative per positive => a balanced 100/100 surface per fold.
3. Every succeeded row's learned model is scored on its fold's 100 hard negatives
   with the campaign's learned-model stack (run_learned_model_with_api +
   evaluate_model_sets, eval_match_policy=full_exact_model). The positive side of
   the surface is IDENTICAL to the committed complete-information surface, so
   TP_FULL/FN_FULL are reused from the committed row (reproduced bit-exactly by
   the --verify path) and
       MCC_HARD = mcc(TP_FULL, FP_HARD, TN_HARD, FN_FULL).

Outputs (audit-trail pattern of data/rescore_eval_fixed/)
---------------------------------------------------------
  data/rescore_hard_negatives/hard_neg_sets/<SEM>_fold<i>/   the 100 verified
      Hamming-1 instances (.lp) + manifest.json (source positive, flipped arg,
      flip direction, oracle rejections)
  data/rescore_hard_negatives/results/<config>/results_<k>.csv   per-row rescores
  data/rescore_hard_negatives/summary_by_cell.csv               per grid cell
  data/rescore_hard_negatives/summary_surface_hard.csv          Table-5-shaped
      (q x semantics x f, balanced arm, pooled over completeness)

GRD rows are skipped (out of the paper's scope; GRD is scored on the bare AAF,
so a labelled-negative surface does not apply).

Usage
-----
  python analysis/hard_negative_rescore.py            # full run (~30-60 min)
  python analysis/hard_negative_rescore.py --verify   # + per-semantics row
                                                      #   reproduction check
  python analysis/hard_negative_rescore.py --smoke    # 1 config dir only
"""

import argparse
import csv
import glob
import json
import os
import random
import re
import sys
import time
from collections import defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from arglas.train_test import (  # noqa: E402
    build_grouped_folds,
    build_grouped_balanced_test,
    evaluate_model_sets,
    matthews_corrcoef,
    run_ground_truth_with_api,
    run_learned_model_with_api,
    stable_seed_from_parts,
)
from arglas.generate_ilasp_task import (  # noqa: E402
    build_synthetic_negative,
    parse_lp_instance,
    render_label_facts,
)
from arglas.solver_policy import (  # noqa: E402
    get_background_file,
    get_clingo_args,
    get_completion_rules_enabled,
    get_semantics_entry,
    get_show_predicates,
    load_semantics_config,
)
from arglas.solver_runtime import solve_models  # noqa: E402
from arglas.artifact_paths import resolve_repo_path  # noqa: E402

# Pinned campaign identity (experiments/run_configs/final_synthetic_v2_pos*.json).
TEST_SAMPLING_SEED = 20260312
K_FOLDS = 5
TEST_PER_CLASS = 100
HARD_NEG_SEED_TAG = "hard_negative_rescore"
SEMANTICS = ("STB", "ADM", "CMP", "PRF")  # GRD out of scope (bare-AAF eval)

LABELLED_BASE_DEFAULT = os.path.join(_REPO, "artifacts", "final_synthetic_v2", "labelled")
RESULTS_BASE_DEFAULT = os.path.join(_REPO, "data", "exp1_v2", "results")
OUT_BASE_DEFAULT = os.path.join(_REPO, "data", "rescore_hard_negatives")

OUT_HEADER = [
    "ILASP_TASK_FILENAME", "SEMANTICS", "P_PARTIAL", "NOISE", "RATIO_CONFIG",
    "NFILES_POS", "NFILES_NEG", "ITERATION", "ILASP_TRAIN_SUCCEEDED",
    "LEARNED_MODEL_FILENAME",
    "TEST_FULL_SET_POS", "TEST_FULL_SET_NEG",
    "TP_FULL", "FP_FULL", "TN_FULL", "FN_FULL", "MCC_FULL",
    "HARD_NEG_COUNT", "FP_HARD", "TN_HARD", "MCC_HARD", "ACCURACY_HARD",
    "HARD_EVAL_SECONDS",
]


def build_stacks(semantics_config, sem):
    entry = get_semantics_entry(semantics_config, sem)
    lbg = get_background_file(semantics_config, stage="train_test_learned", semantics=sem)
    gbg = get_background_file(semantics_config, stage="train_test_ground_truth", semantics=sem)
    return {
        "asp": resolve_repo_path(entry["file"]),
        "lbg": resolve_repo_path(lbg) if lbg else None,
        "gbg": resolve_repo_path(gbg) if gbg else None,
        "largs": get_clingo_args(semantics_config, sem, stage="train_test_learned"),
        "gargs": get_clingo_args(semantics_config, sem, stage="train_test_ground_truth"),
        "lcomp": get_completion_rules_enabled(
            semantics_config, stage="train_test_learned", semantics=sem),
        "gcomp": get_completion_rules_enabled(
            semantics_config, stage="train_test_ground_truth", semantics=sem),
        "lshow": get_show_predicates(
            semantics_config, stage="train_test_learned", semantics=sem),
        "gshow": get_show_predicates(
            semantics_config, stage="train_test_ground_truth", semantics=sem),
    }


def gt_rejects(stacks, instance_program):
    """True iff the ground-truth stack has NO model for the injected labelling --
    the exact criterion under which evaluate_model_sets treats an instance as a
    ground-truth negative on the campaign surface."""
    files = [stacks["gbg"], stacks["asp"]] if stacks["gbg"] else [stacks["asp"]]
    models = solve_models(
        files_to_load=files,
        clingo_args=list(stacks["gargs"]),
        completion_rules=stacks["gcomp"],
        additional_program=instance_program,
        show_predicates=list(stacks["gshow"]),
    )
    return len(models) == 0


def full_test_split(pool_dir, fold_index):
    folds = build_grouped_folds(pool_dir, K_FOLDS, fold_seed=TEST_SAMPLING_SEED)
    _, test_aafs = folds[fold_index - 1]
    return build_grouped_balanced_test(
        pool_dir, test_aafs, TEST_PER_CLASS,
        fold_seed=TEST_SAMPLING_SEED, fold_index=fold_index,
    )


def render_instance(af_facts, labels):
    return "\n".join(af_facts + [f"{fact}." for fact in render_label_facts(labels)]) + "\n"


def generate_hard_neg_set(sem, fold, pool_dir, stacks, out_dir):
    """One oracle-verified Hamming-1 negative per held-out positive test item
    (top-up pass with second flips if a positive has no illegal single flip).
    Deterministic given the pinned seeds. Returns manifest dict."""
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    test_files = full_test_split(pool_dir, fold)
    pos_files = [f for f in test_files if "_POS_" in f]
    rng = random.Random(stable_seed_from_parts(
        HARD_NEG_SEED_TAG, TEST_SAMPLING_SEED, sem, fold))

    entries, rejected_legal = [], 0
    used = set()  # (source_file, flipped_arg) already emitted

    def try_source(pf, skip_used):
        nonlocal rejected_legal
        af_facts, labels = parse_lp_instance(os.path.join(pool_dir, pf))
        flippable = sorted(a for a, s in labels.items() if s in ("in", "out"))
        rng.shuffle(flippable)
        for arg in flippable:
            if skip_used and (pf, arg) in used:
                continue
            mutated = dict(labels)
            mutated[arg] = "out" if mutated[arg] == "in" else "in"
            program = render_instance(af_facts, mutated)
            if gt_rejects(stacks, program):
                used.add((pf, arg))
                return {
                    "source_pos": pf,
                    "flipped_arg": arg,
                    "direction": f"{labels[arg]}->{mutated[arg]}",
                    "program": program,
                }
            rejected_legal += 1
        return None

    for pf in pos_files:
        hit = try_source(pf, skip_used=False)
        if hit:
            entries.append(hit)
    # Top-up: some positives may have NO illegal single flip (e.g. admissible
    # sets whose every Hamming-1 neighbour is itself admissible).
    top_up_pool = list(pos_files)
    while len(entries) < len(pos_files) and top_up_pool:
        pf = top_up_pool.pop(0)
        hit = try_source(pf, skip_used=True)
        if hit:
            entries.append(hit)

    files = []
    for i, e in enumerate(entries, 1):
        base = e["source_pos"].replace(".lp", "")
        fname = f"{base}_HNEG_{i}.lp"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(e["program"])
        files.append({
            "file": fname,
            "source_pos": e["source_pos"],
            "flipped_arg": e["flipped_arg"],
            "direction": e["direction"],
        })

    manifest = {
        "semantics": sem,
        "fold": fold,
        "pool": os.path.relpath(pool_dir, _REPO),
        "test_sampling_seed": TEST_SAMPLING_SEED,
        "k_folds": K_FOLDS,
        "test_per_class": TEST_PER_CLASS,
        "hard_neg_seed_tag": HARD_NEG_SEED_TAG,
        "n_positives": len(pos_files),
        "n_hard_negatives": len(files),
        "n_flips_rejected_still_legal": rejected_legal,
        "files": files,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def verify_row_reproduction(sem, pool_dir, stacks, results_base):
    """Recompute one committed row's *_FULL confusion counts from scratch and
    require bit-exact agreement -- proves the split + stack reconstruction."""
    pattern = os.path.join(results_base, f"{sem}_partial_*_ratio_1", "results_*.csv")
    for path in sorted(glob.glob(pattern)):
        with open(path) as fh:
            rows = [r for r in csv.DictReader(fh, delimiter=";")]
        for r in rows:
            if r["ILASP_TRAIN_SUCCEEDED"] != "1":
                continue
            test_files = full_test_split(pool_dir, int(r["ITERATION"]))
            tp = fp = tn = fn = 0
            for tf in test_files:
                p = os.path.join(pool_dir, tf)
                pred = run_learned_model_with_api(
                    r["LEARNED_MODEL_FILENAME"], p, stacks["lbg"],
                    clingo_args=stacks["largs"], completion_rules=stacks["lcomp"],
                    show_predicates=stacks["lshow"])
                gt = run_ground_truth_with_api(
                    stacks["asp"], p, stacks["gbg"],
                    clingo_args=stacks["gargs"], completion_rules=stacks["gcomp"],
                    show_predicates=stacks["gshow"])
                _, a, b, c, d = evaluate_model_sets(pred, gt, "full_exact_model")
                tp += a; fp += b; tn += c; fn += d
            expected = tuple(int(r[k]) for k in ("TP_FULL", "FP_FULL", "TN_FULL", "FN_FULL"))
            if (tp, fp, tn, fn) != expected:
                raise RuntimeError(
                    f"[verify] {sem}: reconstruction mismatch for {path} iter "
                    f"{r['ITERATION']}: got {(tp, fp, tn, fn)}, committed {expected}")
            print(f"[verify] {sem}: {os.path.basename(os.path.dirname(path))} "
                  f"iter {r['ITERATION']} reproduced exactly {(tp, fp, tn, fn)}")
            return
    raise RuntimeError(f"[verify] {sem}: no succeeded row found")


def score_row_on_hard_negs(row, stacks, hard_dir, manifest):
    fp_hard = tn_hard = 0
    t0 = time.perf_counter()
    for entry in manifest["files"]:
        pred = run_learned_model_with_api(
            row["LEARNED_MODEL_FILENAME"],
            os.path.join(hard_dir, entry["file"]),
            stacks["lbg"],
            clingo_args=stacks["largs"],
            completion_rules=stacks["lcomp"],
            show_predicates=stacks["lshow"],
        )
        # Ground truth is NEG by construction (oracle-verified at generation):
        # full_exact_model on a gt-negative instance => FP iff any model predicted.
        _, _, add_fp, add_tn, _ = evaluate_model_sets(pred, [], "full_exact_model")
        fp_hard += add_fp
        tn_hard += add_tn
    return fp_hard, tn_hard, time.perf_counter() - t0


def process_config_dir(cfg_dir, results_base, out_base, labelled_base,
                       semantics_config, stacks_cache, manifest_cache):
    cfg = os.path.basename(cfg_dir)
    sem = cfg.split("_")[0]
    if sem not in SEMANTICS:
        return []
    if sem not in stacks_cache:
        stacks_cache[sem] = build_stacks(semantics_config, sem)
    stacks = stacks_cache[sem]
    pool_dir = os.path.join(labelled_base, f"labelled_{sem}_full")
    out_cfg_dir = os.path.join(out_base, "results", cfg)
    os.makedirs(out_cfg_dir, exist_ok=True)

    emitted = []
    for path in sorted(glob.glob(os.path.join(cfg_dir, "results_*.csv"))):
        out_path = os.path.join(out_cfg_dir, os.path.basename(path))
        with open(path) as fh:
            rows = [r for r in csv.DictReader(fh, delimiter=";")]
        if os.path.exists(out_path):
            with open(out_path) as fh:
                done = sum(1 for _ in csv.DictReader(fh, delimiter=";"))
            if done == len(rows):
                with open(out_path) as fh:
                    emitted.extend(csv.DictReader(fh, delimiter=";"))
                continue
            os.remove(out_path)

        out_rows = []
        for r in rows:
            fold = int(r["ITERATION"])
            key = (sem, fold)
            if key not in manifest_cache:
                hn_dir = os.path.join(out_base, "hard_neg_sets", f"{sem}_fold{fold}")
                manifest_cache[key] = (
                    hn_dir, generate_hard_neg_set(sem, fold, pool_dir, stacks, hn_dir))
            hn_dir, manifest = manifest_cache[key]

            base = {
                "ILASP_TASK_FILENAME": r["ILASP_TASK_FILENAME"],
                "SEMANTICS": sem,
                "P_PARTIAL": r["P_PARTIAL"],
                "NOISE": r["NOISE"],
                "RATIO_CONFIG": cfg.rsplit("ratio_", 1)[-1],
                "NFILES_POS": r["NFILES_POS"],
                "NFILES_NEG": r["NFILES_NEG"],
                "ITERATION": r["ITERATION"],
                "ILASP_TRAIN_SUCCEEDED": r["ILASP_TRAIN_SUCCEEDED"],
                "LEARNED_MODEL_FILENAME": r["LEARNED_MODEL_FILENAME"],
                "TEST_FULL_SET_POS": r["TEST_FULL_SET_POS"],
                "TEST_FULL_SET_NEG": r["TEST_FULL_SET_NEG"],
                "TP_FULL": r["TP_FULL"], "FP_FULL": r["FP_FULL"],
                "TN_FULL": r["TN_FULL"], "FN_FULL": r["FN_FULL"],
                "MCC_FULL": r["MCC_FULL"],
            }
            if r["ILASP_TRAIN_SUCCEEDED"] != "1":
                # Failure taxonomy stays first-class: no fabricated scores.
                base.update({"HARD_NEG_COUNT": "", "FP_HARD": "", "TN_HARD": "",
                             "MCC_HARD": "", "ACCURACY_HARD": "",
                             "HARD_EVAL_SECONDS": ""})
                out_rows.append(base)
                continue

            fp_hard, tn_hard, elapsed = score_row_on_hard_negs(r, stacks, hn_dir, manifest)
            tp_full, fn_full = int(r["TP_FULL"]), int(r["FN_FULL"])
            n_pos = tp_full + fn_full
            n_hard = fp_hard + tn_hard
            mcc_hard = matthews_corrcoef(tp_full, fp_hard, tn_hard, fn_full)
            acc_hard = (tp_full + tn_hard) / (n_pos + n_hard) if (n_pos + n_hard) else 0.0
            base.update({
                "HARD_NEG_COUNT": n_hard,
                "FP_HARD": fp_hard,
                "TN_HARD": tn_hard,
                "MCC_HARD": mcc_hard,
                "ACCURACY_HARD": acc_hard,
                "HARD_EVAL_SECONDS": round(elapsed, 4),
            })
            out_rows.append(base)

        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=OUT_HEADER, delimiter=";")
            w.writeheader()
            w.writerows(out_rows)
        emitted.extend(out_rows)
    print(f"[rescore] {cfg}: done")
    return emitted


def write_summaries(all_rows, out_base):
    ok = [r for r in all_rows if str(r["ILASP_TRAIN_SUCCEEDED"]) == "1"
          and r["MCC_HARD"] != ""]

    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    # Per grid cell (sem, p, q, ratio, f)
    cells = defaultdict(list)
    for r in ok:
        key = (r["SEMANTICS"], r["P_PARTIAL"], r["NOISE"], r["RATIO_CONFIG"],
               r["NFILES_POS"])
        cells[key].append((float(r["MCC_FULL"]), float(r["MCC_HARD"])))
    with open(os.path.join(out_base, "summary_by_cell.csv"), "w", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["SEMANTICS", "P_PARTIAL", "NOISE", "RATIO_CONFIG", "NFILES_POS",
                    "N_RUNS", "MEAN_MCC_FULL", "MEAN_MCC_HARD", "MEAN_DELTA"])
        for key in sorted(cells):
            vals = cells[key]
            mf = mean([v[0] for v in vals]); mh = mean([v[1] for v in vals])
            w.writerow(list(key) + [len(vals), f"{mf:.4f}", f"{mh:.4f}",
                                    f"{mh - mf:+.4f}"])

    # Table-5-shaped: q x sem x f, balanced arm (ratio 1), pooled over p.
    surf = defaultdict(list)
    for r in ok:
        if r["RATIO_CONFIG"] != "1":
            continue
        surf[(r["NOISE"], r["SEMANTICS"], int(r["NFILES_POS"]))].append(
            (float(r["MCC_FULL"]), float(r["MCC_HARD"])))
    with open(os.path.join(out_base, "summary_surface_hard.csv"), "w", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["NOISE", "SEMANTICS", "F", "N_RUNS",
                    "MEAN_MCC_FULL", "MEAN_MCC_HARD", "MEAN_DELTA"])
        for key in sorted(surf, key=lambda k: (float(k[0]), k[1], k[2])):
            vals = surf[key]
            mf = mean([v[0] for v in vals]); mh = mean([v[1] for v in vals])
            w.writerow(list(key) + [len(vals), f"{mf:.4f}", f"{mh:.4f}",
                                    f"{mh - mf:+.4f}"])
    print(f"[summary] {len(ok)} scored rows -> summary_by_cell.csv, "
          f"summary_surface_hard.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-base", default=RESULTS_BASE_DEFAULT)
    ap.add_argument("--labelled-base", default=LABELLED_BASE_DEFAULT)
    ap.add_argument("--out-base", default=OUT_BASE_DEFAULT)
    ap.add_argument("--verify", action="store_true",
                    help="Recompute one committed row per semantics from scratch "
                         "and require bit-exact *_FULL agreement before rescoring.")
    ap.add_argument("--smoke", action="store_true",
                    help="Process a single config dir per semantics (dev check).")
    args = ap.parse_args()

    semantics_config = load_semantics_config(resolve_repo_path("semantics_config.json"))
    stacks_cache, manifest_cache = {}, {}

    if args.verify:
        for sem in SEMANTICS:
            stacks_cache[sem] = build_stacks(semantics_config, sem)
            verify_row_reproduction(
                sem, os.path.join(args.labelled_base, f"labelled_{sem}_full"),
                stacks_cache[sem], args.results_base)

    cfg_dirs = sorted(d for d in glob.glob(os.path.join(args.results_base, "*"))
                      if os.path.isdir(d))
    if args.smoke:
        seen = set(); keep = []
        for d in cfg_dirs:
            sem = os.path.basename(d).split("_")[0]
            if sem in SEMANTICS and sem not in seen:
                seen.add(sem); keep.append(d)
        cfg_dirs = keep

    os.makedirs(args.out_base, exist_ok=True)
    t0 = time.time()
    all_rows = []
    for d in cfg_dirs:
        all_rows.extend(process_config_dir(
            d, args.results_base, args.out_base, args.labelled_base,
            semantics_config, stacks_cache, manifest_cache))
    write_summaries(all_rows, args.out_base)
    n_scored = sum(1 for r in all_rows
                   if str(r["ILASP_TRAIN_SUCCEEDED"]) == "1" and r["MCC_HARD"] != "")
    print(f"[done] {len(all_rows)} rows ({n_scored} scored) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
