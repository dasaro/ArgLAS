#!/usr/bin/env python3
"""Seed-robustness for the aux9 combined vocabulary: paired (baseline, aux-ON) committed-only at
several fold seeds. Flushes each result to results/aux9_robustness.json IMMEDIATELY so session
interruptions cannot wipe completed cells. Re-running skips already-done (seed,config) cells."""
import json, os, time
import unified_compare as U
import aux9_combined as A9

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "aux9_robustness.json")
SEEDS = [20260703, 424242, 777, 20250101]

def load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {}

def flush(d):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"; json.dump(d, open(tmp, "w"), indent=1); os.replace(tmp, OUT)

d = load()
for seed in SEEDS:
    for with_aux in (False, True):
        key = f"{seed}_{'aux' if with_aux else 'base'}"
        if key in d and d[key].get("committed_only") is not None:
            print(f"[{key}] cached committed_only={d[key]['committed_only']:.4f}", flush=True)
            continue
        U.SEED = seed
        t0 = time.time()
        r = A9.cv(phase="final", with_aux=with_aux, timeout=150)
        d[key] = {"seed": seed, "aux": with_aux, "committed_only": round(r["committed_only"], 4),
                  "skeptical_acc3": round(r["skeptical_acc3"], 4), "secs": round(time.time() - t0)}
        flush(d)
        print(f"[{key}] committed_only={r['committed_only']:.4f} skeptical={r['skeptical_acc3']:.4f} "
              f"({d[key]['secs']}s)", flush=True)
# paired deltas
print("\n=== paired aux - baseline deltas ===", flush=True)
for seed in SEEDS:
    b = d.get(f"{seed}_base", {}).get("committed_only")
    a = d.get(f"{seed}_aux", {}).get("committed_only")
    if b is not None and a is not None:
        print(f"  seed {seed}: baseline {b:.4f} -> aux {a:.4f}  (delta {a-b:+.4f})", flush=True)
print("DONE", flush=True)
