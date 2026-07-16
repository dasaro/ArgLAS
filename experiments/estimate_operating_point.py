#!/usr/bin/env python3
"""Estimate the real-data operating point (p, q) for the Exp1->Exp2 bridge.

Given multi-annotator labellings of AAFs, estimate:
  - p  : label completeness  = mean fraction of arguments committed to in/out
  - q  : idiosyncratic per-argument noise, inverted from inter-annotator
         disagreement D via the iid-flip identity D = 2q(1-q)  ->  q = (1-sqrt(1-2D))/2
  - CF : consensus conflict-freeness violation rate (a MODEL-MISMATCH proxy, kept
         strictly separate from q)
and place (p, q) on the measured Exp1 recovery surface (predicted MCC per semantics).

This is a STUB: the analysis is real and self-tested, but it reads a normalized JSON
schema (see --help / --emit-schema) rather than the raw workbook. Adapt the loader when
the real records are wired in. Three-valued aware: human `undec` and missing labels are
both treated as non-commitments (NOT as `out`).

  self-test:  python3 estimate_operating_point.py --selftest
  run:        python3 estimate_operating_point.py --input records.json [--bootstrap 1000]

Normalized input schema:
  {
    "frameworks": { "<id>": {"n_args": 4, "attacks": [["a","b"], ...]}, ... },
    "annotations": [ {"aaf": "<id>", "annotator": "<pid>",
                      "labels": {"a": "in", "b": "out", "c": "undec"}}, ... ]
  }
  (arguments omitted from `labels`, or marked "undec", count as non-commitments)
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from itertools import combinations

COMMIT = {"in", "out"}

# Measured Exp1 recovery surface (mean MCC, pooled over f, succeeded folds) from
# artifacts/final_synthetic_corrected_20260625. Axes: partial p in {1.0,0.75,0.5},
# noise in {0.0,0.1,0.2}. Used for placement (bilinear interpolation).
EXP1_MCC = {
    "ADM": {1.0: {0.0: .986, 0.1: .934, 0.2: .766}, 0.75: {0.0: .892, 0.1: .776, 0.2: .568}, 0.5: {0.0: .850, 0.1: .569, 0.2: .396}},
    "CMP": {1.0: {0.0: .952, 0.1: .913, 0.2: .834}, 0.75: {0.0: .870, 0.1: .806, 0.2: .570}, 0.5: {0.0: .872, 0.1: .446, 0.2: .156}},
    "STB": {1.0: {0.0: .971, 0.1: .896, 0.2: .856}, 0.75: {0.0: .917, 0.1: .768, 0.2: .605}, 0.5: {0.0: .868, 0.1: .724, 0.2: .341}},
}
P_AXIS = [0.5, 0.75, 1.0]
N_AXIS = [0.0, 0.1, 0.2]


def _bracket(axis, v):
    v = min(max(v, axis[0]), axis[-1])
    for i in range(len(axis) - 1):
        if axis[i] <= v <= axis[i + 1]:
            lo, hi = axis[i], axis[i + 1]
            t = 0.0 if hi == lo else (v - lo) / (hi - lo)
            return lo, hi, t
    return axis[-1], axis[-1], 0.0


def predict_mcc(sem, p, q):
    grid = EXP1_MCC[sem]
    plo, phi, tp = _bracket(P_AXIS, p)
    nlo, nhi, tn = _bracket(N_AXIS, q)
    c00, c01 = grid[plo][nlo], grid[plo][nhi]
    c10, c11 = grid[phi][nlo], grid[phi][nhi]
    bottom = c00 * (1 - tn) + c01 * tn
    top = c10 * (1 - tn) + c11 * tn
    return bottom * (1 - tp) + top * tp


def n_args_of(fw):
    return int(fw["n_args"]) if "n_args" in fw else len(fw["args"])


def estimate_p(frameworks, annotations):
    vals = []
    for a in annotations:
        N = n_args_of(frameworks[a["aaf"]])
        if N == 0:
            continue
        commits = sum(1 for s in a["labels"].values() if s in COMMIT)
        vals.append(commits / N)
    return (sum(vals) / len(vals)) if vals else float("nan"), vals


def estimate_q(frameworks, annotations):
    # pool pairwise disagreements over commitments per (framework, arg)
    counts = defaultdict(lambda: {"in": 0, "out": 0})
    for a in annotations:
        for arg, s in a["labels"].items():
            if s in COMMIT:
                counts[(a["aaf"], arg)][s] += 1
    dis_pairs = tot_pairs = 0
    for c in counts.values():
        k = c["in"] + c["out"]
        if k >= 2:
            dis_pairs += c["in"] * c["out"]
            tot_pairs += k * (k - 1) // 2
    if tot_pairs == 0:
        return float("nan"), float("nan"), 0
    D = dis_pairs / tot_pairs
    if D >= 0.5:
        return D, 0.5, tot_pairs  # iid model maxes at D=0.5; clamp q
    q = (1 - math.sqrt(1 - 2 * D)) / 2
    return D, q, tot_pairs


def cf_violation_per_annotation(frameworks, annotations):
    bad = 0
    for a in annotations:
        atts = frameworks[a["aaf"]]["attacks"]
        L = a["labels"]
        if any(L.get(x) == "in" and L.get(y) == "in" for x, y in atts):
            bad += 1
    return bad / len(annotations) if annotations else float("nan")


def cf_violation_consensus(frameworks, annotations):
    # majority commitment per (framework, arg); CF-check the consensus labelling
    counts = defaultdict(lambda: {"in": 0, "out": 0})
    for a in annotations:
        for arg, s in a["labels"].items():
            if s in COMMIT:
                counts[(a["aaf"], arg)][s] += 1
    consensus = {}
    for (fw, arg), c in counts.items():
        if c["in"] or c["out"]:
            consensus.setdefault(fw, {})[arg] = "in" if c["in"] > c["out"] else "out"
    bad = 0
    for fw, lab in consensus.items():
        atts = frameworks[fw]["attacks"]
        if any(lab.get(x) == "in" and lab.get(y) == "in" for x, y in atts):
            bad += 1
    return bad / len(consensus) if consensus else float("nan")


def bootstrap_ci(frameworks, annotations, stat_fn, B, seed=0):
    rng = random.Random(seed)
    n = len(annotations)
    out = []
    for _ in range(B):
        sample = [annotations[rng.randrange(n)] for _ in range(n)]
        v = stat_fn(frameworks, sample)
        if v == v:  # not NaN
            out.append(v)
    out.sort()
    if not out:
        return (float("nan"), float("nan"))
    lo = out[int(0.025 * len(out))]
    hi = out[min(len(out) - 1, int(0.975 * len(out)))]
    return (lo, hi)


def analyze(frameworks, annotations, B=1000):
    p_hat, _ = estimate_p(frameworks, annotations)
    D, q_hat, pairs = estimate_q(frameworks, annotations)
    cf_ann = cf_violation_per_annotation(frameworks, annotations)
    cf_con = cf_violation_consensus(frameworks, annotations)
    p_ci = bootstrap_ci(frameworks, annotations, lambda f, a: estimate_p(f, a)[0], B, 1)
    q_ci = bootstrap_ci(frameworks, annotations, lambda f, a: estimate_q(f, a)[1], B, 2)
    by_size = defaultdict(list)
    for a in annotations:
        N = n_args_of(frameworks[a["aaf"]])
        commits = sum(1 for s in a["labels"].values() if s in COMMIT)
        if N:
            by_size[N].append(commits / N)
    return {
        "n_frameworks": len(frameworks), "n_annotations": len(annotations),
        "p_hat": p_hat, "p_ci": p_ci,
        "D": D, "q_hat": q_hat, "q_pairs": pairs, "q_ci": q_ci,
        "cf_violation_per_annotation": cf_ann, "cf_violation_consensus": cf_con,
        "p_by_size": {N: (sum(v) / len(v), len(v)) for N, v in sorted(by_size.items())},
        "predicted_mcc": {s: predict_mcc(s, p_hat, q_hat) for s in EXP1_MCC} if p_hat == p_hat and q_hat == q_hat else {},
    }


def report(r):
    print(f"Frameworks: {r['n_frameworks']}   Annotations: {r['n_annotations']}")
    print(f"\nCompleteness  p_hat = {r['p_hat']:.3f}   95% CI [{r['p_ci'][0]:.3f}, {r['p_ci'][1]:.3f}]")
    print("  by AAF size N:  " + " · ".join(f"N={N}: p={m:.3f} (n={k})" for N, (m, k) in r["p_by_size"].items()))
    if r["q_hat"] == r["q_hat"]:
        print(f"\nNoise         q_hat = {r['q_hat']:.3f}   95% CI [{r['q_ci'][0]:.3f}, {r['q_ci'][1]:.3f}]   "
              f"(from D={r['D']:.3f} over {r['q_pairs']} committed pairs)")
    else:
        print("\nNoise         q_hat = NA  (no argument had >=2 committed annotators — q not identifiable)")
    print(f"\nModel-mismatch (kept separate from q):")
    print(f"  consensus CF-violation rate = {r['cf_violation_consensus']:.3f}   "
          f"(per-annotation = {r['cf_violation_per_annotation']:.3f})")
    if r["predicted_mcc"]:
        print(f"\nPredicted Exp1 recovery at (p={r['p_hat']:.2f}, noise={r['q_hat']:.2f})  [bilinear on the measured surface]:")
        for s, m in r["predicted_mcc"].items():
            print(f"  {s}: MCC ~ {m:.3f}")
        print("  -> Exp2 shortfall below this = the model-mismatch (human-non-Dung-ness).")


def make_selftest(p_true=0.8, q_true=0.12, K=7, M=20, N=4, seed=7):
    rng = random.Random(seed)
    frameworks, annotations = {}, []
    for k in range(K):
        args = [f"a{i}" for i in range(N)]
        # random attacks; base labelling = a random independent set IN (conflict-free)
        attacks = [(x, y) for x in args for y in args if x != y and rng.random() < 0.35]
        inset = []
        for a in args:
            if all(not ((a, b) in attacks or (b, a) in attacks) for b in inset):
                if rng.random() < 0.5:
                    inset.append(a)
        truth = {a: ("in" if a in inset else "out") for a in args}
        fid = f"F{k}"
        frameworks[fid] = {"n_args": N, "attacks": attacks}
        for m in range(M):
            labels = {}
            for a in args:
                if rng.random() > p_true:
                    continue  # abstain (undec/missing)
                s = truth[a]
                if rng.random() < q_true:
                    s = "out" if s == "in" else "in"
                labels[a] = s
            annotations.append({"aaf": fid, "annotator": f"F{k}_p{m}", "labels": labels})
    return frameworks, annotations, p_true, q_true


def main(argv=None):
    ap = argparse.ArgumentParser(description="Estimate the real-data (p, q) operating point.")
    ap.add_argument("--input", help="Normalized JSON records.")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--selftest", action="store_true", help="Inject known (p,q) and check recovery.")
    ap.add_argument("--emit-schema", action="store_true", help="Print the expected input schema and exit.")
    args = ap.parse_args(argv)

    if args.emit_schema:
        print(__doc__)
        return 0
    if args.selftest:
        fw, ann, p_true, q_true = make_selftest()
        r = analyze(fw, ann, B=args.bootstrap)
        print(f"=== SELF-TEST (true p={p_true}, q={q_true}) ===")
        report(r)
        ok_p = abs(r["p_hat"] - p_true) < 0.03
        ok_q = abs(r["q_hat"] - q_true) < 0.03
        print(f"\nRecovery: p {'OK' if ok_p else 'OFF'} (Δ={r['p_hat']-p_true:+.3f}), "
              f"q {'OK' if ok_q else 'OFF'} (Δ={r['q_hat']-q_true:+.3f})")
        return 0 if (ok_p and ok_q) else 1
    if not args.input:
        ap.error("provide --input <records.json> or --selftest")
    data = json.load(open(args.input))
    r = analyze(data["frameworks"], data["annotations"], B=args.bootstrap)
    report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
