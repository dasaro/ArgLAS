"""Secondary metrics on the PIPELINE-learned models (run_integration.py output).

GRD E2 (discrimination MCC): the pipeline GRD convention (eval_on_bare_aaf)
structurally has no negative class (grounded always exists on a bare AAF), so
its MCC column is 0-degenerate. Following route G1, re-score each pipeline
model on the SAME fold-held-out labelled instances with the checker oracle
grd_check_oracle.lp (UNSAT exactly on non-grounded-consistent labellings),
learned side = [bg_nochoice_grd + model + labelled instance] (the ':- in,out'
constraint rejects clashes). full_exact_model. This gives a real 2x2 / MCC
comparable to ADM/CMP/STB.

PRF bare-AAF audit (route P2's discriminating metric): labelled-instance
full_exact_model at p=1.0 cannot see the preferred/stable gap; audit each
pipeline model by exact model-set equivalence [bg_learned_prf + model +
convention] vs [preferred.lp + domRec] on (a) the fold's held-out test AAFs,
(b) the 14 incoherent campaign AAFs (empty preferred; in NO pool, so held out
from every fold).
"""
import json
import os
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
INTEG = os.path.join(REPO, "analysis/grd_prf_lab/integration")
G1 = os.path.join(REPO, "analysis/grd_prf_lab/g1_definite_core")
sys.path.insert(0, REPO)
os.chdir(REPO)

import train_test as T  # noqa: E402

AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")
GRD_POOL = os.path.join(INTEG, "pools/labelled_GRD_full")
PRF_POOL = os.path.join(INTEG, "pools/labelled_PRF_full")
BG_NOCHOICE = os.path.join(INTEG, "bg_nochoice_grd.lp")
BG_PRF = os.path.join(INTEG, "bg_learned_prf.lp")
GRD_CHECK = os.path.join(G1, "grd_check_oracle.lp")
PREFERRED_LP = os.path.join(REPO, "ASPARTIX", "preferred.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]
INCOH = ["aaf_5_16", "aaf_5_35", "aaf_5_42", "aaf_6_14", "aaf_6_91",
         "aaf_7_10", "aaf_7_15", "aaf_7_52", "aaf_7_59", "aaf_7_67",
         "aaf_7_75", "aaf_8_42", "aaf_8_78", "aaf_8_90"]

out = {"GRD_E2": [], "PRF_bare": []}

# ---- GRD E2 -----------------------------------------------------------------
folds = T.build_grouped_folds(GRD_POOL, 5, fold_seed=0)
for it in range(1, 6):
    _, test_aafs = folds[it - 1]
    test_files = T.build_grouped_balanced_test(GRD_POOL, test_aafs, 50, 0, it)
    for f in (10, 20):
        model = os.path.join(
            INTEG, f"train_output/GRD_full/ilasp_task_iter_{it}_pos_{f}_neg_{f}_noise_0.lp")
        tp = fp = tn = fn = 0
        for tf in test_files:
            path = os.path.join(GRD_POOL, tf)
            pred = T.run_learned_model_with_api(
                model, path, BG_NOCHOICE, clingo_args=[],
                completion_rules=False, show_predicates=["in/1", "out/1"])
            gt = T.run_ground_truth_with_api(
                GRD_CHECK, path, None, clingo_args=[],
                completion_rules=False, show_predicates=["in/1", "out/1"])
            ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
            tp += a; fp += b; tn += c; fn += d
        out["GRD_E2"].append(
            {"fold": it, "f": f, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
             "MCC": round(T.matthews_corrcoef(tp, fp, tn, fn), 4),
             "ACC": round((tp + tn) / max(1, tp + fp + tn + fn), 4)})

# ---- PRF bare-AAF audit ------------------------------------------------------
pfolds = T.build_grouped_folds(PRF_POOL, 5, fold_seed=0)


def prf_pair(model, path):
    pred = T.run_learned_model_with_api(
        model, path, BG_PRF, clingo_args=DOMREC,
        completion_rules=True, show_predicates=["in/1"])
    gt = T.run_ground_truth_with_api(
        PREFERRED_LP, path, None, clingo_args=DOMREC,
        completion_rules=False, show_predicates=["in/1"])
    return T.canonical_model_set(pred) == T.canonical_model_set(gt)


for it in range(1, 6):
    _, test_aafs = pfolds[it - 1]
    for f in (10, 20):
        model = os.path.join(
            INTEG, f"train_output/PRF_full/ilasp_task_iter_{it}_pos_{f}_neg_{f}_noise_0.lp")
        if not os.path.exists(model):
            continue
        exact = 0
        chosen = sorted(test_aafs)
        for (n, i) in chosen:
            if prf_pair(model, os.path.join(AAF_DIR, f"aaf_{n}_{i}.lp")):
                exact += 1
        incoh_ok = sum(
            1 for stem in INCOH
            if prf_pair(model, os.path.join(AAF_DIR, stem + ".lp")))
        out["PRF_bare"].append(
            {"fold": it, "f": f,
             "bare_exact_heldout": f"{exact}/{len(chosen)}",
             "incoherent_exact": f"{incoh_ok}/14"})

with open(os.path.join(INTEG, "secondary_metrics.json"), "w") as fh:
    json.dump(out, fh, indent=1)
print(json.dumps(out, indent=1))
