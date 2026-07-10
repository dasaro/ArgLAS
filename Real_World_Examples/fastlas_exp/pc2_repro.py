#!/usr/bin/env python3
"""P2 probe: INDEPENDENT reproduction of condition D WITHIN arm (real labels, aux vocab).

From scratch: enumerate D cells (own cell_key), read the cached LOCO rules from the
harness state file, re-run prediction via A9.predict, score with OWN scoring code
(no G.committed_only_acc / D.metrics_from_conf), compare to the harness table.
Also hand-recompute the H1 (within vs global) McNemar triple from the stored paired
lists with an OWN exact-binomial implementation."""
import json, math, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import unified_compare as U
import aux9_combined as A9

STATE = os.path.join(HERE, "results", "per_condition_experiment.json")
st = json.load(open(STATE))["final_aux"]
cst = st["conditions"]["D"]
assert cst.get("done"), "condition D not done in state file"

# ---- own cell enumeration (mirrors harness definition, written independently) ----
def my_cell_key(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

recs = U.load_pooled("final")
drecs = [r for r in recs if r["version"] == "D"]
cells = sorted({my_cell_key(r) for r in drecs})
print(f"D: {len(drecs)} pooled responses (participants), {len(cells)} distinct cells "
      f"(harness says n_recs={cst['n_recs']}, n_cells={cst['n_cells']})")

# ---- re-run prediction per LOCO fold, own scoring ----
conf_c, conf_s = Counter(), Counter()          # (human,pred) counters, credulous/skeptical
my_paired_within = []
for ci, ck in enumerate(cells):
    rules = cst["loco"][str(ci)]["rules"]
    test = [r for r in drecs if my_cell_key(r) == ck]
    for r in test:
        pc = A9.predict(rules, r["args"], r["attacks"], "credulous", with_aux=True) \
            if rules else {a: "undec" for a in r["args"]}
        ps = A9.predict(rules, r["args"], r["attacks"], "skeptical", with_aux=True) \
            if rules else {a: "undec" for a in r["args"]}
        for a, h in r["labels"].items():
            conf_c[(h, pc.get(a, "undec"))] += 1
            conf_s[(h, ps.get(a, "undec"))] += 1
            my_paired_within.append(1 if pc.get(a, "undec") == h else 0)

def my_committed_only(conf):
    tot = sum(n for (h, p), n in conf.items() if h in ("in", "out"))
    cor = sum(n for (h, p), n in conf.items() if h in ("in", "out") and h == p)
    return (cor / tot if tot else float("nan")), tot

def my_acc3(conf):
    tot = sum(conf.values())
    return sum(n for (h, p), n in conf.items() if h == p) / tot if tot else float("nan")

co, ncom = my_committed_only(conf_c)
acc3_c, acc3_s = my_acc3(conf_c), my_acc3(conf_s)
hw = cst["table"]["within"]
print("\n--- WITHIN arm, condition D ---")
print(f"mine   : committed_only={co:.4f} n_committed={ncom} cred_acc3={acc3_c:.4f} skept_acc3={acc3_s:.4f}")
print(f"harness: committed_only={hw['credulous']['committed_only']:.4f} "
      f"n_committed={hw['credulous']['n_committed']} cred_acc3={hw['credulous']['acc3']:.4f} "
      f"skept_acc3={hw['skeptical']['acc3']:.4f}")
match = (round(co, 4) == hw["credulous"]["committed_only"]
         and ncom == hw["credulous"]["n_committed"]
         and round(acc3_c, 4) == hw["credulous"]["acc3"]
         and round(acc3_s, 4) == hw["skeptical"]["acc3"])
print(f"MATCH to 4dp: {match}")

# also compare my per-response credulous correctness vector to the stored one
stored = cst["paired"]["within"]
print(f"paired-vector: len mine={len(my_paired_within)} stored={len(stored)} "
      f"identical={my_paired_within == stored} "
      f"(sum mine={sum(my_paired_within)} stored={sum(stored)})")

# ---- hand-check H1 McNemar (within vs global, credulous, response-level) ----
w, g = cst["paired"]["within"], cst["paired"]["global"]
b = sum(1 for x, y in zip(w, g) if x == 1 and y == 0)
c_ = sum(1 for x, y in zip(w, g) if y == 1 and x == 0)
n = b + c_
if n == 0:
    p = 1.0
else:
    pmf = [math.comb(n, i) * 0.5 ** n for i in range(n + 1)]
    thr = pmf[min(b, c_)] * (1 + 1e-9)
    p = min(1.0, sum(x for x in pmf if x <= thr))
ht = cst["tests"]["H1_within_vs_global"]["credulous"]
print("\n--- H1 within-vs-global McNemar (credulous, response-level) ---")
print(f"mine   : b(within-only)={b} c(global-only)={c_} p={p:.6f}")
print(f"harness: b={ht['n1_only']} c={ht['n2_only']} p={ht['p']}")
print(f"MATCH: {b == ht['n1_only'] and c_ == ht['n2_only'] and round(p, 6) == ht['p']}")
