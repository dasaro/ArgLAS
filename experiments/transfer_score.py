#!/usr/bin/env python3
"""Tier-1 cross-pool transfer scoring (evaluation-only; no new ILASP runs).

Answers the generator-breadth objection empirically: does a program learned on one
AAF pool classify complete-information labellings drawn from a DIFFERENT pool
correctly? For exactly-recovered programs cross-topology transfer at MCC 1.0 is
entailed by the equivalence theorems; this driver verifies that for the
campaign-learned presentations and measures how far noisy-cell hypotheses degrade
off-distribution.

Inputs (all committed / already on disk):
  - committed results CSVs: data/exp1_v2/results, data/v3_{sparse,self,large}/results
    (anchor slice: STB/ADM/CMP/PRF x p in {1.0,0.5} x q in {0.0,0.1} x f in {20,60}
     x 5 folds; LEARNED_MODEL_FILENAME maps each run to its learned model)
  - learned models: artifacts/final_synthetic_v2 + artifacts/final_synthetic_v3_*
    (local-only, gitignored)
  - committed AAF pools: data/exp1_v2/aafs, data/v3_{sparse,self,large}/aafs

Per (target pool, semantics) a fixed complete-information 80+80 test surface is
built from the TARGET pool's committed AAFs via the ASPARTIX oracle (same
label_generation runtime as the campaign, p=1.0, deterministic seeds), written to
data/transfer/surfaces/. Every successful anchor run's model is then scored on
that surface with the exact campaign scorer (train_test.run_learned_model_with_api /
run_ground_truth_with_api / evaluate_model_sets, full_exact_model; PRF gets the
eval-time domRec subset-maximality symmetrically via semantics_config, exactly as
the harness does).

Directions: dense->{sparse,self,large}, each v3 pool->dense, plus same-pool
controls (source surface == target surface; NOTE controls draw from the whole
pool, so they can overlap the model's training AAFs -- calibration only, use the
stored fold-disjoint MCC_FULL as the honest within-pool reference).

Usage:
  python3 experiments/transfer_score.py --validate   # reproduce stored *_FULL counts
  python3 experiments/transfer_score.py              # full run (resumable)
Outputs: data/transfer/transfer_scores.csv, data/transfer/transfer_summary.csv,
         data/transfer/surfaces/ (+ manifest.json).
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(_os.sys.argv[0] if __name__ == "__main__" else __file__)), "..")))
import argparse
import csv
import glob
import json
import os
import random
import sys
import time
from multiprocessing import Pool

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, REPO)

from arglas import train_test as T
from arglas import generate_extensions as GE
from arglas.solver_runtime import build_semantics_runtime
from arglas.solver_policy import load_semantics_config

SEMS = ("ADM", "CMP", "STB", "PRF")
P_TOKENS = {"1_0": 1.0, "0_5": 0.5}
Q_TOKENS = {"0_0": 0.0, "0_1": 0.1}
F_VALUES = {"20", "60"}
PER_CLASS = 80
SURFACE_SEED_BASE = 20260715  # fixed, independent of campaign seeds
FOLD_SEED = 20260312          # campaign test_sampling_seed (validation mode only)

POOLS = {
    "dense": {"data": "data/exp1_v2", "artifacts": "artifacts/final_synthetic_v2",
              "stored_per_class": 100},
    "sparse": {"data": "data/v3_sparse", "artifacts": "artifacts/final_synthetic_v3_sparse",
               "stored_per_class": 80},
    "self": {"data": "data/v3_self", "artifacts": "artifacts/final_synthetic_v3_self",
             "stored_per_class": 30},
    "large": {"data": "data/v3_large", "artifacts": "artifacts/final_synthetic_v3_large",
              "stored_per_class": 60},
}
DIRECTIONS = [
    ("dense", "dense"), ("dense", "sparse"), ("dense", "self"), ("dense", "large"),
    ("sparse", "sparse"), ("sparse", "dense"),
    ("self", "self"), ("self", "dense"),
    ("large", "large"), ("large", "dense"),
]

OUT_DIR = os.path.join(REPO, "data", "transfer")
SURFACE_DIR = os.path.join(OUT_DIR, "surfaces")
SCORES_CSV = os.path.join(OUT_DIR, "transfer_scores.csv")
SUMMARY_CSV = os.path.join(OUT_DIR, "transfer_summary.csv")

SCORES_HEADER = [
    "SOURCE_POOL", "TARGET_POOL", "SEMANTICS", "P_PARTIAL", "NOISE", "NFILES_POS",
    "FOLD", "ILASP_TRAIN_SUCCEEDED", "STORED_MCC", "STORED_MCC_FULL",
    "SURFACE_POS", "SURFACE_NEG", "TP", "FP", "TN", "FN", "MCC", "ACCURACY",
    "LEARNED_MODEL_FILENAME", "SCORE_SECONDS",
]


# ----------------------------------------------------------------------------
# Anchor-slice rows from the committed results CSVs
# ----------------------------------------------------------------------------

def load_anchor_rows():
    rows = []
    for pool, cfg in POOLS.items():
        rdir = os.path.join(REPO, cfg["data"], "results")
        for sem in SEMS:
            for ptok, p in P_TOKENS.items():
                for qtok, q in Q_TOKENS.items():
                    cell = f"{sem}_partial_{ptok}_noise_{qtok}_ratio_1"
                    cdir = os.path.join(rdir, cell)
                    if not os.path.isdir(cdir):
                        raise FileNotFoundError(f"Missing anchor cell {cdir}")
                    for path in sorted(glob.glob(os.path.join(cdir, "results_*.csv"))):
                        for r in csv.DictReader(open(path), delimiter=";"):
                            if r["NFILES_POS"] not in F_VALUES:
                                continue
                            rows.append({
                                "pool": pool, "sem": sem, "p": p, "q": q,
                                "f": int(r["NFILES_POS"]),
                                "fold": int(r["ITERATION"]),
                                "model": r["LEARNED_MODEL_FILENAME"],
                                "succeeded": r["ILASP_TRAIN_SUCCEEDED"] in ("1", "True", "true"),
                                "stored_mcc": r["MCC"],
                                "stored_mcc_full": r["MCC_FULL"],
                                "stored_full": {k: r.get(f"{k}_FULL", "") for k in ("TP", "FP", "TN", "FN")},
                                "key": f"{pool}|{sem}|{p}|{q}|{r['NFILES_POS']}|{r['ITERATION']}",
                            })
    return rows


# ----------------------------------------------------------------------------
# Complete-information transfer surfaces (80 POS + 80 NEG per pool x semantics)
# ----------------------------------------------------------------------------

def build_surface(pool, sem, cfg_json):
    """Oracle-label the pool's committed AAFs at p=1.0 (campaign label_generation
    runtime, allow_empty convention) and keep a deterministic 80 POS + 80 NEG
    sample; at most one POS and one NEG per source AAF on the first pass (a
    second pass tops up POS with a distinct extension per AAF if the pool has
    fewer than 80 AAFs admitting an extension, e.g. STB on the 180-AAF large
    pool). Writes labelled .lp files to data/transfer/surfaces/<pool>/<sem>/."""
    aaf_dir = os.path.join(REPO, POOLS[pool]["data"], "aafs")
    out_dir = os.path.join(SURFACE_DIR, pool, sem)
    os.makedirs(out_dir, exist_ok=True)
    runtime = build_semantics_runtime(cfg_json, sem, stage="label_generation")

    files = sorted(f for f in os.listdir(aaf_dir) if f.endswith(".lp"))
    order_rng = random.Random(T.stable_seed_from_parts(
        "transfer_surface_order", SURFACE_SEED_BASE, pool, sem))
    order_rng.shuffle(files)

    pos_items, neg_items = [], []
    seen_pos = {}  # aaf filename -> set of chosen extension signatures
    passes = 0
    while (len(pos_items) < PER_CLASS or len(neg_items) < PER_CLASS) and passes < 3:
        passes += 1
        for fname in files:
            if len(pos_items) >= PER_CLASS and len(neg_items) >= PER_CLASS:
                break
            stem = fname[:-3]
            input_path = os.path.join(aaf_dir, fname)
            seed = T.stable_seed_from_parts(
                "transfer_surface_item", SURFACE_SEED_BASE, pool, sem, fname, passes)
            random.seed(seed)  # GE helpers use the global RNG
            args, atts = GE.extract_arguments_attacks(input_path)
            models = GE.run_clingo(input_path, runtime)

            if len(pos_items) < PER_CLASS and models:
                chosen_sigs = seen_pos.setdefault(fname, set())
                candidates = []
                for m in models:
                    sig = tuple(sorted(str(a) for a in m))
                    if sig not in chosen_sigs:
                        candidates.append((sig, m))
                if candidates:
                    sig, model = candidates[random.randrange(len(candidates))]
                    chosen_sigs.add(sig)
                    ext_atoms = [f"{a}." for a in model]
                    k = sum(1 for it in pos_items if it[0] == stem) + 1
                    out_name = f"{stem}_{sem}_POS_{k}.lp"
                    with open(os.path.join(out_dir, out_name), "w") as f:
                        f.write("\n".join(args + atts + ext_atoms) + "\n")
                    pos_items.append((stem, out_name))

            if len(neg_items) < PER_CLASS and not any(it[0] == stem for it in neg_items):
                negs = GE.generate_negative_examples(
                    input_path, runtime, args, p_partial=1.0,
                    attempts=5, precomputed_models=models)
                if negs:
                    out_name = f"{stem}_{sem}_NEG_1.lp"
                    with open(os.path.join(out_dir, out_name), "w") as f:
                        f.write("\n".join(args + atts + negs[0]) + "\n")
                    neg_items.append((stem, out_name))

    if len(pos_items) < PER_CLASS or len(neg_items) < PER_CLASS:
        raise RuntimeError(
            f"Surface {pool}/{sem}: only POS={len(pos_items)} NEG={len(neg_items)} "
            f"(need {PER_CLASS} each) after {passes} passes.")
    return {
        "pool": pool, "semantics": sem, "aaf_dir": os.path.relpath(aaf_dir, REPO),
        "seed_base": SURFACE_SEED_BASE, "per_class": PER_CLASS,
        "pos_files": sorted(n for _, n in pos_items),
        "neg_files": sorted(n for _, n in neg_items),
    }


def ensure_surfaces():
    manifest_path = os.path.join(SURFACE_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path))
        ok = all(
            f"{pool}/{sem}" in manifest
            and all(os.path.exists(os.path.join(SURFACE_DIR, pool, sem, n))
                    for n in manifest[f"{pool}/{sem}"]["pos_files"] + manifest[f"{pool}/{sem}"]["neg_files"])
            for pool in POOLS for sem in SEMS)
        if ok:
            print("[surfaces] complete manifest found; reusing.", flush=True)
            return manifest
    cfg_json = load_semantics_config(T.resolve_repo_path("config/semantics_config.json"))
    manifest = {}
    for pool in POOLS:
        for sem in SEMS:
            t0 = time.time()
            manifest[f"{pool}/{sem}"] = build_surface(pool, sem, cfg_json)
            print(f"[surfaces] {pool}/{sem}: 80+80 built in {time.time()-t0:.1f}s", flush=True)
    os.makedirs(SURFACE_DIR, exist_ok=True)
    json.dump(manifest, open(manifest_path + ".tmp", "w"), indent=1)
    os.replace(manifest_path + ".tmp", manifest_path)
    return manifest


# ----------------------------------------------------------------------------
# Scoring (exact campaign scorer; per-worker runtime + ground-truth caches)
# ----------------------------------------------------------------------------

def make_runtimes():
    cfgp = T.resolve_repo_path("config/semantics_config.json")
    cfg = T.load_semantics_config(cfgp)
    rt = {}
    for sem in SEMS:
        entry = T.get_semantics_entry(cfg, sem)
        rt[sem] = {
            "asp_file": T.resolve_repo_path(entry["file"]),
            "l_args": T.get_clingo_args(cfg, sem, stage="train_test_learned"),
            "g_args": T.get_clingo_args(cfg, sem, stage="train_test_ground_truth"),
            "l_bg": (lambda v: T.resolve_repo_path(v) if v else None)(
                T.get_background_file(cfg, stage="train_test_learned", semantics=sem)),
            "g_bg": (lambda v: T.resolve_repo_path(v) if v else None)(
                T.get_background_file(cfg, stage="train_test_ground_truth", semantics=sem)),
            "l_comp": T.get_completion_rules_enabled(cfg, stage="train_test_learned", semantics=sem),
            "g_comp": T.get_completion_rules_enabled(cfg, stage="train_test_ground_truth", semantics=sem),
            "l_show": T.get_show_predicates(cfg, stage="train_test_learned", semantics=sem),
            "g_show": T.get_show_predicates(cfg, stage="train_test_ground_truth", semantics=sem),
            "bare": T.get_eval_on_bare_aaf(cfg, sem),
        }
        assert not rt[sem]["bare"], f"bare-AAF eval unexpected for {sem}"
    return rt


_RT = None
_GT_CACHE = {}


def _score(model_file, input_dir, test_files, rt, gt_key_prefix):
    tp = fp = tn = fn = 0
    for tf in test_files:
        test_path = os.path.join(input_dir, tf)
        pred = T.run_learned_model_with_api(
            model_file, test_path, rt["l_bg"], clingo_args=rt["l_args"],
            completion_rules=rt["l_comp"], show_predicates=rt["l_show"])
        gt_key = (gt_key_prefix, tf)
        if gt_key not in _GT_CACHE:
            _GT_CACHE[gt_key] = T.run_ground_truth_with_api(
                rt["asp_file"], test_path, rt["g_bg"], clingo_args=rt["g_args"],
                completion_rules=rt["g_comp"], show_predicates=rt["g_show"])
        gt = _GT_CACHE[gt_key]
        _, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp += a; fp += b; tn += c; fn += d
    return tp, fp, tn, fn


def score_unit(unit):
    """unit = (row, target_pool, surface_files). Returns a SCORES_HEADER row."""
    global _RT
    if _RT is None:
        _RT = make_runtimes()
    row, target, surface_files = unit
    rt = _RT[row["sem"]]
    t0 = time.time()
    input_dir = os.path.join(SURFACE_DIR, target, row["sem"])
    tp, fp, tn, fn = _score(row["model"], input_dir, surface_files, rt,
                            gt_key_prefix=(target, row["sem"]))
    n_pos = sum(1 for x in surface_files if "_POS_" in x)
    n_neg = len(surface_files) - n_pos
    mcc = T.matthews_corrcoef(tp, fp, tn, fn)
    acc = T.safe_div(tp + tn, tp + fp + tn + fn)
    return [row["pool"], target, row["sem"], row["p"], row["q"], row["f"], row["fold"],
            1, row["stored_mcc"], row["stored_mcc_full"], n_pos, n_neg,
            tp, fp, tn, fn, round(mcc, 6), round(acc, 6),
            row["model"], round(time.time() - t0, 2)]


# ----------------------------------------------------------------------------
# Validation: reproduce the stored *_FULL confusion counts with this plumbing
# ----------------------------------------------------------------------------

def validate(rows, workers):
    """For one successful p=0.5 row per (pool x semantics), rebuild the campaign's
    complete-information fold test set from the local artifacts and check that this
    script's scorer reproduces the stored TP_FULL/FP_FULL/TN_FULL/FN_FULL exactly."""
    global _RT
    if _RT is None:
        _RT = make_runtimes()
    picks, seen = [], set()
    for r in rows:
        if not r["succeeded"] or r["p"] != 0.5:
            continue
        k = (r["pool"], r["sem"])
        if k in seen:
            continue
        seen.add(k)
        picks.append(r)
    n_bad = 0
    for r in picks:
        art = os.path.join(REPO, POOLS[r["pool"]]["artifacts"], "labelled")
        matched_dir = os.path.join(art, f"labelled_{r['sem']}_partial_{r['p']}")
        full_dir = os.path.join(art, f"labelled_{r['sem']}_full")
        per_class = POOLS[r["pool"]]["stored_per_class"]
        folds = T.build_grouped_folds(matched_dir, 5, fold_seed=FOLD_SEED)
        test_aafs = folds[r["fold"] - 1][1]
        tfs = T.build_grouped_balanced_test(full_dir, test_aafs, per_class,
                                            fold_seed=FOLD_SEED, fold_index=r["fold"])
        tp, fp, tn, fn = _score(r["model"], full_dir, tfs, _RT[r["sem"]],
                                gt_key_prefix=("validate", r["pool"], r["sem"], r["fold"]))
        stored = {k2: int(v) for k2, v in r["stored_full"].items() if v != ""}
        got = {"TP": tp, "FP": fp, "TN": tn, "FN": fn}
        ok = all(got[k2] == stored.get(k2) for k2 in got)
        n_bad += 0 if ok else 1
        print(f"[validate] {r['key']}: stored={stored} got={got} -> "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
    print(f"[validate] {len(picks) - n_bad}/{len(picks)} rows reproduce stored *_FULL counts.",
          flush=True)
    return n_bad == 0


# ----------------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------------

def write_summary(score_rows):
    """Mean transfer MCC per (source, target, semantics, p, q, f) over folds."""
    groups = {}
    for r in score_rows:
        key = (r["SOURCE_POOL"], r["TARGET_POOL"], r["SEMANTICS"],
               r["P_PARTIAL"], r["NOISE"], r["NFILES_POS"])
        groups.setdefault(key, []).append(r)
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["SOURCE_POOL", "TARGET_POOL", "SEMANTICS", "P_PARTIAL", "NOISE",
                    "NFILES_POS", "N_FOLDS_SCORED", "MEAN_TRANSFER_MCC", "MIN_TRANSFER_MCC",
                    "MEAN_STORED_MCC_FULL", "MEAN_TRANSFER_MINUS_STORED_FULL"])
        for key in sorted(groups):
            rs = groups[key]
            mccs = [float(r["MCC"]) for r in rs]
            stored = [float(r["STORED_MCC_FULL"]) for r in rs if r["STORED_MCC_FULL"] != ""]
            mean_mcc = sum(mccs) / len(mccs)
            mean_stored = sum(stored) / len(stored) if stored else ""
            delta = (mean_mcc - mean_stored) if stored else ""
            w.writerow(list(key) + [len(rs), round(mean_mcc, 6), round(min(mccs), 6),
                                    round(mean_stored, 6) if stored != "" else "",
                                    round(delta, 6) if delta != "" else ""])
    print(f"[summary] wrote {SUMMARY_CSV}", flush=True)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true",
                    help="reproduce stored *_FULL counts for one row per pool x semantics")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = load_anchor_rows()
    n_fail = sum(1 for r in rows if not r["succeeded"])
    print(f"[anchor] {len(rows)} rows loaded ({n_fail} train-failures excluded from scoring)",
          flush=True)
    assert len(rows) == 640, f"expected 640 anchor rows, got {len(rows)}"

    if a.validate:
        sys.exit(0 if validate(rows, a.workers) else 1)

    manifest = ensure_surfaces()

    # Failure rows: emitted once with empty metrics (failure taxonomy stays first-class).
    done = set()
    existing = []
    if os.path.exists(SCORES_CSV):
        for r in csv.DictReader(open(SCORES_CSV), delimiter=";"):
            existing.append(r)
            done.add((r["SOURCE_POOL"], r["TARGET_POOL"], r["SEMANTICS"], r["P_PARTIAL"],
                      r["NOISE"], r["NFILES_POS"], r["FOLD"]))
        print(f"[resume] {len(existing)} rows already in {SCORES_CSV}", flush=True)
    else:
        with open(SCORES_CSV, "w", newline="") as f:
            csv.writer(f, delimiter=";").writerow(SCORES_HEADER)

    units, fail_rows = [], []
    for src, tgt in DIRECTIONS:
        for row in rows:
            if row["pool"] != src:
                continue
            key = (src, tgt, row["sem"], str(row["p"]), str(row["q"]), str(row["f"]),
                   str(row["fold"]))
            if key in done:
                continue
            if not row["succeeded"]:
                fail_rows.append([src, tgt, row["sem"], row["p"], row["q"], row["f"],
                                  row["fold"], 0, row["stored_mcc"], row["stored_mcc_full"],
                                  "", "", "", "", "", "", "", "", row["model"], ""])
                continue
            m = manifest[f"{tgt}/{row['sem']}"]
            units.append((row, tgt, sorted(m["pos_files"] + m["neg_files"])))

    if fail_rows:
        with open(SCORES_CSV, "a", newline="") as f:
            w = csv.writer(f, delimiter=";")
            for fr in fail_rows:
                w.writerow(fr)
        print(f"[failures] recorded {len(fail_rows)} unscored train-failure rows", flush=True)

    print(f"[score] {len(units)} (model x target-surface) units to score", flush=True)
    t0 = time.time()
    n = 0
    with Pool(a.workers) as pool:
        with open(SCORES_CSV, "a", newline="") as f:
            w = csv.writer(f, delimiter=";")
            for out in pool.imap_unordered(score_unit, units, chunksize=4):
                w.writerow(out)
                f.flush()
                n += 1
                if n % 50 == 0 or n == len(units):
                    print(f"[score] {n}/{len(units)} done ({time.time()-t0:.0f}s)", flush=True)

    all_rows = [r for r in csv.DictReader(open(SCORES_CSV), delimiter=";")
                if r["ILASP_TRAIN_SUCCEEDED"] == "1"]
    write_summary(all_rows)
    print(f"[done] {len(all_rows)} scored rows total in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
