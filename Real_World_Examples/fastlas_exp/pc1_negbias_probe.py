#!/usr/bin/env python3
"""P1 extra probe: per-arm count of train-derived negatives that coincide with the
(attacks, commit) of a held-out TEST cell of that arm. Not leakage (train-only inputs),
but a scoring bias against the arm; must be roughly symmetric across arms for H1/H2 fairness.
Also: determinism of shared_folds across calls (cache-consistency of global_theories)."""
import sys, os
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import unified_compare as U

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")

def cell_key(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

def ex_key(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))

recs = U.load_pooled("final")
byv = defaultdict(list)
for r in recs:
    byv[r["version"]].append(r)

def neg_hits(train, test_recs):
    negs, neg_w = U.shared_negatives(train, 150)
    tk = {ex_key(r) for r in test_recs}
    hits = sum(1 for (ar, at, ng) in negs
               if (tuple(sorted(at)), tuple(sorted(ng.items()))) in tk)
    return hits, len(negs), neg_w

# WITHIN
tot_w = tot_wn = 0
for v in VERSIONS:
    vr = byv[v]
    for ck in sorted({cell_key(r) for r in vr}):
        tr = [r for r in vr if cell_key(r) != ck]
        if not tr:
            continue
        h, n, _ = neg_hits(tr, [r for r in vr if cell_key(r) == ck])
        tot_w += h; tot_wn += n
print(f"WITHIN : neg==test-cell hits {tot_w} / {tot_wn} negs across all LOCO folds")

# GLOBAL
folds = U.shared_folds(recs, 5)
tot_g = tot_gn = 0
per_fold = []
for fi in range(len(folds)):
    tr = [r for j, f in enumerate(folds) if j != fi for r in f]
    h, n, w = neg_hits(tr, folds[fi])
    per_fold.append((fi, h, n, w))
    tot_g += h; tot_gn += n
print(f"GLOBAL : neg==test-cell hits {tot_g} / {tot_gn} negs across 5 folds  per-fold={per_fold}")

# TRANSFER
tot_t = tot_tn = 0
per_v = []
for v in VERSIONS:
    test_cells = {cell_key(r) for r in byv[v]}
    tr = [r for r in recs if r["version"] != v and cell_key(r) not in test_cells]
    h, n, _ = neg_hits(tr, byv[v])
    per_v.append((v, h, n))
    tot_t += h; tot_tn += n
print(f"TRANSFER: neg==test-cell hits {tot_t} / {tot_tn} negs across 7 LOCO conditions  per-v={per_v}")

# determinism of shared_folds (global_theories cache is keyed only by fold index)
f1 = U.shared_folds(recs, 5)
f2 = U.shared_folds(U.load_pooled("final"), 5)
same = all(len(a) == len(b) and all(cell_key(x) == cell_key(y) and x["pid"] == y["pid"]
                                    for x, y in zip(a, b)) for a, b in zip(f1, f2))
print(f"shared_folds deterministic across reloads (pid+cell order identical): {same}")
