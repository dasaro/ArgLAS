#!/usr/bin/env python3
"""P3 probe 1: quantify design asymmetries for H1 (within vs global).
- per-condition recs / distinct cells / cell multiplicities / (rec,arg) and (cell,arg) pair counts
- training-set sizes: WITHIN-LOCO vs GLOBAL 5-fold, per test cell
- same-condition cell exposure: WITHIN train vs GLOBAL train (granularity mismatch b)
- gate hazard: which conditions have all-undec grounded labels everywhere (committed_only=None)
"""
import sys, os
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")

def cell_key(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

recs = U.load_pooled("final")
print(f"TOTAL pooled recs: {len(recs)}")
byv = defaultdict(list)
for r in recs:
    byv[r["version"]].append(r)

folds = U.shared_folds(recs, 5)
fold_of = {}
for fi, f in enumerate(folds):
    for r in f:
        fold_of[cell_key(r)] = fi
fold_sizes = [len(f) for f in folds]
print(f"fold sizes (recs): {fold_sizes}")
all_cells = {cell_key(r) for r in recs}
print(f"total distinct cells (pool): {len(all_cells)}")

print(f"\n{'cond':<5}{'recs':>5}{'cells':>6}{'mult(min/med/max)':>19}{'recArgPairs':>12}{'cellArgPairs':>13}{'commRecArg':>11}{'commCellArg':>12}")
tot_ra = tot_ca = 0
for v in VERSIONS:
    vr = byv[v]
    cells = sorted({cell_key(r) for r in vr})
    mult = Counter(cell_key(r) for r in vr)
    ms = sorted(mult.values())
    ra = sum(len(r["labels"]) for r in vr)
    ca = sum(len(dict(ck[1])) for ck in cells)
    # committed (human in/out) counts
    cra = sum(1 for r in vr for a, h in r["labels"].items() if h in ("in", "out"))
    cca = sum(1 for ck in cells for a, h in dict(ck[1]).items() if h in ("in", "out"))
    tot_ra += ra; tot_ca += ca
    print(f"{v:<5}{len(vr):>5}{len(cells):>6}{str(ms[0])+'/'+str(ms[len(ms)//2])+'/'+str(ms[-1]):>19}{ra:>12}{ca:>13}{cra:>11}{cca:>12}")
print(f"pool rec-arg pairs={tot_ra}  cell-arg pairs={tot_ca}  inflation factor={tot_ra/tot_ca:.2f}")

print("\n=== (a) training-set size asymmetry (recs) ===")
print(f"{'cond':<5}{'WITHIN train (min-max over LOCO)':>34}{'GLOBAL train (min-max over folds)':>36}")
for v in VERSIONS:
    vr = byv[v]
    cells = sorted({cell_key(r) for r in vr})
    wsizes = [len([r for r in vr if cell_key(r) != ck]) for ck in cells]
    gsizes = sorted({len(recs) - fold_sizes[fold_of[ck]] for ck in cells})
    print(f"{v:<5}{f'{min(wsizes)}-{max(wsizes)} (n_c={len(vr)})':>34}{f'{gsizes[0]}-{gsizes[-1]} (pool={len(recs)})':>36}")

print("\n=== (b) same-condition CELL exposure per test cell: WITHIN vs GLOBAL ===")
print(f"{'cond':<5}{'ncells':>7}{'WITHIN own-cells seen':>22}{'GLOBAL own-cells seen (min/mean/max)':>38}{'WITHIN-GLOBAL delta mean':>25}")
for v in VERSIONS:
    vr = byv[v]
    vcells = sorted({cell_key(r) for r in vr})
    n = len(vcells)
    gseen = []
    for ck in vcells:
        fi = fold_of[ck]
        # v-cells visible to the GLOBAL theory that scores ck = v-cells NOT in fold fi
        seen = sum(1 for c2 in vcells if fold_of[c2] != fi)
        gseen.append(seen)
    wseen = n - 1
    import statistics
    print(f"{v:<5}{n:>7}{wseen:>22}{f'{min(gseen)}/{statistics.mean(gseen):.1f}/{max(gseen)}':>38}{f'{wseen - statistics.mean(gseen):+.1f} cells':>25}")

print("\n=== also: same-condition REC exposure (recs of v in train) ===")
import statistics
for v in VERSIONS:
    vr = byv[v]
    vcells = sorted({cell_key(r) for r in vr})
    mult = Counter(cell_key(r) for r in vr)
    w = [len(vr) - mult[ck] for ck in vcells]
    g = []
    for ck in vcells:
        fi = fold_of[ck]
        g.append(sum(mult[c2] for c2 in vcells if fold_of[c2] != fi))
    print(f"{v}: WITHIN own-recs mean {statistics.mean(w):.1f}  GLOBAL own-recs mean {statistics.mean(g):.1f}  delta {statistics.mean(w)-statistics.mean(g):+.1f}")

print("\n=== gate hazard: grounded labels all-undec? (committed_only -> None -> report crash) ===")
for v in VERSIONS:
    vr = byv[v]
    graphs = {(tuple(sorted(r["attacks"])), tuple(r["args"])) for r in vr}
    ncommit = 0
    for atts, args in graphs:
        labs = D.textbook_labellings("grounded", list(args), [list(x) for x in atts] if atts and isinstance(atts[0], (list, tuple)) else list(atts))
        lab = D.project(labs, list(args), "skeptical")
        ncommit += sum(1 for s in lab.values() if s in ("in", "out"))
    print(f"{v}: distinct graphs={len(graphs)}  committed grounded labels across graphs={ncommit}"
          + ("   <-- ALL-UNDEC: gate committed_only=None for every arm incl cf2 -> report() crash" if ncommit == 0 else ""))
