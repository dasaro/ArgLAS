#!/usr/bin/env python3
"""V2 final stable probe: drop the zero-stable-extension graphs (stable assigns them NO
labelling -> all-undec positives that NO total semantics can cover), extension positives,
through the exact harness fold machinery. If ILASP now recovers stable, the gate failure is
fully attributed to those graphs, not to weights/maxv/neg_w or any harness bug."""
import os, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D

TRUE_THEORY = ["in(V1) :- arg(V1); not defeated(V1).", "out(V1) :- defeated(V1)."]

base = U.load_pooled("final")
cache, counters, recs = {}, Counter(), []
for r in base:
    key = (tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))
    if key not in cache:
        cache[key] = D.textbook_labellings("stable", r["args"], r["attacks"])
    labs = cache[key]
    if not labs:
        continue  # zero-extension graph excluded
    lab = sorted(labs, key=lambda l: tuple(sorted(l.items())))[counters[key] % len(labs)]
    counters[key] += 1
    proj = D.project(labs, r["args"], "skeptical")
    recs.append({"pid": r["pid"], "args": r["args"], "attacks": r["attacks"],
                 "labels": {a: lab.get(a, "undec") for a in r["args"]},
                 "commit": D.committed(lab),
                 "target": {a: proj.get(a, "undec") for a in r["args"]}})

nz = sum(1 for k, v in cache.items() if not v)
print(f"kept {len(recs)}/{len(base)} recs; excluded {nz} zero-extension graphs")
folds = U.shared_folds(recs, 2)
print(f"folds={[len(f) for f in folds]}")
conf, conf_true = Counter(), Counter()
for fi in range(len(folds)):
    test = folds[fi]
    train = [r for j, f in enumerate(folds) if j != fi for r in f]
    cells = U.dedup_weighted(train)
    negs, neg_w = U.shared_negatives(train, 150)
    t0 = time.time()
    rules, to = U.ilasp_fold(cells, negs, neg_w, 240)
    print(f"fold {fi}: train={len(train)} cells={len(cells)} negs={len(negs)} neg_w={neg_w} "
          f"ilasp {time.time()-t0:.1f}s TO={to}")
    for rl in (rules or ["(EMPTY)"]):
        print(f"   {rl}")
    for r in test:
        conf += D.score(U.predict_arm("ilasp_maxv1", rules, r["args"], r["attacks"], "skeptical"), r["target"])
        conf_true += D.score(D.project(D.learned_labellings(TRUE_THEORY, r["args"], r["attacks"]),
                                       r["args"], "skeptical"), r["target"])
m, mt = D.metrics_from_conf(conf), D.metrics_from_conf(conf_true)
errs = {f"{h}>{p}": n for (h, p), n in conf.items() if h != p}
print(f"POOLED heldout ilasp acc3={m['acc3']:.4f} (n={m['n_args']}) "
      f"GATE(>=0.95): {'PASS' if m['acc3'] >= 0.95 else 'FAIL'} errors={errs}")
print(f"TRUE stable theory same path: acc3={mt['acc3']:.4f}")
