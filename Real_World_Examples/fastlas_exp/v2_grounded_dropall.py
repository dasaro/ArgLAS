#!/usr/bin/env python3
"""V2 safety check: drop-all negatives must not break the grounded gate (all 3 arms)."""
import os, sys, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
from v2_gate import synth_recs
from v2_stable_fix import dropall_negs

recs, _ = synth_recs("final", "grounded")
folds = U.shared_folds(recs, 2)
conf = {a: Counter() for a in ("ilasp_maxv1", "fastlas_opl", "fastlas_nopl")}
for fi in range(len(folds)):
    test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
    cells = U.dedup_weighted(train)
    negs, _ = U.shared_negatives(train, 150)
    negs = negs + dropall_negs(train)
    neg_w = max(1, round(100 * len(train) / len(negs)))
    rb = {}
    rb["ilasp_maxv1"], _t = U.ilasp_fold(cells, negs, neg_w, 240)
    rb["fastlas_opl"], _t = U.fastlas_fold(cells, negs, neg_w, "opl", 60)
    rb["fastlas_nopl"], _t = U.fastlas_fold(cells, negs, neg_w, "nopl", 240)
    print(f"fold {fi} negs={len(negs)} neg_w={neg_w}")
    for a, rl in rb.items(): print(f"  {a}: {rl}")
    for r in test:
        for a in conf:
            conf[a] += D.score(U.predict_arm(a, rb[a], r["args"], r["attacks"], "skeptical"), r["labels"])
for a, c in conf.items():
    m = D.metrics_from_conf(c)
    print(f"{a}: pooled heldout acc3={m['acc3']:.4f} (n={m['n_args']}) {'PASS' if m['acc3']>=0.95 else 'FAIL'}")
