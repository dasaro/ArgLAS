#!/usr/bin/env python3
"""V1 supplemental: phase='first' identity checks + OPL/NOPL task byte-identity +
all-undec merge audit + fold balance report."""
import os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G

OK = lambda name, cond, extra="": print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

def cellkey(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

def commitkey(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))

for phase in ("final", "first"):
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, 5)
    n_resp = sum(len(r["labels"]) for r in recs)
    au = [r for r in recs if not r["commit"]]
    print(f"\n=== phase={phase}: {len(recs)} participants, {n_resp} responses, "
          f"fold sizes {[len(f) for f in folds]}, all-undec={len(au)} ===")
    cellsets = [set(cellkey(r) for r in f) for f in folds]
    straddle = sum(len(cellsets[i] & cellsets[j]) for i in range(len(cellsets)) for j in range(i + 1, len(cellsets)))
    OK("no (graph,labels) cell straddles folds", straddle == 0, f"({straddle})")
    cs = []
    for fi in range(len(folds)):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        tck = set(commitkey(r) for r in train)
        cs.append(sum(1 for r in test if commitkey(r) in tck))
    OK("no (graph,commit) positive-example straddle either", sum(cs) == 0, f"(per fold {cs})")
    # per-fold neg stats + weight sanity for ALL folds
    for fi in range(len(folds)):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            print(f"    fold {fi}: SKIPPED (empty train or test)")
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, 150)
        wsum = sum(c["weight"] for c in cells)
        print(f"    fold {fi}: train={len(train)} cells={len(cells)} posmass={wsum} "
              f"negs={len(negs)} neg_w={neg_w} negmass={neg_w*len(negs)} "
              f"ratio={neg_w*len(negs)/wsum:.3f} test_resp={sum(len(r['labels']) for r in test)}")
        assert wsum == 100 * len(train), "pos mass != 100/response"

# OPL vs NOPL receive the byte-identical task (only the CLI mode flag differs)
recs = U.load_pooled("final")
folds = U.shared_folds(recs, 5)
train = [r for j, f in enumerate(folds) if j != 0 for r in f]
cells = U.dedup_weighted(train)
negs, neg_w = U.shared_negatives(train, 150)
t_opl = U.fastlas_task(cells, negs, neg_w, maxv=1, enrich=True)
t_default = U.fastlas_task(cells, negs, neg_w)  # what fastlas_fold passes for both arms
OK("\nOPL and NOPL arms consume the byte-identical FastLAS task", t_opl == t_default)

# all-undec merge audit: which recs merged into the weight-500 cell?
groups = defaultdict(list)
for r in train:
    if not r["commit"]:
        groups[tuple(sorted(r["attacks"]))].append((r["version"], r["pid"], tuple(sorted(r["labels"].items()))))
print("\nall-undec train recs by drawn graph:")
for g, members in groups.items():
    print(f"  graph {g}:")
    for m in members:
        print(f"    {m}")

# cell_folds label-cells for the all-undec recs: do they share ONE cell (travel together)?
lab_cells = defaultdict(list)
for r in recs:
    if not r["commit"]:
        lab_cells[cellkey(r)].append((r["version"], r["pid"]))
print(f"\nall-undec label-cells: {len(lab_cells)} distinct")
for k, v in lab_cells.items():
    print(f"  labels {k[1]} <- {v}")
