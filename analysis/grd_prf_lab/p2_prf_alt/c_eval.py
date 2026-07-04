#!/usr/bin/env python3
"""Part C evaluation: score every candidate PRF theory.

1) Bare-AAF oracle-equivalence (all 500 + the 100 held-out test AAFs):
     learned side = background_knowledge.lp + theory + completion rules + bare AAF,
                    plain enumeration, projected to in/1  -> set of in-sets
     GT           = preferred in-sets (Part A, ASPARTIX preferred + domRec)
     equivalent iff the two sets of in-sets are EQUAL.
   Also re-run learned side with the PRF pipeline clingo args
   (--heuristic=Domain --enum=domRec) and assert identity (no #heuristic atoms
   in any learned theory -> domRec is ignored).

2) Held-out grouped balanced test MCC (pipeline-faithful, via train_test):
     50 POS + 50 NEG labelled instances sampled from TEST-AAF pool files,
     learned: T.run_learned_model_with_api(bg, theory, instance),
              completion=True, clingo_args=PRF sem args, show in/out
     gt:      T.run_ground_truth_with_api(preferred.lp, instance),
              completion=False, same args, show in/out
     T.evaluate_model_sets(=full_exact_model), T.matthews_corrcoef.

3) Diagnostic: preferred-vs-stable divergence on the pool (the "totality
   shortcut" ceiling).
"""
import json
import os
import random
import re
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
sys.path.insert(0, REPO)
os.chdir(REPO)
import clingo  # noqa: E402
import train_test as T  # noqa: E402

LAB = os.path.join(REPO, "analysis/grd_prf_lab/p2_prf_alt")
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")
POOL = os.path.join(LAB, "pools/labelled_PRF_full")
BACKGROUND = os.path.join(REPO, "background_knowledge.lp")
PREFERRED_LP = os.path.join(REPO, "ASPARTIX/preferred.lp")
PRF_ARGS = ["--heuristic=Domain", "--enum=domRec"]
SHOW = ["in/1", "out/1"]

DATA = json.load(open(os.path.join(LAB, "a_gap_results.json")))["per_aaf"]
SPLIT = json.load(open(os.path.join(LAB, "c_split.json")))


def extract(out_file):
    return "\n".join(T.extract_hypothesis_rules(open(f"{LAB}/models/{out_file}").read()))


THEORIES = {
    "prf_f10_plain(all-AAF,f10)": extract("prf_f10_plain.out"),
    "prf_f10_heur(all-AAF,f10)": extract("prf_f10_heur.out"),
    "c2_default(pin-hardneg)": extract("c2_default.out"),
    "c2_ml4rl6(pin-hardneg)": extract("c2_ml4rl6.out"),
    "c2_na(pin-hardneg)": extract("c2_na.out"),
    "c2_maxv3(pin-hardneg)": extract("c2_maxv3.out"),
    "c3_default(pin-hard+rand)": extract("c3_default.out"),
    "c3_ml4rl6(pin-hard+rand)": extract("c3_ml4rl6.out"),
    "c3_maxv3(pin-hard+rand)": extract("c3_maxv3.out"),
    "c4_default(pipeline-f40)": extract("c4_default.out"),
    "ORACLE_STB_diag(not learned)":
        ":- in(V1), in(V2), att(V1,V2).\n:- out(V1), not defeated(V1).",
}


def learned_insets(theory_file, aaf_path, args=()):
    models = T.run_learned_model_with_api(
        theory_file, aaf_path, BACKGROUND,
        clingo_args=list(args), completion_rules=True, show_predicates=["in/1"])
    return {frozenset(m) for m in models}


