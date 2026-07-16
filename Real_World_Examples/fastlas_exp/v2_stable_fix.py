#!/usr/bin/env python3
"""V2 minimal-fix probe: the Hamming-1 shell cannot pin TOTALITY (all H1 neighbors of a
stable extension are rejected by both the true stable theory and the shorter grounded-ish
one; the shorter theory's spurious models are >=H2 away). Minimal fix: add ONE 'drop-all'
(all-undec) negative per distinct train graph (skipping graphs where all-undec is itself a
train positive). Everything else identical to the harness fold path."""
import os, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G


def build(include_zero_ext):
    base = U.load_pooled("final")
    cache, counters, recs = {}, Counter(), []
    for r in base:
        key = (tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))
        if key not in cache:
            cache[key] = D.textbook_labellings("stable", r["args"], r["attacks"])
        labs = cache[key]
        if not labs:
            if not include_zero_ext:
                continue
            lab = {a: "undec" for a in r["args"]}
        else:
            lab = sorted(labs, key=lambda l: tuple(sorted(l.items())))[counters[key] % len(labs)]
            counters[key] += 1
        proj = D.project(labs, r["args"], "skeptical")
        recs.append({"pid": r["pid"], "args": r["args"], "attacks": r["attacks"],
                     "labels": {a: lab.get(a, "undec") for a in r["args"]},
                     "commit": D.committed(lab),
                     "target": {a: proj.get(a, "undec") for a in r["args"]}})
    return recs


def dropall_negs(train):
    pos_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in train}
    seen, extra = set(), []
    for r in train:
        key = (tuple(sorted(r["attacks"])), ())
        if key in pos_keys or key in seen:
            continue
        seen.add(key)
        extra.append((r["args"], r["attacks"], {}))
    return extra


def run(include_zero_ext):
    recs = build(include_zero_ext)
    folds = U.shared_folds(recs, 2)
    tag = "ALL graphs" if include_zero_ext else "zero-ext excluded"
    print(f"\n===== stable + drop-all negatives ({tag}) recs={len(recs)} folds={[len(f) for f in folds]} =====")
    conf = Counter()
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        cells = U.dedup_weighted(train)
        negs, _ = U.shared_negatives(train, 150)
        negs = negs + dropall_negs(train)          # << the fix
        neg_w = max(1, round(100 * len(train) / len(negs)))  # same mass-balance formula
        t0 = time.time()
        rules, to = U.ilasp_fold(cells, negs, neg_w, 240)
        print(f" fold {fi}: cells={len(cells)} negs={len(negs)} (+{len(dropall_negs(train))} drop-all) "
              f"neg_w={neg_w} ilasp {time.time()-t0:.1f}s TO={to}")
        for rl in (rules or ["(EMPTY)"]):
            print(f"    {rl}")
        for r in test:
            conf += D.score(U.predict_arm("ilasp_maxv1", rules, r["args"], r["attacks"], "skeptical"),
                            r["target"])
    m = D.metrics_from_conf(conf)
    errs = {f"{h}>{p}": n for (h, p), n in conf.items() if h != p}
    print(f" POOLED heldout ilasp acc3={m['acc3']:.4f} (n={m['n_args']}) "
          f"GATE(>=0.95): {'PASS' if m['acc3'] >= 0.95 else 'FAIL'} errors={errs}")
    return m["acc3"]


if __name__ == "__main__":
    a = run(include_zero_ext=False)
    b = run(include_zero_ext=True)
    print(f"\nSUMMARY drop-all fix: zero-ext-excluded acc3={a:.4f} | all-graphs acc3={b:.4f}")
