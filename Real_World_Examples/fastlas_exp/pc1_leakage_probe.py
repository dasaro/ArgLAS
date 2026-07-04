#!/usr/bin/env python3
"""P1 probe: leakage & identity across the three arms of per_condition_experiment.py.
Reconstructs the exact loops of the harness (read-only, no learning) and checks:
  (1) WITHIN-LOCO: held-out cell never in that fold's train
  (2) GLOBAL fold_of: scoring theory trained without the fold containing the cell;
      cross-condition identical cells grouped into ONE fold; quantify sharing
  (3) TRANSFER guard: no train rec cell == any test cell; n_guarded per condition
  (4) Coverage: every response scored exactly once per arm; confusion mass = n labels
  (5) Negatives from each arm's own train only (structural check of learn() inputs)
  (X) EXTRA adversarial: example-space identity (attacks, commit) collisions that
      bypass the labels-based cell identity in each arm.
"""
import sys, os
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import unified_compare as U
import fl_discover as G

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")

def cell_key(r):  # byte-identical to harness
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

def ex_key(r):    # FastLAS positive-example identity (dedup_weighted key)
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))

recs = U.load_pooled("final")
print(f"pool n={len(recs)} responses")
byv = defaultdict(list)
for r in recs:
    byv[r["version"]].append(r)
for v in VERSIONS:
    print(f"  {v}: n_recs={len(byv[v])} n_cells={len({cell_key(r) for r in byv[v]})}")

# ---------- cross-condition cell sharing ----------
cell_versions = defaultdict(set)
for r in recs:
    cell_versions[cell_key(r)].add(r["version"])
shared = {ck: vs for ck, vs in cell_versions.items() if len(vs) > 1}
print(f"\n[SHARING] distinct cells total={len(cell_versions)}, shared across >1 condition={len(shared)}")
pair_cnt = Counter()
for ck, vs in shared.items():
    pair_cnt[tuple(sorted(vs))] += 1
for vs, c in sorted(pair_cnt.items()):
    print(f"  shared cell sets {vs}: {c} cells")
n_recs_in_shared = sum(1 for r in recs if cell_key(r) in shared)
print(f"  responses living in shared cells: {n_recs_in_shared}")

# ---------- (1) WITHIN-LOCO ----------
fail1 = 0
exsp1 = 0  # example-space collisions: train rec with same (attacks,commit) as held-out cell but different cell_key
exsp1_detail = []
for v in VERSIONS:
    vrecs = byv[v]
    cells = sorted({cell_key(r) for r in vrecs})
    for ck in cells:
        test = [r for r in vrecs if cell_key(r) == ck]
        train = [r for r in vrecs if cell_key(r) != ck]
        fail1 += sum(1 for r in train if cell_key(r) == ck)
        test_ex = {ex_key(r) for r in test}
        n_coll = sum(1 for r in train if ex_key(r) in test_ex)
        if n_coll:
            exsp1 += n_coll
            exsp1_detail.append((v, cells.index(ck), n_coll))
print(f"\n[1 WITHIN] leaked train recs with held-out cell_key: {fail1} (expect 0)")
print(f"[1 WITHIN, example-space] train recs whose (attacks,commit) == a held-out cell's: {exsp1}")
if exsp1_detail[:10]:
    print("   detail (v, cell_idx, n):", exsp1_detail[:10])

# ---------- (2) GLOBAL fold_of ----------
folds = U.shared_folds(recs, 5)
print(f"\n[2 GLOBAL] n_folds={len(folds)} sizes={[len(f) for f in folds]} sum={sum(len(f) for f in folds)}")
# partition check: every cell entirely inside one fold; every rec in exactly one fold
cell_fold_sets = defaultdict(set)
rec_count = Counter()
for fi, f in enumerate(folds):
    for r in f:
        cell_fold_sets[cell_key(r)].add(fi)
        rec_count[id(r)] += 1
straddle = {ck: fs for ck, fs in cell_fold_sets.items() if len(fs) > 1}
print(f"  cells straddling >1 fold: {len(straddle)} (expect 0)")
print(f"  recs appearing in !=1 fold: {sum(1 for c in rec_count.values() if c != 1)} "
      f"(covered {len(rec_count)}/{len(recs)})")
# fold_of exactly as harness builds it
fold_of = {}
for fi, f in enumerate(folds):
    for r in f:
        fold_of[cell_key(r)] = fi
# the scoring theory for cell ck is global_theories[fold_of[ck]], trained on folds != fold_of[ck]
fail2 = 0
exsp2 = 0
for fi in range(len(folds)):
    train = [r for j, f in enumerate(folds) if j != fi for r in f]
    held_cells = {cell_key(r) for r in folds[fi]}
    fail2 += sum(1 for r in train if cell_key(r) in held_cells)
    held_ex = {ex_key(r) for r in folds[fi]}
    exsp2 += sum(1 for r in train if ex_key(r) in held_ex)
