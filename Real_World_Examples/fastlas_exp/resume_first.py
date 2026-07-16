#!/usr/bin/env python3
"""Resume the interrupted unified comparison: phase=first has folds 0-3 recorded (with learned
rules per arm) in results/unified_final.json; fold 4 was lost. Re-score folds 0-3 from the STORED
rules (deterministic — folds and predictions are reproducible), learn fold 4 live, and write the
completed state to results/unified_final.json (backing up the partial file first)."""
import json, os, shutil, time
from collections import Counter
import unified_compare as U
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import discover_semantics as D
import fl_discover as G

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "results", "unified_final.json")
shutil.copy(PATH, PATH + ".partial_bak")
state = json.load(open(PATH))
meta = state["first"]
stored = {f["fold"]: f for f in meta["folds"]}
timeouts = {"ilasp": 1800, "opl": 300, "nopl": 600}

recs = U.load_pooled("first")
folds = U.shared_folds(recs, 5)
conf = {(a, rd): Counter() for a in U.ARMS for rd in U.READINGS}
paired = {(a, rd): [] for a in U.ARMS for rd in ("skeptical", "credulous")}
pair_keys = []
new_folds = []

for fi in range(len(folds)):
    test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
    if fi in stored:
        frec = stored[fi]
        rules_by_arm = {a: frec["arms"][a]["rules"] for a in U.LEARNERS}
        print(f"[first] fold {fi}: reusing stored rules "
              + " ".join(f"{a}:{len(r)}r" for a, r in rules_by_arm.items()), flush=True)
    else:
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, 150)
        frec = {"fold": fi, "n_train": len(train), "n_cells": len(cells),
                "n_negs": len(negs), "neg_w": neg_w, "arms": {}}
        rules_by_arm = {}
        for arm in U.LEARNERS:
            t0 = time.time()
            if arm == "ilasp_maxv1":
                rules, to = U.ilasp_fold(cells, negs, neg_w, timeouts["ilasp"])
            elif arm == "fastlas_opl":
                rules, to = U.fastlas_fold(cells, negs, neg_w, "opl", timeouts["opl"])
            else:
                rules, to = U.fastlas_fold(cells, negs, neg_w, "nopl", timeouts["nopl"])
            rules_by_arm[arm] = rules
            frec["arms"][arm] = {"secs": round(time.time() - t0, 1), "timed_out": to,
                                 "n_rules": len(rules), "rules": rules}
            print(f"[first] fold {fi} {arm}: {frec['arms'][arm]['secs']}s "
                  f"{len(rules)}r{' TO' if to else ''}", flush=True)
    for r in test:
        preds = {}
        for arm in U.ARMS:
            for rd in U.READINGS:
                p = U.predict_arm(arm, rules_by_arm.get(arm), r["args"], r["attacks"], rd)
                conf[(arm, rd)] += D.score(p, r["labels"])
                if rd in ("skeptical", "credulous"):
                    preds[(arm, rd)] = p
        cellk = (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))
        for a_, h in r["labels"].items():
            pair_keys.append((cellk, a_))
            for arm in U.ARMS:
                for rd in ("skeptical", "credulous"):
                    paired[(arm, rd)].append(1 if preds[(arm, rd)].get(a_, "undec") == h else 0)
    new_folds.append(frec)

meta["folds"] = new_folds
meta["status"] = "done"
meta["table"] = U._table(conf, paired, pair_keys)
meta["conf"] = {f"{a}|{rd}": {f"{h}>{p}": n for (h, p), n in c.items()}
                for (a, rd), c in conf.items()}
state["status"] = "ALL DONE"
U._flush(PATH, state)
U.print_report(state)
print(f"\nresumed + completed -> {PATH}")
