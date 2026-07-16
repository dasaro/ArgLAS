"""Pool sanity vs the exact eval stacks:
POS: gt (preferred.lp+domRec) nonempty; TRUE core + convention == gt (TP).
NEG: gt empty; TRUE core pred empty (TN).
Also: the TRUE-core MCC ceiling should be 1.0 on the sampled instances.
"""
import os
import random
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention")
sys.path.insert(0, REPO)
from arglas import train_test as T  # noqa: E402

PREFERRED_LP = os.path.join(REPO, "config", "ASPARTIX", "preferred.lp")
BG_CONV = os.path.join(LAB, "bg_learned_prf.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]

for pool, core in [("pool_adm", "true_adm_core.lp"),
                   ("pool_cmp", "true_cmp_core.lp")]:
    d = os.path.join(LAB, pool, "labelled_PRF_full")
    core_path = os.path.join(LAB, core)
    rng = random.Random(1)
    pos = rng.sample(sorted(f for f in os.listdir(d) if "_POS_" in f), 60)
    neg = rng.sample(sorted(f for f in os.listdir(d) if "_NEG_" in f), 60)
    tp = fp = tn = fn = 0
    bad = []
    for f in pos + neg:
        path = os.path.join(d, f)
        pred = T.run_learned_model_with_api(
            core_path, path, BG_CONV, clingo_args=DOMREC,
            completion_rules=True, show_predicates=["in/1"])
        gt = T.run_ground_truth_with_api(
            PREFERRED_LP, path, None, clingo_args=DOMREC,
            completion_rules=False, show_predicates=["in/1"])
        ok, a, b, c, dd = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp += a; fp += b; tn += c; fn += dd
        if not ok:
            bad.append(f)
        if "_POS_" in f and not gt:
            bad.append(("POS-with-empty-gt", f))
        if "_NEG_" in f and gt:
            bad.append(("NEG-with-nonempty-gt", f))
    print(pool, f"TP={tp} FP={fp} TN={tn} FN={fn} "
          f"MCC={T.matthews_corrcoef(tp, fp, tn, fn):.3f} bad={bad[:6]}")