def stable_insets(name):
    """Total complete in-sets (= stable) from Part A data."""
    args, atts = set(), []
    for line in open(os.path.join(AAF_DIR, name)):
        line = line.strip()
        if line.startswith("arg("):
            args.add(line[4:-2])
        elif line.startswith("att("):
            m = re.match(r"att\((\w+),(\w+)\)\.", line)
            atts.append((m.group(1), m.group(2)))
    out = set()
    for s in DATA[name]["cmp"]:
        ins = {re.match(r"in\((\w+)\)", a).group(1) for a in s}
        attacked = {b for (a, b) in atts if a in ins}
        if ins | attacked == args:
            out.add(frozenset(f"in({x})" for x in ins))
    return out


def main():
    aafs = sorted(DATA)
    test_aafs = set(SPLIT["test"])

    # ---- diagnostic: preferred vs stable on the pool
    n_div = 0
    for name in aafs:
        prf = {frozenset(s) for s in map(tuple, DATA[name]["prf"])}
        if stable_insets(name) != prf:
            n_div += 1
    print(f"[diag] preferred != stable(total complete) on {n_div}/500 AAFs "
          f"-> totality-shortcut equivalence ceiling = {1 - n_div/500:.3f}\n")

    # ---- held-out balanced instance test set (grouped: test AAFs only)
    test_stems = {a[:-3] for a in test_aafs}
    pos_files = sorted(f for f in os.listdir(POOL)
                       if "_POS_" in f and re.match(r"(aaf_\d+_\d+)_", f).group(1) in test_stems)
    neg_files = sorted(f for f in os.listdir(POOL)
                       if "_NEG_" in f and re.match(r"(aaf_\d+_\d+)_", f).group(1) in test_stems)
    rng = random.Random(42)
    test_pos = rng.sample(pos_files, 50)
    test_neg = rng.sample(neg_files, 50)

    results = {}
    for tname, rules in THEORIES.items():
        tf = os.path.join(LAB, "models/_eval_theory.lp")
        with open(tf, "w") as f:
            f.write(rules + "\n")

        eq_all = eq_test = 0
        domrec_mismatch = 0
        fail_names = []
        for name in aafs:
            path = os.path.join(AAF_DIR, name)
            pred = learned_insets(tf, path)
            gt = {frozenset(s) for s in map(tuple, DATA[name]["prf"])}
            ok = pred == gt
            pred2 = learned_insets(tf, path, args=PRF_ARGS)
            if pred2 != pred:
                domrec_mismatch += 1
            eq_all += int(ok)
            if name in test_aafs:
                eq_test += int(ok)
            if not ok and len(fail_names) < 3:
                fail_names.append(name)

        tp = fp = tn = fn = 0
        for fn_file in test_pos + test_neg:
            inst = os.path.join(POOL, fn_file)
            pred = T.run_learned_model_with_api(
                tf, inst, BACKGROUND, clingo_args=PRF_ARGS,
                completion_rules=True, show_predicates=SHOW)
            gt = T.run_ground_truth_with_api(
                PREFERRED_LP, inst, None, clingo_args=PRF_ARGS,
                completion_rules=False, show_predicates=SHOW)
            _, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
            tp += a; fp += b; tn += c; fn += d
        mcc = T.matthews_corrcoef(tp, fp, tn, fn)
        acc = (tp + tn) / (tp + fp + tn + fn)

        results[tname] = dict(eq_all=eq_all, eq_test=eq_test,
                              mcc=mcc, conf=(tp, fp, tn, fn), acc=acc)
        print(f"{tname}")
        print(f"  rules: {rules.strip().replace(chr(10), ' | ')}")
        print(f"  bare-AAF oracle-equivalence: {eq_all}/500 all "
              f"({eq_all/5:.1f}%), {eq_test}/100 held-out "
              f"| domRec-vs-plain mismatches: {domrec_mismatch} "
              f"| first fails: {fail_names}")
        print(f"  held-out balanced MCC={mcc:.3f} acc={acc:.3f} "
              f"TP,FP,TN,FN={tp},{fp},{tn},{fn}\n")

    json.dump(results, open(os.path.join(LAB, "c_eval_results.json"), "w"),
              indent=1, default=str)


if __name__ == "__main__":
    main()
