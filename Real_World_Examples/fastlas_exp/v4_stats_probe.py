#!/usr/bin/env python3
"""V4 statistics-correctness probe for unified_compare.py.

(1) mcnemar exact two-sided binomial unit tests (scipy-free hand values)
(2) committed_only_acc + chance-reference semantics
(3) acc3 / metrics_from_conf on hand-built confusions
(4) response-weighted pooling = sum-correct/sum-total (vs mean-of-means)
(5) replicate smoke fold 0 from the stored rules; recompute conf, acc3,
    committed-only, and McNemar b/c from raw predictions; diff vs _table.
"""
import json, math, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
from apples_to_apples import mcnemar, binom_two_sided

FAIL = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        FAIL.append(name + " :: " + detail)

# ---------------- (1) mcnemar unit tests ----------------
print("== (1) mcnemar ==")
# hand value b=5,c=8: n=13, two-sided exact = 2*P(X<=5) = 2*2380/8192
hand_5_8 = 2 * sum(math.comb(13, i) for i in range(6)) / 2**13
check("mcnemar(5,8) == 0.581055 (2*2380/8192)", abs(mcnemar(5, 8) - hand_5_8) < 1e-12,
      f"got {mcnemar(5,8):.6f} expect {hand_5_8:.6f}")
check("mcnemar(0,3) == 0.25", abs(mcnemar(0, 3) - 0.25) < 1e-12, f"got {mcnemar(0,3):.6f}")
check("mcnemar(2,6) hand", abs(mcnemar(2, 6) - 2*sum(math.comb(8,i) for i in range(3))/2**8) < 1e-12,
      f"got {mcnemar(2,6):.6f} expect {2*sum(math.comb(8,i) for i in range(3))/2**8:.6f}")
check("mcnemar(3,7) hand", abs(mcnemar(3, 7) - 2*sum(math.comb(10,i) for i in range(4))/2**10) < 1e-12,
      f"got {mcnemar(3,7):.6f} expect {2*sum(math.comb(10,i) for i in range(4))/2**10:.6f}")
check("symmetry mcnemar(5,8)==mcnemar(8,5)", mcnemar(5, 8) == mcnemar(8, 5))
check("b==c -> p==1", mcnemar(4, 4) == 1.0, f"got {mcnemar(4,4)}")
check("b=c=0 -> nan", math.isnan(mcnemar(0, 0)))
check("mcnemar(0,20) tiny", abs(mcnemar(0, 20) - 2/2**20) < 1e-15, f"got {mcnemar(0,20):.3e}")
# central-term inclusion: odd n has no central term issue; even n with k=n/2 must give 1
check("mcnemar(6,6)==1", mcnemar(6, 6) == 1.0)
# binom_two_sided at p=1/3 (used for vs-chance elsewhere): min-likelihood method.
# k=3,n=3: pmf(3)=1/27 is the unique minimum -> p = 1/27 (scipy.binomtest agrees)
check("binom_two_sided(3,3,1/3) = 1/27 (min-likelihood)", abs(binom_two_sided(3, 3) - 1/27) < 1e-12,
      f"got {binom_two_sided(3,3):.6f}")
# grid check: at p=0.5 the min-likelihood method == min(1, 2*smaller-tail) by symmetry
def two_min_tail(k, n):
    lo = sum(math.comb(n, i) for i in range(0, min(k, n-k)+1)) / 2**n
    return min(1.0, 2*lo)
grid_bad = [(b, c) for b in range(0, 13) for c in range(0, 13) if b+c > 0
            and abs(mcnemar(b, c) - two_min_tail(min(b, c), b+c)) > 1e-12]
check("mcnemar == 2*min-tail on full 0..12 x 0..12 grid", not grid_bad, str(grid_bad[:5]))

# ---------------- (2)+(3) hand-built confusion tests ----------------
print("\n== (2)(3) metrics_from_conf / committed_only_acc ==")
conf = Counter({("in","in"):10, ("in","out"):2, ("in","undec"):3,
                ("out","in"):1, ("out","out"):7, ("out","undec"):2,
                ("undec","in"):4, ("undec","out"):0, ("undec","undec"):6})
