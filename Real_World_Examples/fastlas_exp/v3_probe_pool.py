#!/usr/bin/env python3
"""V3 probe: data faithfulness vs 2022 IndAF counting + leak-freeness.
(1) pool counts, G/p2 absence, all-undec kept, graph == att_final for both phases
(2) textbook anchor over the FULL 5-fold harness path (skeptical %correct) vs PAPER + validated baseline
(3) leak checks: cell straddling, commit-level straddling, train-only negatives, deterministic cap
(4) response weighting: every labelled arg scored exactly once per arm per reading
"""
import os, sys, glob
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G

EXTRACT = D.EXTRACT

def parse_graph(path):
    args, attacks, labels = D.parse_lp(path)
    return tuple(sorted(attacks)), args, labels

print("=" * 90)
print("PART 1: POOL FAITHFULNESS")
print("=" * 90)
pools = {}
for phase in ("final", "first"):
    recs = U.load_pooled(phase)
    pools[phase] = recs
    n_resp = sum(len(r["labels"]) for r in recs)
    per_v = Counter(r["version"] for r in recs)
    per_v_resp = Counter()
    for r in recs:
        per_v_resp[r["version"]] += len(r["labels"])
    all_undec = [(r["version"], r["pid"]) for r in recs
                 if all(s == "undec" for s in r["labels"].values())]
    print(f"\nphase={phase}: participants={len(recs)}  responses={n_resp}")
    print(f"  per-version participants: {dict(sorted(per_v.items()))}")
    print(f"  per-version responses:    {dict(sorted(per_v_resp.items()))}")
    print(f"  all-undec participants kept: {len(all_undec)} -> {sorted(all_undec)}")
    g_pids = sorted(r["pid"] for r in recs if r["version"] == "G")
    print(f"  G pids: {g_pids}")
    print(f"  G/p2 present in pool: {any(p == 'p2' for p in g_pids)}")

# duplicated pids within a version?
for phase in ("final", "first"):
    dup = [k for k, c in Counter((r["version"], r["pid"]) for r in pools[phase]).items() if c > 1]
    print(f"phase={phase}: duplicate (version,pid) entries: {dup}")

# graph identity: pooled graph == att_final graph for BOTH phases; differs from att_first where drawings differ
print("\n-- graph source check (ALL participants, both phases) --")
for phase in ("final", "first"):
    n_match_final = n_mismatch_final = n_diff_first = n_first_missing = 0
    mismatches = []
    for r in pools[phase]:
        v, pid = r["version"], r["pid"]
        pooled_att = tuple(sorted(r["attacks"]))
        f_final = os.path.join(EXTRACT, f"version{v}", "att_final__lab_final", f"{pid}.lp")
        att_final = parse_graph(f_final)[0] if os.path.exists(f_final) else None
        if att_final == pooled_att:
            n_match_final += 1
        else:
            n_mismatch_final += 1
            mismatches.append((v, pid, pooled_att, att_final))
        f_first = os.path.join(EXTRACT, f"version{v}", "att_first__lab_first", f"{pid}.lp")
        if os.path.exists(f_first):
            att_first = parse_graph(f_first)[0]
            if att_first != pooled_att:
                n_diff_first += 1
        else:
            n_first_missing += 1
    print(f"phase={phase}: pooled graph == att_final(gold-source file): {n_match_final}/{len(pools[phase])}"
          f"  mismatches={n_mismatch_final}")
    print(f"           pooled graph != participant's att_first drawing: {n_diff_first} "
          f"(att_first file missing: {n_first_missing})")
    for m in mismatches[:5]:
        print("   MISMATCH:", m)

