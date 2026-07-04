#!/usr/bin/env python3
"""Contextual-reasoning test: does each condition A-G have a DISTINCT best-fitting semantics?
For each condition and phase: (1) committed-only of every textbook semantics on THAT condition's
human labellings (no training -> the clean 'how well does semantics S describe these humans'
measure); (2) whether the best textbook semantics VARIES across conditions (= contextual); (3) a
per-condition LEARNED theory (base vocab, resubstitution) to see what axioms each condition prefers
and whether they differ. Flushes to results/per_condition.json."""
import json, os, time
from collections import Counter
import unified_compare as U
import aux9_combined as A9
import fl_discover as G
import discover_semantics as D

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "per_condition.json")
VERSIONS = ("A", "B", "C", "D", "E", "F", "G")
GROUP = {"A": "FLOAT", "B": "FLOAT", "C": "FLOAT", "D": "SIMPLE", "E": "SIMPLE", "F": "SIMPLE", "G": "CYCLE"}


def cond_recs(v, phase):
    return [r for r in U.load_pooled(phase) if r["version"] == v]


def textbook_committed(recs, kind, reading="credulous"):
    conf = Counter()
    for r in recs:
        labs = D.textbook_labellings(kind, r["args"], r["attacks"])
        conf += D.score(D.project(labs, r["args"], reading), r["labels"])
    return G.committed_only_acc(conf)[0]


def learned_theory(recs, with_aux=False, timeout=200):
    cells = U.dedup_weighted(recs); negs, neg_w = U.shared_negatives(recs, 150)
    task = A9.build_task(cells, negs, neg_w, with_aux=with_aux)
    return G.run_fastlas(task, mode="opl", timeout=timeout) or []


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    res = {}
    for phase in ("final", "first"):
        res[phase] = {}
        print(f"\n############ phase={phase} · per-condition textbook committed-only (credulous) ############", flush=True)
        print(f"  {'cond':<5}{'type':<8}{'grd':>7}{'pref':>7}{'stab':>7}{'comp':>7}{'cf2':>7}   best", flush=True)
        for v in VERSIONS:
            recs = cond_recs(v, phase)
            tb = {k: textbook_committed(recs, k) for k in D.TEXTBOOK}
            best = max(tb, key=tb.get)
            res[phase][v] = {"type": GROUP[v], "n": len(recs), "textbook": {k: round(x, 3) for k, x in tb.items()},
                             "best_textbook": best, "best_val": round(tb[best], 3)}
            print(f"  {v:<5}{GROUP[v]:<8}" + "".join(f"{tb[k]:>7.3f}" for k in ("grounded", "preferred", "stable", "complete", "cf2"))
                  + f"   {best} ({tb[best]:.3f})", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
    # per-condition learned theories (base vocab, resubstitution) on the discriminating conditions
    print("\n############ per-condition LEARNED theories (base vocab, phase=final, resubstitution) ############", flush=True)
    res["learned_theories"] = {}
    for v in VERSIONS:
        recs = cond_recs(v, "final")
        t0 = time.time()
        rules = learned_theory(recs, with_aux=False)
        co = None
        conf = Counter()
        for r in recs:  # resubstitution committed-only of the learned theory
            conf += D.score(G.predict(rules, r["args"], r["attacks"], "credulous", enrich=True), r["labels"])
        co = G.committed_only_acc(conf)[0]
        res["learned_theories"][v] = {"type": GROUP[v], "n_rules": len(rules), "rules": rules,
                                      "resub_committed_only": round(co, 3), "secs": round(time.time() - t0)}
        json.dump(res, open(OUT, "w"), indent=1)
        print(f"\n  === {v} ({GROUP[v]}, n={len(recs)}, learned committed-only(resub)={co:.3f}) ===", flush=True)
        for rl in rules:
            print(f"     {rl}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("\nDONE", flush=True)