m = D.metrics_from_conf(conf)
tot = 35; acc3_hand = (10+7+6)/35
check("acc3 = diag/total", abs(m["acc3"] - acc3_hand) < 1e-12, f"got {m['acc3']:.6f} expect {acc3_hand:.6f}")
# macroF1 by hand: in: tp=10 fp=5 fn=5 -> P=R=2/3 F=2/3 ; out: tp=7 fp=2 fn=3 -> P=7/9 R=0.7 F=2*0.5444/1.4778
f_in = 2*(10/15)*(10/15)/((10/15)+(10/15))
f_out = 2*(7/9)*(7/10)/((7/9)+(7/10))
f_ud = 2*(6/11)*(6/10)/((6/11)+(6/10))
check("macroF1 hand (all 3 classes present)", abs(m["macroF1"] - (f_in+f_out+f_ud)/3) < 1e-12,
      f"got {m['macroF1']:.6f} expect {(f_in+f_out+f_ud)/3:.6f}")
co, ncom = G.committed_only_acc(conf)
check("committed_only = (10+7)/25", abs(co - 17/25) < 1e-12 and ncom == 25,
      f"got {co:.4f} n={ncom} expect 0.68 n=25")
# absent-class handling: no undec in gold AND prediction -> class dropped from macroF1
conf2 = Counter({("in","in"):5, ("in","out"):1, ("out","in"):2, ("out","out"):4})
m2 = D.metrics_from_conf(conf2)
f_in2 = 2*(5/7)*(5/6)/((5/7)+(5/6)); f_out2 = 2*(4/5)*(4/6)/((4/5)+(4/6))
check("macroF1 skips absent class", abs(m2["macroF1"] - (f_in2+f_out2)/2) < 1e-12,
      f"got {m2['macroF1']:.6f} expect {(f_in2+f_out2)/2:.6f}")
# class present in gold only (all missed): must be INCLUDED with F1=0
conf3 = Counter({("in","in"):5, ("undec","in"):3})
m3 = D.metrics_from_conf(conf3)
f_in3 = 2*(5/8)*1/((5/8)+1)
check("gold-only class included as F1=0", abs(m3["macroF1"] - (f_in3+0)/2) < 1e-12,
      f"got {m3['macroF1']:.6f} expect {(f_in3)/2:.6f}")
# committed-only counts undec-prediction-on-committed as WRONG (chance for 3-way guesser = 1/3)
conf4 = Counter({("in","undec"):10, ("out","undec"):10})
co4, n4 = G.committed_only_acc(conf4)
check("undec pred on committed = wrong", co4 == 0.0 and n4 == 20, f"got {co4} n={n4}")

# ---------------- (4)+(5) replicate smoke fold 0 ----------------
print("\n== (5) replicate smoke fold 0 from stored rules ==")
smoke = json.load(open(os.path.join(HERE, "results", "unified_smoke.json")))
meta = smoke["final"]; frec = meta["folds"][0]
recs = U.load_pooled("final")
check("n_responses meta", meta["n_responses"] == sum(len(r["labels"]) for r in recs) == 495,
      f"meta {meta['n_responses']} recomputed {sum(len(r['labels']) for r in recs)}")
check("n_participants meta", meta["n_participants"] == len(recs), f"{meta['n_participants']} vs {len(recs)}")
folds = U.shared_folds(recs, 5)
test = folds[0]; train = [r for j, f in enumerate(folds) if j != 0 for r in f]
check("fold0 n_train matches", frec["n_train"] == len(train), f"{frec['n_train']} vs {len(train)}")
cells = U.dedup_weighted(train)
negs, neg_w = U.shared_negatives(train, meta["max_neg"])
check("fold0 n_cells/n_negs/neg_w match", frec["n_cells"] == len(cells) and frec["n_negs"] == len(negs)
      and frec["neg_w"] == neg_w, f"json ({frec['n_cells']},{frec['n_negs']},{frec['neg_w']}) vs ({len(cells)},{len(negs)},{neg_w})")
