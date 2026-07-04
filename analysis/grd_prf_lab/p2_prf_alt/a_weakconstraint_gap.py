#!/usr/bin/env python3
"""Part A: quantify how wrong the tempting weak-constraint PRF route is.

For every campaign AAF compare:
  PRF  = preferred extensions  (ASPARTIX preferred.lp + --heuristic=Domain --enum=domRec,
         i.e. the pipeline's ground-truth convention)
  MAXC = maximum-CARDINALITY complete extensions (ASPARTIX complete.lp core +
         #maximize over in/1, clingo --opt-mode=optN, all optimal models)
  CMP  = all complete extensions (plain enumeration)  [also needed by Part C]

Cross-checks:
  - brute-force preferred = subset-maximal elements of CMP in-sets, must equal PRF
    (independently validates the domRec convention on this pool -> T4)
  - MAXC must be a subset of PRF (T2 direction that IS guaranteed)

Outputs JSON with per-AAF sets + a summary.
"""
import json
import os
import sys

import clingo

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")
OUT = os.path.join(REPO, "analysis/grd_prf_lab/p2_prf_alt/a_gap_results.json")

PREFERRED_LP = os.path.join(REPO, "ASPARTIX/preferred.lp")
COMPLETE_LP = os.path.join(REPO, "ASPARTIX/complete.lp")


def solve_in_sets(files, extra_program=None, args=(), optimal_only=False):
    ctl = clingo.Control(["-n", "0", "--warn=none", *args])
    for f in files:
        ctl.load(f)
    if extra_program:
        ctl.add("base", [], extra_program)
    ctl.add("base", [], "#show in/1.")
    ctl.ground([("base", [])])
    models = []
    with ctl.solve(yield_=True) as handle:
        for m in handle:
            if optimal_only and not m.optimality_proven:
                continue
            models.append(frozenset(str(s) for s in m.symbols(shown=True)))
    # dedupe (optN can re-yield; disjunctive enum can repeat projections)
    return set(models)


def maximal_elements(sets_of_insets):
    """Subset-maximal in-sets (brute-force preferred from complete)."""
    insets = [set(s) for s in sets_of_insets]
    out = set()
    for i, s in enumerate(insets):
        if not any(j != i and s < t for j, t in enumerate(insets)):
            out.add(frozenset(s))
    return out


def main():
    aafs = sorted(f for f in os.listdir(AAF_DIR) if f.endswith(".lp"))
    assert len(aafs) == 500, len(aafs)

    per_aaf = {}
    n_diff = 0
    total_missed = 0
    n_domrec_mismatch = 0
    n_maxc_not_subset = 0
    n_prf_neq_cmp = 0

    for name in aafs:
        path = os.path.join(AAF_DIR, name)
        prf = solve_in_sets([PREFERRED_LP, path],
                            args=("--heuristic=Domain", "--enum=domRec"))
        cmp_sets = solve_in_sets([COMPLETE_LP, path])
        maxc = solve_in_sets([COMPLETE_LP, path],
                             extra_program="#maximize{1,X : in(X)}.",
                             args=("--opt-mode=optN",), optimal_only=True)

        brute_prf = maximal_elements(cmp_sets)
        if brute_prf != prf:
            n_domrec_mismatch += 1
        if not maxc <= prf:
            n_maxc_not_subset += 1
        if prf != cmp_sets:
            n_prf_neq_cmp += 1

        missed = prf - maxc
        differs = len(missed) > 0 or maxc != prf
        if differs:
            n_diff += 1
            total_missed += len(missed)

        per_aaf[name] = {
            "prf": sorted(sorted(s) for s in prf),
            "cmp": sorted(sorted(s) for s in cmp_sets),
            "maxc": sorted(sorted(s) for s in maxc),
            "n_prf": len(prf),
            "n_cmp": len(cmp_sets),
            "n_maxc": len(maxc),
            "n_missed_by_maxcard": len(missed),
            "differs": differs,
        }

    summary = {
        "n_aafs": len(aafs),
        "n_aafs_maxcard_differs_from_preferred": n_diff,
        "pct_aafs_differ": round(100.0 * n_diff / len(aafs), 2),
        "total_preferred_labellings_missed_by_maxcard": total_missed,
        "total_preferred_labellings": sum(v["n_prf"] for v in per_aaf.values()),
        "n_aafs_preferred_neq_complete": n_prf_neq_cmp,
        "sanity_domrec_vs_bruteforce_mismatches": n_domrec_mismatch,
        "sanity_maxcard_not_subset_of_preferred": n_maxc_not_subset,
        "weakconstraint_bareAAF_exactmodel_accuracy_ceiling":
            round(1.0 - n_diff / len(aafs), 4),
    }
    with open(OUT, "w") as f:
        json.dump({"summary": summary, "per_aaf": per_aaf}, f, indent=1)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
