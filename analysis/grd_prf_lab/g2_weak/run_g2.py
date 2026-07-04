"""Route G2 main experiment.

Protocol: grouped 5-fold CV over the 500 campaign AAFs via
train_test.build_grouped_folds (fold_seed=0, identical convention to the
corrected campaign). Per fold and per f in {10, 20}:

  TRAIN: sample f source-AAFs from the fold's train AAFs (seeded with
  train_test.stable_seed_from_parts). ILASP task =
    background : fixed 3-valued complete-labelling core (core_complete.lp)
    bias       : #modeo(1, in(var(arg))). #modeo(1, out(var(arg))).
                 #maxv(2). #weight(1). #maxp(1).
    examples   : one #pos per complete labelling of each train AAF, with the
                 FULL labelling as inclusions and its complement (over in/out
                 atoms of all args) as exclusions -> each example pins exactly
                 one answer set of B ∪ context;
                 #brave_ordering(g, c, <) for the grounded labelling g vs
                 every non-grounded complete labelling c of the same AAF.
  Variants: V1 tight  (--max-wc-length=1), V2 default (no wc-length flag).

  TEST: balanced hold-out from the fold's TEST AAFs only, 50 POS + 50 NEG via
  train_test.build_grouped_balanced_test (fold_seed=0). Two readings:
    (a) verifier (per labelled instance, gives MCC): with L = instance label,
        pred_models = [M in OPT(core + learned + bare AAF) if M == L],
        gt_models   = [M in grounded.lp(bare AAF) if M == L],
        scored by train_test.evaluate_model_sets("full_exact_model").
    (b) pipeline bare-AAF exact (per unique test AAF, gives accuracy):
        OPT(core + learned + bare) == grounded.lp(bare) as projected model
        sets (this is the GRD eval_on_bare_aaf + full_exact_model convention;
        it has no negative class, so MCC degenerates there by construction).
  OPT = optimal answer sets: clingo -n 0 --opt-mode=optN, keep
  optimality_proven models (all models if the program has no weak constraint).
"""
import json
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude/analysis/grd_prf_lab/g2_weak")
import g2lib as G
T = G.T

K = 5
F_VALUES = [10, 20]
TEST_PER_CLASS = 50
FOLD_SEED = 0
ILASP_TIMEOUT = 600

BIAS = (
    "#modeo(1, in(var(arg))).\n"
    "#modeo(1, out(var(arg))).\n"
    "#maxv(2).\n"
    "#weight(1).\n"
    "#maxp(1).\n"
)
VARIANTS = {
    "V1_tight": ["--max-wc-length=1"],
    "V2_default": [],
}


def labelling_example(ex_id, labels, arglist, context_facts):
    universe = {f"{p}({a})" for a in arglist for p in ("in", "out")}
    incl = sorted(labels)
    excl = sorted(universe - set(labels))
    ctx = " ".join(f"{f}." if not f.endswith(".") else f for f in context_facts)
    return f"#pos({ex_id}, {{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx}}})."


