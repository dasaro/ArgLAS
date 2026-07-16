#!/usr/bin/env python3
"""Part B: score the old-route learned GRD theories through the REAL pipeline
evaluation convention (imports train_test) over all 500 campaign AAFs.

GRD convention per semantics_config.json:
  learned stack   = background_knowledge.lp + learned rules + BARE AAF
  completion      = False (GRD override)
  clingo_args     = --heuristic=Domain --enum=domRec  (sem-level args apply to
                    the learned stage too via get_clingo_args)
  show            = in/1, out/1
  gt stack        = grounded.lp + BARE AAF (no background), completion False,
                    same clingo args, show in/1, out/1
  match           = full_exact_model (exact model-set equality)
"""
import os
import re
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
sys.path.insert(0, REPO)
os.chdir(REPO)

from arglas import train_test as T  # noqa: E402

AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p2_prf_alt")
BACKGROUND = os.path.join(REPO, "config/background_knowledge.lp")
GROUNDED = os.path.join(REPO, "config/ASPARTIX/grounded.lp")

GRD_ARGS = ["--heuristic=Domain", "--enum=domRec"]
SHOW = ["in/1", "out/1"]


def extract_rules(ilasp_out):
    with open(ilasp_out) as f:
        text = f.read()
    return "\n".join(T.extract_hypothesis_rules(text))


def score(theory_text, n_aafs=500, args=GRD_ARGS):
    model_file = os.path.join(LAB, "models", "_tmp_theory.lp")
    with open(model_file, "w") as f:
        f.write(theory_text + "\n")
    aafs = sorted(f for f in os.listdir(AAF_DIR) if f.endswith(".lp"))[:n_aafs]
    tp = fp = tn = fn = correct = 0
    pred_model_counts = []
    for name in aafs:
        path = os.path.join(AAF_DIR, name)
        pred = T.run_learned_model_with_api(
            model_file, path, BACKGROUND,
            clingo_args=args, completion_rules=False, show_predicates=SHOW)
        gt = T.run_ground_truth_with_api(
            GROUNDED, path, None,
            clingo_args=args, completion_rules=False, show_predicates=SHOW)
        ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        correct += int(ok)
        tp += a; fp += b; tn += c; fn += d
        pred_model_counts.append(len(pred))
    acc = correct / len(aafs)
    import statistics
    return acc, (tp, fp, tn, fn), statistics.median(pred_model_counts), max(pred_model_counts)


def main():
    theories = {
        "grd_f10_plain": extract_rules(f"{LAB}/models/grd_f10_plain.out"),
        "grd_f10_heur": extract_rules(f"{LAB}/models/grd_f10_heur.out"),
        "grd_f30_plain": extract_rules(f"{LAB}/models/grd_f30_plain.out"),
        "grd_f30_heur": extract_rules(f"{LAB}/models/grd_f30_heur.out"),
        # the one good theory the 2026-06-24 session saw ILASP learn (memory):
        "memory_rule_plus_heuristic":
            "in(V1) :- arg(V1), not not_defended(V1).\n#heuristic in(V1). [1@1, false]",
    }
    for name, th in theories.items():
        acc, conf, med_pred, max_pred = score(th)
        print(f"{name}: bare-AAF exact-model acc={acc:.3f} "
              f"TP,FP,TN,FN={conf} median|pred|={med_pred} max|pred|={max_pred}")
        print("  theory: " + th.replace("\n", " | "))


if __name__ == "__main__":
    main()
