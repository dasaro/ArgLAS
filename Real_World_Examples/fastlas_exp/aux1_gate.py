#!/usr/bin/env python3
"""SYNTHETIC GATE for aux1: feed CLEAN grounded labels through the EXACT aux1 learn+predict path
and confirm it still recovers grounded (skeptical acc3 ~ 1.0). The aux predicates must NOT break
recovery. We build clean grounded cells on the real IndAF graphs, learn a `violated` theory with
the aux background, predict grounded-of-survivors, and score vs the clean grounded labels.
"""
import os, sys, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import aux1_scc_cycle as A


def clean_grounded_recs(phase="final"):
    """Replace each participant's human labels with the CLEAN grounded labelling of their graph."""
    recs = U.load_pooled(phase)
    out = []
    seen = set()
    for r in recs:
        gk = tuple(sorted(r["attacks"]))
        if gk in seen:
            continue
        seen.add(gk)
        labs = D.textbook_labellings("grounded", r["args"], r["attacks"])
        # grounded is unique -> one labelling; take skeptical projection = the labelling itself
        gl = D.project(labs, r["args"], "skeptical")
        commit = {a: s for a, s in gl.items() if s in ("in", "out")}
        out.append({"args": r["args"], "attacks": r["attacks"], "commit": commit,
                    "labels": gl})
    return out


def gate(variant="both", mode="opl", maxv=1, timeout=120):
    recs = clean_grounded_recs("final")
    # learn on ALL cells (recovery test, resubstitution is the correct check for a gate)
    cells = U.dedup_weighted(recs)
    negs, neg_w = U.shared_negatives(recs, 200)
    task = A.build_task(cells, negs, neg_w, variant, maxv=maxv)
    rules = G.run_fastlas(task, mode=mode, timeout=timeout)
    conf = {rd: Counter() for rd in D.READINGS}
    for r in recs:
        for rd in D.READINGS:
            conf[rd] += D.score(A.predict(rules, r["args"], r["attacks"], rd, variant), r["labels"])
    return {"variant": variant, "rules": rules,
            "skept_acc3": D.metrics_from_conf(conf["skeptical"])["acc3"],
            "cred_acc3": D.metrics_from_conf(conf["credulous"])["acc3"],
            "grounded_acc3": D.metrics_from_conf(conf["grounded"])["acc3"],
            "committed_only_skept": G.committed_only_acc(conf["skeptical"])[0],
            "n_cells": len(cells), "n_negs": len(negs)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="both")
    ap.add_argument("--mode", default="opl")
    ap.add_argument("--maxv", type=int, default=1)
    a = ap.parse_args()
    r = gate(variant=a.variant, mode=a.mode, maxv=a.maxv)
    print(json.dumps(r, indent=1, default=str))