# spot-check 10 participants for phase=first explicitly: labels from lab_first, graph from att_final
print("\n-- spot-check 10 participants, phase=first --")
import random
rng = random.Random(7)
sample = rng.sample(pools["first"], 10)
for r in sample:
    v, pid = r["version"], r["pid"]
    att_pool = tuple(sorted(r["attacks"]))
    att_final = parse_graph(os.path.join(EXTRACT, f"version{v}", "att_final__lab_final", f"{pid}.lp"))[0]
    ff = os.path.join(EXTRACT, f"version{v}", "att_first__lab_first", f"{pid}.lp")
    att_first = parse_graph(ff)[0] if os.path.exists(ff) else "MISSING"
    # labels should equal lab_first labels from the att_final__lab_first file
    lab_file = os.path.join(EXTRACT, f"version{v}", "att_final__lab_first", f"{pid}.lp")
    _, largs, llabels = parse_graph(lab_file)
    lab_expected = {a: s for a, s in llabels.items() if s in D.CLASSES}
    ok_g = att_pool == att_final
    same_first = att_pool == att_first
    ok_l = r["labels"] == lab_expected
    print(f"  {v}/{pid}: graph==att_final:{ok_g}  graph==att_first:{same_first}  labels==lab_first:{ok_l}")

# cross-phase graph identity for common pids
common = {(r["version"], r["pid"]): tuple(sorted(r["attacks"])) for r in pools["final"]}
diffs = 0
n_common = 0
for r in pools["first"]:
    k = (r["version"], r["pid"])
    if k in common:
        n_common += 1
        if common[k] != tuple(sorted(r["attacks"])):
            diffs += 1
print(f"\ncross-phase: common participants={n_common}, graphs differing between phases={diffs}")
only_final = set(common) - {(r['version'], r['pid']) for r in pools['first']}
only_first = {(r['version'], r['pid']) for r in pools['first']} - set(common)
print(f"participants only in final pool: {sorted(only_final)}")
print(f"participants only in first pool: {sorted(only_first)}")

print("\n" + "=" * 90)
print("PART 2: TEXTBOOK ANCHOR over the FULL 5-fold harness path (skeptical)")
print("=" * 90)
VALIDATED = {"final": {"grounded": 56.2, "preferred": 63.8, "cf2": 64.8}}
from apples_to_apples import PAPER
for phase in ("final", "first"):
    recs = pools[phase]
    folds = U.shared_folds(recs, 5)
    print(f"\nphase={phase}: n_folds={len(folds)}  fold sizes={[len(f) for f in folds]}")
    conf = {(a, rd): Counter() for a in D.TEXTBOOK for rd in D.READINGS}
    seen_pids = Counter()
    tb_cache = {}
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        for r in test:
            seen_pids[(r["version"], r["pid"])] += 1
            for arm in D.TEXTBOOK:
                key = (arm, tuple(sorted(r["attacks"])), tuple(r["args"]))
                if key not in tb_cache:
                    tb_cache[key] = D.textbook_labellings(arm, r["args"], r["attacks"])
                labs = tb_cache[key]
                for rd in D.READINGS:
                    conf[(arm, rd)] += D.score(D.project(labs, r["args"], rd), r["labels"])
    multi = {k: c for k, c in seen_pids.items() if c != 1}
    print(f"  every participant tested exactly once across folds: {not multi} "
          f"(violations: {multi})")
    print(f"  {'sem':<11}{'n':<6}{'%correct(skept)':<17}{'PAPER ind-' + phase:<14}{'validated' if phase == 'final' else ''}")
    for arm in D.TEXTBOOK:
        c = conf[(arm, "skeptical")]
        n = sum(c.values())
        pc = 100.0 * sum(c[(x, x)] for x in D.CLASSES) / n
        paper = PAPER.get(("ind", phase), {}).get(arm, "-")
        val = VALIDATED.get(phase, {}).get(arm, "-")
        print(f"  {arm:<11}{n:<6}{pc:<17.2f}{str(paper):<14}{val}")

