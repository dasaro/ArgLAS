"""Sanity A: hand-written weak constraint on the complete core reproduces
grounded on ALL 500 campaign AAFs (oracle-equivalence bound for ILASP).

Checks per AAF:
  1. core in-projection == ASPARTIX complete.lp in-projection (core correct)
  2. OPT(core + ':~ in(X).[1@1,X]')  == grounded.lp model set (exact, in+out)
  3. OPT(core + ':~ out(X).[1@1,X]') == grounded.lp model set (exact, in+out)
  4. grounded.lp has exactly one model
"""
import json
import sys

sys.path.insert(0, "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude/analysis/grd_prf_lab/g2_weak")
import g2lib as G

WC_IN = ":~ in(X). [1@1, X]"
WC_OUT = ":~ out(X). [1@1, X]"

fails = {"core_vs_aspartix": [], "wc_in": [], "wc_out": [], "gt_not_unique": []}
n = 0
n_multi_complete = 0
for size, idx, path in G.all_aafs():
    n += 1
    bare = G.read_bare_aaf(path)
    gt = G.grounded_gt_models(bare)
    if len(gt) != 1:
        fails["gt_not_unique"].append((size, idx, len(gt)))
    gt_set = G.T.canonical_model_set(gt)

    comp = G.complete_labellings(bare)
    if len(comp) > 1:
        n_multi_complete += 1
    core_insets = {frozenset(a for a in m if a.startswith("in(")) for m in comp}
    if core_insets != G.aspartix_complete_insets(bare):
        fails["core_vs_aspartix"].append((size, idx))

    for name, wc in (("wc_in", WC_IN), ("wc_out", WC_OUT)):
        opt = G.solve_optimal_models([G.CORE_FILE], additional_program=bare + "\n" + wc)
        if G.T.canonical_model_set(opt) != gt_set:
            fails[name].append((size, idx))

print(json.dumps({
    "n_aafs": n,
    "n_multi_complete": n_multi_complete,
    "fail_counts": {k: len(v) for k, v in fails.items()},
    "fail_examples": {k: v[:5] for k, v in fails.items()},
}, indent=2))
