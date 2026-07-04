#!/usr/bin/env python3
"""Sensitivity check: phase=first fold-1 ILASP hit the 1800s cap (0 rules -> all-undec for that
fold). Re-run ONLY that fold's ILASP with a 3h budget; recompute ILASP's phase=first pooled
numbers with the new fold-1 rules (all other arms/folds unchanged). Reports the delta so we know
whether the ILASP phase=first number was a time-budget artifact or a genuine model limit."""
import json, os, time
from collections import Counter
import unified_compare as U
import discover_semantics as D
import fl_discover as G

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "results", "unified_final.json")
BIG = 10800  # 3h
d = json.load(open(PATH))
m = d["first"]
recs = U.load_pooled("first")
folds = U.shared_folds(recs, 5)

# re-learn ILASP on fold 1 with the big budget
fi = 1
train = [r for j, f in enumerate(folds) if j != fi for r in f]
cells = U.dedup_weighted(train); negs, neg_w = U.shared_negatives(train, 150)
print(f"[sensitivity] re-running phase=first fold {fi} ILASP with {BIG}s budget "
      f"({len(cells)} cells, {len(negs)} negs)...", flush=True)
t0 = time.time()
rules, to = U.ilasp_fold(cells, negs, neg_w, BIG)
print(f"[sensitivity] done in {round(time.time()-t0)}s, timed_out={to}, {len(rules)} rules:", flush=True)
for r in rules:
    print("   ", r, flush=True)

# swap the new rules into the stored fold record, recompute ILASP phase=first confusion
for f in m["folds"]:
    if f["fold"] == fi:
        f["arms"]["ilasp_maxv1"] = {"secs": round(time.time()-t0, 1), "timed_out": to,
                                    "n_rules": len(rules), "rules": rules, "sensitivity": True}
stored = {f["fold"]: f["arms"]["ilasp_maxv1"]["rules"] for f in m["folds"]}

conf = {rd: Counter() for rd in U.READINGS}
for j in range(len(folds)):
    test = folds[j]
    rl = stored[j]
    for r in test:
        for rd in U.READINGS:
            conf[rd] += D.score(U.predict_arm("ilasp_maxv1", rl, r["args"], r["attacks"], rd), r["labels"])

print("\n=== ILASP phase=first, AFTER fold-1 sensitivity re-run ===")
old = d["first"]["table"]["ilasp_maxv1"]
for rd in U.READINGS:
    co, _ = G.committed_only_acc(conf[rd])
    a = D.metrics_from_conf(conf[rd])["acc3"]
    o = old.get(rd, {})
    print(f"  {rd:<10} acc3 {a:.3f} (was {o.get('acc3','?')}) · committed-only {co:.3f} (was {o.get('committed_only','?')})")
print("  cf2 phase=first skeptical acc3 was 0.556 — comparison unchanged in direction.")

# persist the updated fold record + a sensitivity note (do not overwrite the main table numbers;
# store the recomputed ILASP row separately for transparency)
m["ilasp_sensitivity_first"] = {"fold1_rules": rules, "fold1_timed_out": to,
    "recomputed": {rd: {"acc3": round(D.metrics_from_conf(conf[rd])["acc3"], 4),
                        "committed_only": round(G.committed_only_acc(conf[rd])[0], 4)} for rd in U.READINGS}}
U._flush(PATH, d)
print(f"\nsaved -> {PATH}")
