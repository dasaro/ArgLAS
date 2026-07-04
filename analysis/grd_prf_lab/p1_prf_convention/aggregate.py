"""Aggregate run results: pooled confusion + MCC per variant x f."""
import json
import os
import sys
from collections import defaultdict

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
sys.path.insert(0, REPO)
import train_test as T  # noqa: E402

RUNS = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention/runs")

rows = []
for f in sorted(os.listdir(RUNS)):
    if f.startswith("results_") and f.endswith(".json"):
        for line in open(os.path.join(RUNS, f)):
            line = line.strip()
            if line:
                rows.append(json.loads(line))

groups = defaultdict(list)
for r in rows:
    variant, ff, fold = r["tag"].split("_")
    groups[(variant, ff)].append(r)

for (variant, ff), rs in sorted(groups.items()):
    tp = sum(r.get("tp", 0) for r in rs)
    fp = sum(r.get("fp", 0) for r in rs)
    tn = sum(r.get("tn", 0) for r in rs)
    fn = sum(r.get("fn", 0) for r in rs)
    mccs = [r["mcc"] for r in rs if "mcc" in r]
    bares = [r.get("bare_aaf_exact_preferred_recovery", "0/0") for r in rs]
    bare_num = sum(int(b.split("/")[0]) for b in bares)
    bare_den = sum(int(b.split("/")[1]) for b in bares)
    trains = [r["train_seconds"] for r in rs]
    fails = [r["tag"] for r in rs if not r.get("succeeded")]
    print(f"{variant} f={ff[1:]}: folds={len(rs)} "
          f"pooled TP={tp} FP={fp} TN={tn} FN={fn} "
          f"pooledMCC={T.matthews_corrcoef(tp, fp, tn, fn):.4f} "
          f"perfoldMCC={[round(m,3) for m in mccs]} "
          f"bare_recovery={bare_num}/{bare_den} "
          f"train_s={[round(t,1) for t in trains]} fails={fails}")

print("\ntheories:")
for r in rows:
    print(r["tag"], "|", "; ".join(r.get("theory", ["<none>"])))