check("neg mass ~ pos mass", abs(neg_w*len(negs) - 100*len(train)) <= len(negs)//2 + 1,
      f"neg mass {neg_w*len(negs)} vs pos mass {100*len(train)}")

rules_by_arm = {a: frec["arms"][a]["rules"] for a in U.LEARNERS}
conf_r = {(a, rd): Counter() for a in U.ARMS for rd in U.READINGS}
paired_r = {(a, rd): [] for a in U.ARMS for rd in ("skeptical", "credulous")}
byver = {(a, rd): defaultdict(Counter) for a in U.ARMS for rd in U.READINGS}
n_test_labels = 0
for r in test:
    n_test_labels += len(r["labels"])
    preds = {}
    for arm in U.ARMS:
        for rd in U.READINGS:
            p = U.predict_arm(arm, rules_by_arm.get(arm), r["args"], r["attacks"], rd)
            sc = D.score(p, r["labels"])
            conf_r[(arm, rd)] += sc
            byver[(arm, rd)][r["version"]] += sc
            if rd in ("skeptical", "credulous"):
                preds[(arm, rd)] = p
    for a_, h in r["labels"].items():
        for arm in U.ARMS:
            for rd in ("skeptical", "credulous"):
                paired_r[(arm, rd)].append(1 if preds[(arm, rd)].get(a_, "undec") == h else 0)

tab = meta["table"]
check("test-label count == table n", all(tab[a][rd]["n"] == n_test_labels
      for a in U.ARMS for rd in U.READINGS), f"n_test_labels={n_test_labels}")

# recompute the whole table and diff cell-by-cell
tab_r = U._table(conf_r, paired_r)
mism = []
for arm in U.ARMS:
    for rd in U.READINGS:
        for k in ("acc3", "committed_only", "n_committed", "n"):
            a, b = tab[arm][rd][k], tab_r[arm][rd][k]
            if a != b:
                mism.append(f"{arm}/{rd}/{k}: json={a} recomputed={b}")
    for k, v in tab[arm].items():
        if k.startswith("mcnemar"):
            if tab_r[arm].get(k) != v:
                mism.append(f"{arm}/{k}: json={v} recomputed={tab_r[arm].get(k)}")
check("recomputed _table == stored table (every cell)", not mism, "; ".join(mism[:8]))
check("best textbook matches", tab["_best_textbook_skeptical"] == tab_r["_best_textbook_skeptical"],
      f"{tab['_best_textbook_skeptical']} vs {tab_r['_best_textbook_skeptical']}")

# independent (non-_table) recomputation of McNemar discordants for each learner arm
bt = tab["_best_textbook_skeptical"]
for arm in U.LEARNERS:
    for rd in ("skeptical", "credulous"):
        a1, a2 = paired_r[(arm, rd)], paired_r[(bt, rd)]
        b = sum(1 for x, y in zip(a1, a2) if x and not y)
        c = sum(1 for x, y in zip(a1, a2) if y and not x)
        j = tab[arm][f"mcnemar_{rd}_vs_{bt}"]
        check(f"McNemar raw-pred {arm}/{rd}: b={b} c={c} p={mcnemar(b,c):.6f}",
              j["learner_only"] == b and j["textbook_only"] == c and abs(j["p"] - round(mcnemar(b, c), 6)) < 1e-9,
              f"json b={j['learner_only']} c={j['textbook_only']} p={j['p']}")
        # consistency: b - c must equal (#learner-correct - #tb-correct)
        check(f"b-c == ncorrect diff {arm}/{rd}", (b - c) == (sum(a1) - sum(a2)),
              f"b-c={b-c} diff={sum(a1)-sum(a2)}")
        # paired sequence sums must reproduce acc3
        check(f"paired acc == conf acc3 {arm}/{rd}",
              abs(sum(a1)/len(a1) - D.metrics_from_conf(conf_r[(arm, rd)])["acc3"]) < 1e-12,
              f"paired {sum(a1)}/{len(a1)}")