def build_task(train_aafs, task_path):
    """Returns (n_examples, n_orderings)."""
    lines = [open(G.CORE_FILE).read(), BIAS]
    n_ex = n_ord = 0
    for size, idx in sorted(train_aafs):
        bare = G.read_bare_aaf(os.path.join(G.AAF_DIR, f"aaf_{size}_{idx}.lp"))
        arglist = G.args_of(bare)
        ctx = [ln.strip() for ln in bare.splitlines()]
        gt = G.grounded_gt_models(bare)
        assert len(gt) == 1
        g_lab = frozenset(gt[0])
        comp = [frozenset(m) for m in G.complete_labellings(bare)]
        g_id = f"g_{size}_{idx}"
        lines.append(labelling_example(g_id, g_lab, arglist, ctx))
        n_ex += 1
        k = 0
        for m in sorted(comp, key=sorted):
            if m == g_lab:
                continue
            k += 1
            c_id = f"c_{size}_{idx}_{k}"
            lines.append(labelling_example(c_id, m, arglist, ctx))
            lines.append(f"#brave_ordering({g_id}, {c_id}, <).")
            n_ex += 1
            n_ord += 1
    with open(task_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return n_ex, n_ord


def run_ilasp(task_path, extra_flags):
    cmd = ["timeout", str(ILASP_TIMEOUT), "ILASP", "--version=4"] + extra_flags + [task_path]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    out = proc.stdout + proc.stderr
    timed_out = proc.returncode == 124
    unsat = T._final_verdict_unsat(out)
    rules = [] if (timed_out or unsat) else G.extract_learned_wcs(out)
    return rules, dt, timed_out, unsat, out


def evaluate(learned_rules, test_files, opt_cache, gt_cache):
    hyp = "\n".join(learned_rules)
    tp = fp = tn = fn = 0
    pos_gt_mismatch = 0
    aaf_exact = {}
    per_class = {"POS": [0, 0], "NEG": [0, 0]}  # [correct, total]
    for tf in test_files:
        path = os.path.join(G.POOL_DIR, tf)
        bare_lines, labels = G.parse_instance(path)
        bare = "\n".join(bare_lines)
        gid = T.aaf_group_id(tf)
        if gid not in gt_cache:
            gt_cache[gid] = G.grounded_gt_models(bare)
        if gid not in opt_cache:
            opt_cache[gid] = G.solve_optimal_models(
                [G.CORE_FILE], additional_program=bare + "\n" + hyp)
        gt, opt = gt_cache[gid], opt_cache[gid]
        pred_models = [m for m in opt if m == labels]
        gt_models = [m for m in gt if m == labels]
        is_pos_file = "_POS_" in tf
        if bool(gt_models) != is_pos_file:
            pos_gt_mismatch += 1
        correct, a, b, c, d = T.evaluate_model_sets(pred_models, gt_models,
                                                    "full_exact_model")
        tp, fp, tn, fn = tp + a, fp + b, tn + c, fn + d
        cls = "POS" if is_pos_file else "NEG"
        per_class[cls][0] += int(correct)
        per_class[cls][1] += 1
        if gid not in aaf_exact:
            aaf_exact[gid] = (T.canonical_model_set(opt) == T.canonical_model_set(gt))
    n_aaf = len(aaf_exact)
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "mcc": T.matthews_corrcoef(tp, fp, tn, fn),
        "acc": (tp + tn) / max(1, tp + fp + tn + fn),
        "pos_correct": per_class["POS"], "neg_correct": per_class["NEG"],
        "bare_aaf_exact_acc": sum(aaf_exact.values()) / max(1, n_aaf),
        "bare_aaf_n": n_aaf,
        "pos_gt_mismatch": pos_gt_mismatch,
    }


def main():
    folds = T.build_grouped_folds(G.POOL_DIR, K, fold_seed=FOLD_SEED)
    results = []
    for fold_index in range(1, K + 1):
        train_aafs, test_aafs = folds[fold_index - 1]
        test_files = T.build_grouped_balanced_test(
            G.POOL_DIR, test_aafs, TEST_PER_CLASS,
            fold_seed=FOLD_SEED, fold_index=fold_index)
        gt_cache = {}
        for f in F_VALUES:
            seed = T.stable_seed_from_parts("g2_task", FOLD_SEED, fold_index, f)
            rng = random.Random(seed)
            sampled = rng.sample(sorted(train_aafs), f)
            task_path = os.path.join(G.WORK, "tasks",
                                     f"g2_fold{fold_index}_f{f}.las")
            n_ex, n_ord = build_task(sampled, task_path)
            for vname, flags in VARIANTS.items():
                rules, dt, timed_out, unsat, out = run_ilasp(task_path, flags)
                log = os.path.join(G.WORK, "logs",
                                   f"g2_fold{fold_index}_f{f}_{vname}.log")
                with open(log, "w") as lf:
                    lf.write(out)
                opt_cache = {}
                ev = (evaluate(rules, test_files, opt_cache, gt_cache)
                      if not (timed_out or unsat) else None)
                rec = {
                    "fold": fold_index, "f": f, "variant": vname,
                    "n_train_examples": n_ex, "n_orderings": n_ord,
                    "ilasp_seconds": round(dt, 2),
                    "timed_out": timed_out, "unsat": unsat,
                    "learned": rules, "eval": ev,
                }
                results.append(rec)
                print(json.dumps(rec))
    with open(os.path.join(G.WORK, "results_g2.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