print("\n" + "=" * 90)
print("PART 3: LEAK CHECKS")
print("=" * 90)
for phase in ("final", "first"):
    recs = pools[phase]
    folds = U.shared_folds(recs, 5)
    # (a) (graph, full-labelling) cells never straddle folds
    cell2folds = defaultdict(set)
    for fi, f in enumerate(folds):
        for r in f:
            cell2folds[(tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))].add(fi)
    straddle = {k: v for k, v in cell2folds.items() if len(v) > 1}
    print(f"\nphase={phase}: distinct (graph,labelling) cells={len(cell2folds)}; straddling folds: {len(straddle)}")
    # (b) secondary: commit-level cells straddling (test commit seen verbatim in train)
    commit2folds = defaultdict(set)
    for fi, f in enumerate(folds):
        for r in f:
            commit2folds[(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))].add(fi)
    cstraddle = {k: v for k, v in commit2folds.items() if len(v) > 1}
    n_test_leaky = 0
    for fi, f in enumerate(folds):
        train_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))
                      for j, g2 in enumerate(folds) if j != fi for r in g2}
        for r in f:
            if (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) in train_keys:
                n_test_leaky += 1
    print(f"  commit-level cells={len(commit2folds)}; straddling={len(cstraddle)}; "
          f"test recs whose exact (graph,commit) positive is in train: {n_test_leaky}/{len(recs)}")
    # (c) negatives: train-only + deterministic
    for fi in range(len(folds)):
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        negs1, w1 = U.shared_negatives(train, 150)
        negs2, w2 = U.shared_negatives(train, 150)
        det = (negs1 == negs2 and w1 == w2)
        train_graphs = {tuple(sorted(r["attacks"])) for r in train}
        test_graphs = {tuple(sorted(r["attacks"])) for r in folds[fi]}
        neg_graphs = {tuple(sorted(at)) for (_, at, _) in negs1}
        only_test_graphs = neg_graphs - train_graphs
        # negatives must not coincide with any TRAIN positive commit cell
        train_pos = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in train}
        n_hit_pos = sum(1 for (_, at, ng) in negs1
                        if (tuple(sorted(at)), tuple(sorted(ng.items()))) in train_pos)
        # do negatives coincide with a TEST positive (informative, soft so allowed, count it)
        test_pos = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in folds[fi]}
        n_hit_testpos = sum(1 for (_, at, ng) in negs1
                            if (tuple(sorted(at)), tuple(sorted(ng.items()))) in test_pos)
        if fi == 0 or not det or only_test_graphs or n_hit_pos:
            print(f"  fold{fi}: n_negs={len(negs1)} neg_w={w1} deterministic={det} "
                  f"neg-graphs-not-in-train={len(only_test_graphs)} negs==train-pos-cell={n_hit_pos} "
                  f"negs==test-pos-cell(soft, counts as shaping): {n_hit_testpos}")
    # summary over folds
    dets, hits, hits_test = [], [], []
    for fi in range(len(folds)):
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        negs1, w1 = U.shared_negatives(train, 150)
        negs2, w2 = U.shared_negatives(train, 150)
        dets.append(negs1 == negs2 and w1 == w2)
        train_pos = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in train}
        test_pos = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in folds[fi]}
        hits.append(sum(1 for (_, at, ng) in negs1 if (tuple(sorted(at)), tuple(sorted(ng.items()))) in train_pos))
        hits_test.append(sum(1 for (_, at, ng) in negs1 if (tuple(sorted(at)), tuple(sorted(ng.items()))) in test_pos))
    print(f"  all folds deterministic: {all(dets)}; negs==train-pos per fold: {hits}; "
          f"negs==TEST-pos per fold (H1-contamination check, soft): {hits_test}")

print("\n" + "=" * 90)
print("PART 4: RESPONSE WEIGHTING — each labelled arg scored exactly once per arm per reading")
print("=" * 90)
for phase in ("final", "first"):
    recs = pools[phase]
    folds = U.shared_folds(recs, 5)
    n_resp = sum(len(r["labels"]) for r in recs)
    # simulate the harness scoring loop with a dummy arm (textbook grounded) and count contributions
    total_scored = 0
    paired_len = 0
    per_rec_scored = Counter()
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        for r in test:
            c = D.score(D.project(D.textbook_labellings("grounded", r["args"], r["attacks"]),
                                  r["args"], "skeptical"), r["labels"])
            total_scored += sum(c.values())
            per_rec_scored[(r["version"], r["pid"])] += 1
            paired_len += len(r["labels"])
    once = all(v == 1 for v in per_rec_scored.values())
    print(f"phase={phase}: pool responses={n_resp}  scored confusion mass (1 arm,1 reading)={total_scored}  "
          f"paired-vector length={paired_len}  every participant scored exactly once={once}")
    # sanity vs the harness's own meta counting
    print(f"  match: conf n == n_responses: {total_scored == n_resp}; paired == n_responses: {paired_len == n_resp}")

print("\nDONE")
