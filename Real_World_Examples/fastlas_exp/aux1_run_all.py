#!/usr/bin/env python3
"""Driver: run baseline + all aux1 variants under the SAME leak-free harness, write JSON."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import aux1_scc_cycle as A
import unified_compare as U

OUT = os.path.join(HERE, "results", "aux1_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

PHASE = "final"
recs = U.load_pooled(PHASE)  # load once, reuse (identical folds/negs everywhere)
res = {"phase": PHASE, "started": time.strftime("%H:%M:%S"), "runs": {}}


def save():
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)


def rec(name, r):
    res["runs"][name] = {k: v for k, v in r.items() if k != "conf"}
    save()
    co = r["committed_only_cred"]; sk = r["acc3_skept"]; ck = r["committed_only_skept"]
    print(f"### {name}: committed_only_cred={co:.4f}  skept_acc3={sk:.4f}  "
          f"committed_only_skept={ck:.4f}  to={r['timeouts']} empty={r['empty']} {r['secs']}s", flush=True)


print("=== BASELINE (no aux) ===", flush=True)
rec("BASE", A.run_cv_base(phase=PHASE, mode="opl", maxv=1, timeout=120, recs=recs, verbose=True))

for var in ("mutual", "long", "both"):
    print(f"=== AUX variant={var} (maxv=1) ===", flush=True)
    rec(f"aux_{var}_maxv1", A.run_cv(phase=PHASE, variant=var, mode="opl", maxv=1, timeout=120, recs=recs, verbose=True))

# also try both at maxv=2 (allow 2-var rules that combine aux with base preds)
print("=== AUX variant=both (maxv=2, nopl) ===", flush=True)
rec("aux_both_maxv2_nopl", A.run_cv(phase=PHASE, variant="both", mode="nopl", maxv=2, timeout=300, recs=recs, verbose=True))

res["done"] = time.strftime("%H:%M:%S")
save()
print("DONE ->", OUT, flush=True)
