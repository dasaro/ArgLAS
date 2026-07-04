"""Negative control: train on 10 fold-1-train AAFs with a UNIQUE complete
extension (zero orderings) -> ILASP has no preference signal -> empty
hypothesis -> hard negatives (complete-not-grounded) should become FPs on
the fold-1 test set, dragging MCC well below 1. Confirms the eval is not
saturated by construction."""
import json, os, random, sys
sys.path.insert(0, "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude/analysis/grd_prf_lab/g2_weak")
import g2lib as G
from run_g2 import build_task, run_ilasp, evaluate, TEST_PER_CLASS, FOLD_SEED, K
T = G.T

folds = T.build_grouped_folds(G.POOL_DIR, K, fold_seed=FOLD_SEED)
train_aafs, test_aafs = folds[0]
rng = random.Random(12345)
unique = []
for size, idx in sorted(train_aafs):
    bare = G.read_bare_aaf(os.path.join(G.AAF_DIR, f"aaf_{size}_{idx}.lp"))
    if len(G.complete_labellings(bare)) == 1:
        unique.append((size, idx))
sampled = rng.sample(unique, 10)
task = os.path.join(G.WORK, "tasks", "control_unique_f10.las")
n_ex, n_ord = build_task(sampled, task)
rules, dt, to, unsat, out = run_ilasp(task, [])
test_files = T.build_grouped_balanced_test(G.POOL_DIR, test_aafs, TEST_PER_CLASS, fold_seed=FOLD_SEED, fold_index=1)
ev = evaluate(rules, test_files, {}, {})
print(json.dumps({"n_orderings": n_ord, "learned": rules, "unsat": unsat, "eval": ev}))