# stored 'conf' dump vs recomputed confusions + counts sum to n + committed bound
print("\n== (5b) stored conf dump consistency ==")
conf_json = meta["conf"]
bad = []
for (arm, rd), c in conf_r.items():
    stored = Counter({tuple(k.split(">")): v for k, v in conf_json[f"{arm}|{rd}"].items()})
    if stored != c:
        bad.append(f"{arm}|{rd}")
check("stored conf == recomputed conf (all 27 arm x reading)", not bad, ",".join(bad))
for (arm, rd) in conf_r:
    n = sum(conf_r[(arm, rd)].values())
    co, ncom = G.committed_only_acc(conf_r[(arm, rd)])
    assert n == n_test_labels and ncom <= n
print(f"all confusions sum to {n_test_labels}; n_committed=45 <= 72 everywhere")
hum = Counter()
for r in test:
    hum += Counter(r["labels"].values())
check("n_committed == human in+out in fold-0 test", hum["in"] + hum["out"] == 45,
      f"human marginals {dict(hum)}")

# ---------------- (4) pooling: sum-correct/sum-total, not mean of means ----------------
print("\n== (4) response-weighted pooling ==")
for arm in ("cf2", "ilasp_maxv1", "fastlas_opl"):
    for rd in ("skeptical", "credulous"):
        parts = byver[(arm, rd)]
        sum_cor = sum(sum(c[(k, k)] for k in D.CLASSES) for c in parts.values())
        sum_tot = sum(sum(c.values()) for c in parts.values())
        pooled = D.metrics_from_conf(conf_r[(arm, rd)])["acc3"]
        mean_of_means = sum(D.metrics_from_conf(c)["acc3"] for c in parts.values()) / len(parts)
        check(f"pooled acc3 {arm}/{rd} == sumcor/sumtot", abs(pooled - sum_cor/sum_tot) < 1e-12,
              f"pooled={pooled:.4f} sum={sum_cor}/{sum_tot} mean-of-cond-means={mean_of_means:.4f} "
              f"(conds n={[sum(c.values()) for c in parts.values()]})")

# ---------------- (6) caveat quantification: clustering of discordant pairs ----------------
print("\n== (6) McNemar independence caveat: within-cell duplication ==")
# responses inside one (graph,labelling) cell share identical predictions AND identical human
# labels -> identical (x,y) correctness pattern -> discordant pairs are duplicated within cells.
cellid = []
for r in test:
    key = (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))
    for a_ in r["labels"]:
        cellid.append((key, a_))  # per-argument granularity, tagged by cell
n_cells_test = len({k for k, _ in cellid})
print(f"fold-0 test: {n_test_labels} responses from {len(test)} participants, "
      f"{n_cells_test} distinct (graph,labelling) cells")
for arm in U.LEARNERS:
    a1, a2 = paired_r[(arm, "credulous")], paired_r[(bt, "credulous")]
    disc_resp = [(cellid[i][0], cellid[i][1], a1[i], a2[i]) for i in range(len(a1)) if a1[i] != a2[i]]
    b_resp = sum(1 for _, _, x, y in disc_resp if x)
    c_resp = len(disc_resp) - b_resp
    # collapse to unique (cell, arg) discordant units
    uniq = {}
    for key, a_, x, y in disc_resp:
        uniq[(key, a_)] = (x, y)
    b_u = sum(1 for x, y in uniq.values() if x); c_u = len(uniq) - b_u
    print(f"  {arm}: response-level b={b_resp} c={c_resp} p={mcnemar(b_resp, c_resp):.4f}  |  "
          f"unique (cell,arg) units b={b_u} c={c_u} p={mcnemar(b_u, c_u):.4f}")

print("\n" + ("ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} FAILURES:\n" + "\n".join(FAIL)))
