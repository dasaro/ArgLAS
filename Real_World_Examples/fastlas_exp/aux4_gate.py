#!/usr/bin/env python3
"""SYNTHETIC GATE for aux4: feed CLEAN grounded labels through the EXACT aux4 learn+predict path
and confirm it still recovers grounded (skeptical acc3 ~ 1.0). If adding the aux4 structural
predicates breaks recovery, the aux background is unsound and the real numbers cannot be trusted.

We build a set of small AFs, compute their true grounded labelling, use those as the POSITIVE
cells (clean, no noise), generate the H1+dropall negative shell exactly as the real pipeline, run
FastLAS with the aux4 background, then predict grounded-of-survivors on held-out graphs and score
skeptical acc3 vs the true grounded labelling.
"""
import os, sys, itertools, random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import aux4_reachpos as A


def grounded_commit(args, attacks):
    """True grounded labelling (committed in/out only) via ASPARTIX grounded.lp through D."""
    labs = D.textbook_labellings("grounded", args, attacks)
    lab = labs[0] if labs else {a: "undec" for a in args}
    return {a: v for a, v in lab.items() if v in ("in", "out")}


def gen_afs(n_args_range=(3, 4), max_graphs=40, seed=7):
    rng = random.Random(seed)
    afs = []
    for n in n_args_range:
        args = [chr(ord("a") + i) for i in range(n)]
        edges = [(x, y) for x in args for y in args if x != y]
        # sample random subsets of edges
        for _ in range(max_graphs):
            k = rng.randint(1, min(len(edges), n + 2))
            att = sorted(rng.sample(edges, k))
            afs.append((args, att))
    # dedup by attack signature
    seen, uniq = set(), []
    for args, att in afs:
        key = tuple(sorted(att))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((args, att))
    return uniq


def run_gate(aux=True, mode="opl", timeout=120, folds=5, seed=7):
    afs = gen_afs(seed=seed)
    recs = []
    for args, att in afs:
        commit = grounded_commit(args, att)
        recs.append({"args": args, "attacks": att, "commit": commit,
                     "labels": dict(commit)})  # clean: labels == grounded commit
    folds_ = G.cell_folds(recs, folds, seed=U.SEED)
    conf = {rd: Counter() for rd in D.READINGS}
    theories = []
    for fi in range(len(folds_)):
        test = folds_[fi]
        train = [r for j, f in enumerate(folds_) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, 150)
        task = A.build_task(cells, negs, neg_w, maxv=1, enrich=True, aux=aux)
        rules = G.run_fastlas(task, mode=mode, timeout=timeout)
        if rules is None:
            rules = []
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                conf[rd] += D.score(
                    A.predict(rules, r["args"], r["attacks"], rd, enrich=True, aux=aux),
                    r["labels"])
    skept = D.metrics_from_conf(conf["skeptical"])["acc3"]
    co_skept, _ = G.committed_only_acc(conf["skeptical"])
    co_cred, _ = G.committed_only_acc(conf["credulous"])
    return {"aux": aux, "mode": mode, "n_graphs": len(recs), "n_folds": len(folds_),
            "skeptical_acc3": skept, "skeptical_committed_only": co_skept,
            "credulous_committed_only": co_cred, "theories": theories}


if __name__ == "__main__":
    for aux in (False, True):
        r = run_gate(aux=aux)
        print(f"\n=== GATE aux={aux} (n_graphs={r['n_graphs']}, folds={r['n_folds']}) ===")
        print(f"  skeptical acc3 = {r['skeptical_acc3']:.4f}  "
              f"skeptical committed-only = {r['skeptical_committed_only']:.4f}  "
              f"credulous committed-only = {r['credulous_committed_only']:.4f}")
        for t in r["theories"]:
            print("   theory:", t)
