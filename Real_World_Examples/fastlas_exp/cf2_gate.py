#!/usr/bin/env python3
"""SYNTHETIC GATE for CF2 — the pre-registered comparator of Experiment 2.

Symmetric to aux1_gate.py (grounded) and v2_gate.py (stable): feed CLEAN CF2
labels through the EXACT Exp2 learn+predict path and ask whether the learner
recovers CF2 (B1 pass threshold: skeptical acc3 >= 0.95). Unlike grounded,
CF2 is multi-extension on the floating/cycle structures, so each distinct CF2
labelling of a graph is a separate clean "participant" cell (no projection
before training); scoring is per distinct graph against the per-reading
projection of the full CF2 labelling set — exactly how the CF2 comparator row
is scored in unified_compare.py.

Arms (vocabularies) x FastLAS modes, plus one ILASP maxv=1 attempt:
  base    baseline enrich vocabulary (G._FEATS + structural closure)
  mutual / long / both   the aux1 SCC-cycle variants
  aux9    the full combined auxiliary vocabulary of Table tab:aux

Usage:  python3 cf2_gate.py [--arms base,both,aux9] [--modes opl,nopl]
                            [--ilasp] [--timeout 300] [--out cf2_gate_results.json]
"""
import os, sys, json, argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import aux1_scc_cycle as A
import aux9_combined as X9


def clean_cf2_data(phase="final"):
    """One training rec per (distinct graph, distinct CF2 labelling); one truth
    entry per distinct graph with the per-reading projections."""
    recs, graphs, seen = [], [], set()
    for r in U.load_pooled(phase):
        gk = tuple(sorted(r["attacks"]))
        if gk in seen:
            continue
        seen.add(gk)
        labs = D.textbook_labellings("cf2", r["args"], r["attacks"])
        truth = {rd: D.project(labs, r["args"], rd) for rd in D.READINGS}
        graphs.append({"args": r["args"], "attacks": r["attacks"], "truth": truth,
                       "n_labellings": len(labs)})
        for lab in labs:
            full = {a: lab.get(a, "undec") for a in r["args"]}
            commit = {a: s for a, s in full.items() if s in ("in", "out")}
            recs.append({"args": r["args"], "attacks": r["attacks"],
                         "commit": commit, "labels": full})
    return recs, graphs


def learn(arm, mode, cells, negs, neg_w, timeout, maxv):
    if arm == "base":
        task = A.build_task_base(cells, negs, neg_w, maxv=maxv)
    elif arm in ("mutual", "long", "both"):
        task = A.build_task(cells, negs, neg_w, arm, maxv=maxv)
    elif arm == "aux9":
        task = X9.build_task(cells, negs, neg_w, maxv=maxv, enrich=True, with_aux=True)
    else:
        raise ValueError(arm)
    return G.run_fastlas(task, mode=mode, timeout=timeout)


def predict(arm, rules, args, attacks, reading):
    if arm == "base":
        return A.predict_base(rules, args, attacks, reading)
    if arm in ("mutual", "long", "both"):
        return A.predict(rules, args, attacks, reading, arm)
    if arm == "aux9":
        return X9.predict(rules, args, attacks, reading, enrich=True, with_aux=True)
    raise ValueError(arm)


def gate(arm, mode, timeout=300, maxv=1):
    recs, graphs = clean_cf2_data("final")
    # resubstitution recovery test, as in aux1_gate: learn on ALL cells
    cells = U.dedup_weighted(recs)
    negs, neg_w = U.shared_negatives(recs, 200)
    rules = learn(arm, mode, cells, negs, neg_w, timeout, maxv)
    conf = {rd: Counter() for rd in D.READINGS}
    for g in graphs:
        for rd in D.READINGS:
            p = predict(arm, rules, g["args"], g["attacks"], rd)
            conf[rd] += D.score(p, g["truth"][rd])
    return {"arm": arm, "mode": mode, "rules": rules,
            "skept_acc3": D.metrics_from_conf(conf["skeptical"])["acc3"],
            "cred_acc3": D.metrics_from_conf(conf["credulous"])["acc3"],
            "n_cells": len(cells), "n_negs": len(negs),
            "n_graphs": len(graphs),
            "n_labellings": sum(g["n_labellings"] for g in graphs)}


def gate_ilasp(timeout=600):
    recs, graphs = clean_cf2_data("final")
    cells = U.dedup_weighted(recs)
    negs, neg_w = U.shared_negatives(recs, 200)
    rules, timed_out = U.ilasp_fold(cells, negs, neg_w, timeout)
    conf = {rd: Counter() for rd in D.READINGS}
    for g in graphs:
        for rd in D.READINGS:
            p = U.predict_arm("ilasp_maxv1", rules, g["args"], g["attacks"], rd)
            conf[rd] += D.score(p, g["truth"][rd])
    return {"arm": "ilasp_maxv1", "mode": "ilasp", "rules": rules,
            "timed_out": timed_out,
            "skept_acc3": D.metrics_from_conf(conf["skeptical"])["acc3"],
            "cred_acc3": D.metrics_from_conf(conf["credulous"])["acc3"],
            "n_cells": len(cells), "n_negs": len(negs), "n_graphs": len(graphs)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="base,mutual,long,both,aux9")
    ap.add_argument("--modes", default="opl,nopl")
    ap.add_argument("--ilasp", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "cf2_gate_results.json"))
    a = ap.parse_args()
    out = []
    for arm in [x.strip() for x in a.arms.split(",") if x.strip()]:
        for mode in [m.strip() for m in a.modes.split(",") if m.strip()]:
            r = gate(arm, mode, timeout=a.timeout, maxv=a.maxv)
            print(f"[cf2_gate] {arm}/{mode}: skept={r['skept_acc3']:.3f} "
                  f"cred={r['cred_acc3']:.3f} cells={r['n_cells']}", flush=True)
            out.append(r)
    if a.ilasp:
        r = gate_ilasp(timeout=max(a.timeout, 600))
        print(f"[cf2_gate] ilasp_maxv1: skept={r['skept_acc3']:.3f} "
              f"cred={r['cred_acc3']:.3f} timed_out={r['timed_out']}", flush=True)
        out.append(r)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("wrote", a.out)