print(f"  train recs sharing cell_key with their held-out fold: {fail2} (expect 0)")
print(f"  [example-space] train recs sharing (attacks,commit) with held-out fold: {exsp2}")
# shared cross-condition cells all in one fold (automatic guard)
sh_in_one = all(len(cell_fold_sets[ck]) == 1 for ck in shared)
print(f"  all {len(shared)} cross-condition shared cells in ONE fold each: {sh_in_one}")
# and per-condition: theory used for scoring == fold containing the cell
ok_dir = True
for v in VERSIONS:
    for ck in {cell_key(r) for r in byv[v]}:
        fi = fold_of[ck]
        if any(cell_key(r) == ck for j, f in enumerate(folds) if j != fi for r in f):
            ok_dir = False
print(f"  scoring theory fold never trained on its cell (all conditions): {ok_dir}")

# ---------- (3) TRANSFER guard ----------
print("\n[3 TRANSFER]")
tot_guard = 0
for v in VERSIONS:
    test_cells = {cell_key(r) for r in byv[v]}
    train = [r for r in recs if r["version"] != v and cell_key(r) not in test_cells]
    n_guarded = sum(1 for r in recs if r["version"] != v and cell_key(r) in test_cells)
    leak = sum(1 for r in train if cell_key(r) in test_cells)
    test_ex = {ex_key(r) for r in byv[v]}
    exsp = sum(1 for r in train if ex_key(r) in test_ex)
    tot_guard += n_guarded
    print(f"  -{v}: train={len(train)} n_guarded={n_guarded} leak_after_guard={leak} "
          f"example-space bypass (same attacks+commit, diff labels): {exsp}")
print(f"  total guarded recs across conditions: {tot_guard}")

# ---------- (4) coverage: each response scored exactly once per arm ----------
print("\n[4 COVERAGE]")
ok4 = True
for v in VERSIONS:
    vrecs = byv[v]
    cells = sorted({cell_key(r) for r in vrecs})
    seen = Counter()
    mass = 0          # confusion mass per (arm, reading) = sum len(labels)
    n_paired = 0      # paired[] entries per arm
    for ck in cells:
        test = [r for r in vrecs if cell_key(r) == ck]
        for r in test:
            seen[id(r)] += 1
            mass += len(r["labels"])
            n_paired += len(r["labels"])
    once = all(c == 1 for c in seen.values()) and len(seen) == len(vrecs)
    exp_mass = sum(len(r["labels"]) for r in vrecs)
    ok = once and mass == exp_mass
    ok4 &= ok
    print(f"  {v}: n_recs={len(vrecs)} scored_once={once} conf_mass={mass} (=sum labels {exp_mass}) "
          f"paired_len={n_paired} {'OK' if ok else 'FAIL'}")
print(f"  all conditions covered exactly once per arm: {ok4}")

# ---------- (5) negatives from own train only ----------
print("\n[5 NEGATIVES] structural check on a real arm train set (WITHIN D, cell 0)")
vrecs = byv["D"]
cells = sorted({cell_key(r) for r in vrecs})
ck = cells[0]
train = [r for r in vrecs if cell_key(r) != ck]
negs, neg_w = U.shared_negatives(train, 150)
train_graphs = {tuple(sorted(r["attacks"])) for r in train}
test_graphs = {tuple(sorted(r["attacks"])) for r in vrecs if cell_key(r) == ck}
all_from_train = all(tuple(sorted(at)) in train_graphs for (_, at, _) in negs)
# every non-dropall neg is Hamming-1 of some train commit
import discover_semantics as D
train_commits = [dict(r["commit"]) for r in train]
def is_h1_of_train(ng):
    for c in train_commits:
        d = set(c.items()) ^ set(ng.items())
        ks = {k for k, _ in d}
        if len(ks) == 1:
            return True
    return False
n_dropall = sum(1 for (_, _, ng) in negs if ng == {})
n_h1 = sum(1 for (_, _, ng) in negs if ng != {} and is_h1_of_train(ng))
print(f"  negs={len(negs)} (H1={n_h1}, drop-all={n_dropall}, other={len(negs)-n_h1-n_dropall}) "
      f"neg_w={neg_w} all graphs from train: {all_from_train}")
# do any negatives coincide with the HELD-OUT cell's committed labelling? (bias check, not leak)
test_commit_keys = {ex_key(r) for r in vrecs if cell_key(r) == ck}
neg_eq_test = sum(1 for (ar, at, ng) in negs
                  if (tuple(sorted(at)), tuple(sorted(ng.items()))) in test_commit_keys)
print(f"  negatives equal to the held-out cell's (attacks,commit): {neg_eq_test} "
      f"(train-derived only; anti-within bias if >0, not leakage)")
# count this bias across ALL LOCO folds of all conditions
tot_bias = 0
for v in VERSIONS:
    vr = byv[v]
    for ck2 in sorted({cell_key(r) for r in vr}):
        tr = [r for r in vr if cell_key(r) != ck2]
        if not tr:
            continue
        ngs, _ = U.shared_negatives(tr, 150)
        tk = {ex_key(r) for r in vr if cell_key(r) == ck2}
        tot_bias += sum(1 for (ar, at, ng) in ngs
                        if (tuple(sorted(at)), tuple(sorted(ng.items()))) in tk)
print(f"  across ALL WITHIN-LOCO folds: negatives coinciding with held-out cell commit: {tot_bias}")
print("\nPROBE DONE")
