#!/usr/bin/env python3
"""UNIFIED apples-to-apples Exp2 comparison. One harness, four arms, identical everything:

  ARMS: (1) 2022 textbook semantics (grounded/preferred/stable/complete/cf2, skeptical = the
        paper's reading, plus credulous);  (2) ILASP maxv=1;  (3) FastLAS OPL best-params
        (verifier, enrich, maxv=1);  (4) FastLAS NOPL best-params (verifier, enrich, maxv=1).

  APPLES-TO-APPLES GUARANTEES
  - DATA: 2022-faithful IndAF pool via discover_semantics.load_recs(graph="ind"): each
    participant's FINAL drawn graph (att_final = the paper's IndAF, for EVERY label phase),
    all-undecided participants KEPT (the paper counts them). Pooled across conditions A-G.
  - FOLDS: ONE leak-free cell-fold split (distinct (graph,labelling) cells never straddle
    train/test), computed once per phase and reused byte-identically by every learner.
  - EXAMPLES: identical deduped weighted positives (weight = 100 per pooled response) and an
    identical soft Hamming-1 negative list (same cap, same seed, same mass-balanced weight)
    fed to ILASP and both FastLAS arms.
  - SCORING: one code path: response-weighted pooled 3-valued confusions -> acc3 (chance 33.3%),
    COMMITTED-ONLY accuracy (human in/out only; strips free undec->undec; 2-class chance 50%),
    per reading (skeptical = 2022's; credulous; grounded-of-extensions), plus exact-binomial
    McNemar of each learner vs the best textbook on the same responses.
  - The 2022 paper's own IndAF numbers (PAPER dict) are printed alongside as external anchors.

  Usage:
    python3 unified_compare.py --smoke                      # 1 fold, short timeouts, sanity
    python3 unified_compare.py --phases final,first --out results/unified  # the full run
"""
import argparse, json, os, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
from apples_to_apples import mcnemar, PAPER

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")
READINGS = D.READINGS
LEARNERS = ("ilasp_maxv1", "fastlas_opl", "fastlas_nopl")
ARMS = LEARNERS + D.TEXTBOOK
MODES_MAXV1 = D.MODES.replace("#maxv(2).", "#maxv(1).")
assert "#maxv(1)." in MODES_MAXV1, "mode_declarations maxv replacement failed"
SEED = 20260703


# ---------------- data & folds (shared by every arm) ----------------
def load_pooled(phase):
    """2022-faithful IndAF pool: graph = att_final ALWAYS (the paper's IndAF), labels from
    `phase`, all-undec kept. n=495 responses (G/p2 has no final drawing; matches our validated
    IndAF baseline that reproduces the paper's column)."""
    recs = []
    for v in VERSIONS:
        for r in D.load_recs(v, graph="ind", label_phase=phase):
            r["version"] = v
            recs.append(r)
    return recs


def shared_folds(recs, k=5):
    return G.cell_folds(recs, k, seed=SEED)


def dedup_weighted(train):
    """Identical (graph, committed-labelling) positives merged into one weighted cell
    (weight = 100 per pooled response). Same cells feed ILASP and FastLAS."""
    cellw = {}
    for r in train:
        key = (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))
        if key not in cellw:
            cellw[key] = {"args": r["args"], "attacks": r["attacks"], "commit": r["commit"], "weight": 0}
        cellw[key]["weight"] += 100
    return list(cellw.values())


def shared_negatives(train, max_neg=150):
    """One negative list per fold, shared verbatim: soft Hamming-1 shell of the TRAIN commits,
    deterministic cap, PLUS one 'drop-all' (all-undec) negative per distinct train graph.
    The drop-alls pin TOTALITY: without them the H1 shell cannot separate a total semantics
    (stable) from a shorter less-committal theory, biasing every learner toward under-commitment
    (verified: ILASP stable recovery 0.92 -> 1.00 with them; grounded recovery unchanged).
    Skipped on graphs where some train participant IS all-undec (it would equal a positive).
    Weight balanced so total neg mass == total pos mass."""
    negs = G.shell_of(train)
    if max_neg and len(negs) > max_neg:
        import random
        negs = [negs[i] for i in sorted(random.Random(SEED).sample(range(len(negs)), max_neg))]
    pos_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in train}
    seen_graphs = set()
    for r in train:
        gk = tuple(sorted(r["attacks"]))
        if gk in seen_graphs or (gk, ()) in pos_keys:
            continue
        seen_graphs.add(gk)
        negs.append((r["args"], r["attacks"], {}))
    pos_mass = 100 * len(train)
    neg_w = max(1, round(pos_mass / len(negs))) if negs else 100
    return negs, neg_w


# ---------------- the three learner arms ----------------
def ilasp_fold(cells, negs, neg_w, timeout):
    """ILASP maxv=1: learns in/out rules over the Dung vocabulary (choice-rule BG for learning,
    BG_PREDICT for prediction — all the audited fixes active). Soft positives AND soft negatives."""
    pos = [D.render_example("pos", f"p{i}", c["weight"], c["args"], c["attacks"], c["commit"])
           for i, c in enumerate(cells)]
    neg = [D.render_example("neg", f"n{j}", neg_w, ar, at, ng)
           for j, (ar, at, ng) in enumerate(negs)]
    task = "\n".join(pos + neg) + "\n\n" + D.BG + "\n\n" + MODES_MAXV1 + "\n"
    rules = D.run_ilasp(task, timeout=timeout)
    timed_out = rules == ["% TIMEOUT"]
    return ([] if timed_out else rules), timed_out


def fastlas_task(cells, negs, neg_w, maxv=1, enrich=True):
    """FastLAS verifier task from the SAME weighted cells + negative list as ILASP."""
    lines = [G._feat_bg(enrich), "", "#modeh(violated)."] + G._MODEB + (G._MODEB_ENR if enrich else [])
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


def fastlas_fold(cells, negs, neg_w, mode, timeout, maxv=1, enrich=True):
    task = fastlas_task(cells, negs, neg_w, maxv=maxv, enrich=enrich)
    rules = G.run_fastlas(task, mode=mode, timeout=timeout)
    timed_out = rules is None
    return ([] if timed_out else rules), timed_out


def predict_arm(arm, rules, args, attacks, reading):
    if arm == "ilasp_maxv1":
        labs = D.learned_labellings(rules, args, attacks) if rules else []
        if not labs:
            return {a: "undec" for a in args}
        return D.project(labs, args, reading)
    if arm.startswith("fastlas"):
        return G.predict(rules, args, attacks, reading, enrich=True)
    return D.project(D.textbook_labellings(arm, args, attacks), args, reading)


# ---------------- scoring (one path for every arm) ----------------
def run_phase(phase, k, timeouts, max_neg, out_path, state, smoke=False):
    recs = load_pooled(phase)
    folds = shared_folds(recs, k)
    meta = {"phase": phase, "n_responses": sum(len(r["labels"]) for r in recs),
            "n_participants": len(recs), "n_folds": len(folds), "max_neg": max_neg,
            "timeouts_cfg": timeouts, "folds": [], "status": "running"}
    state[phase] = meta
    conf = {(a, rd): Counter() for a in ARMS for rd in READINGS}
    # paired per-response correctness (skeptical + credulous) for McNemar; pair_keys aligns the
    # sequences and enables the cell-level (unique (graph,labelling,arg)) robustness McNemar.
    paired = {(a, rd): [] for a in ARMS for rd in ("skeptical", "credulous")}
    pair_keys = []
    nfolds = 1 if smoke else len(folds)
    for fi in range(nfolds):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = dedup_weighted(train)
        negs, neg_w = shared_negatives(train, max_neg)
        frec = {"fold": fi, "n_train": len(train), "n_cells": len(cells),
                "n_negs": len(negs), "neg_w": neg_w, "arms": {}}
        rules_by_arm = {}
        for arm in LEARNERS:
            t0 = time.time()
            if arm == "ilasp_maxv1":
                rules, to = ilasp_fold(cells, negs, neg_w, timeouts["ilasp"])
            elif arm == "fastlas_opl":
                rules, to = fastlas_fold(cells, negs, neg_w, "opl", timeouts["opl"])
            else:
                rules, to = fastlas_fold(cells, negs, neg_w, "nopl", timeouts["nopl"])
            rules_by_arm[arm] = rules
            frec["arms"][arm] = {"secs": round(time.time() - t0, 1), "timed_out": to,
                                 "n_rules": len(rules), "rules": rules}
        for r in test:
            preds = {}
            for arm in ARMS:
                for rd in READINGS:
                    p = predict_arm(arm, rules_by_arm.get(arm), r["args"], r["attacks"], rd)
                    conf[(arm, rd)] += D.score(p, r["labels"])
                    if rd in ("skeptical", "credulous"):
                        preds[(arm, rd)] = p
            cellk = (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))
            for a_, h in r["labels"].items():
                pair_keys.append((cellk, a_))
                for arm in ARMS:
                    for rd in ("skeptical", "credulous"):
                        paired[(arm, rd)].append(1 if preds[(arm, rd)].get(a_, "undec") == h else 0)
        meta["folds"].append(frec)
        meta["running"] = _table(conf, paired, pair_keys)
        _flush(out_path, state)
        larm = {a: frec["arms"][a] for a in LEARNERS}
        print(f"[{phase}] fold {fi+1}/{len(folds)} "
              + " ".join(f"{a}:{v['secs']}s({v['n_rules']}r{'!TO' if v['timed_out'] else ''})" for a, v in larm.items()),
              flush=True)
    meta["status"] = "done"
    meta["table"] = _table(conf, paired, pair_keys)
    meta["conf"] = {f"{a}|{rd}": {f"{h}>{p}": n for (h, p), n in c.items()}
                    for (a, rd), c in conf.items()}
    _flush(out_path, state)
    return meta


# PRE-REGISTERED McNemar comparator: cf2, the 2022 paper's IndAF winner. Fixed a priori so the
# p-values carry no best-of-5 winner's-curse selection on the test data.
COMPARATOR = "cf2"


def _mcnemar_counts(a1, a2):
    b = sum(1 for x, y in zip(a1, a2) if x and not y)
    c_ = sum(1 for x, y in zip(a1, a2) if y and not x)
    p = mcnemar(b, c_)
    return {"learner_only": b, "textbook_only": c_,
            "p": (1.0 if b == c_ == 0 else round(p, 6))}


def _table(conf, paired, pair_keys):
    out = {}
    for arm in ARMS:
        row = {}
        for rd in READINGS:
            c = conf[(arm, rd)]
            if not c:
                continue
            co, ncom = G.committed_only_acc(c)
            row[rd] = {"acc3": round(D.metrics_from_conf(c)["acc3"], 4),
                       "committed_only": round(co, 4), "n_committed": ncom,
                       "n": sum(c.values())}
        if arm in LEARNERS:
            for rd in ("skeptical", "credulous"):
                a1, a2 = paired[(arm, rd)], paired[(COMPARATOR, rd)]
                if a1 and len(a1) == len(a2):
                    # response-level (the 2022 pooled convention; anti-conservative under the
                    # within-cell duplication) + cell-level robustness (unique (graph,lab,arg)).
                    row[f"mcnemar_{rd}_vs_{COMPARATOR}"] = _mcnemar_counts(a1, a2)
                    first_ix = {}
                    for i, k in enumerate(pair_keys):
                        first_ix.setdefault(k, i)
                    ix = sorted(first_ix.values())
                    row[f"mcnemar_cell_{rd}_vs_{COMPARATOR}"] = _mcnemar_counts(
                        [a1[i] for i in ix], [a2[i] for i in ix])
        out[arm] = row
    out["_comparator"] = COMPARATOR
    return out


def _flush(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def print_report(state):
    for phase, meta in state.items():
        if not isinstance(meta, dict) or "table" not in meta and "running" not in meta:
            continue
        t = meta.get("table") or meta.get("running")
        print(f"\n===== phase={phase} · IndAF pool · n_responses={meta['n_responses']} · "
              f"{len(meta['folds'])}/{meta['n_folds']} folds =====")
        pr = PAPER.get(("ind", phase), {})
        print(f"  2022 PAPER IndAF-{phase} (%correct, skeptical): "
              + "  ".join(f"{k}={v}" for k, v in pr.items()))
        print(f"  {'arm':<14}{'skept_acc3':<12}{'cred_acc3':<11}{'cred_committedOnly':<20}{'skept_committedOnly'}")
        for arm in ARMS:
            row = t.get(arm, {})
            if not row:
                continue
            s, c = row.get("skeptical", {}), row.get("credulous", {})
            print(f"  {arm:<14}{s.get('acc3', float('nan')):<12.3f}{c.get('acc3', float('nan')):<11.3f}"
                  f"{c.get('committed_only', float('nan')):<20.3f}{s.get('committed_only', float('nan')):.3f}")
        bt = t.get("_comparator", COMPARATOR)
        for arm in LEARNERS:
            for rd in ("skeptical", "credulous"):
                m = t.get(arm, {}).get(f"mcnemar_{rd}_vs_{bt}")
                mc = t.get(arm, {}).get(f"mcnemar_cell_{rd}_vs_{bt}")
                if m:
                    print(f"  McNemar {arm}|{rd} vs {bt} (pre-registered): "
                          f"learner-only {m['learner_only']} tb-only {m['textbook_only']} p={m['p']}"
                          + (f"  [cell-level: {mc['learner_only']}/{mc['textbook_only']} p={mc['p']}]" if mc else ""))
        print("  (chance: acc3 33.3% · committed-only: 33.3% for a 3-way guesser, 50% = coin-flip among committed)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phases", default="final,first")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--max-neg", type=int, default=150)
    ap.add_argument("--ilasp-timeout", type=int, default=1800)
    ap.add_argument("--opl-timeout", type=int, default=300)
    ap.add_argument("--nopl-timeout", type=int, default=600)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "unified"))
    ap.add_argument("--smoke", action="store_true", help="1 fold, short timeouts")
    a = ap.parse_args()
    timeouts = {"ilasp": a.ilasp_timeout, "opl": a.opl_timeout, "nopl": a.nopl_timeout}
    if a.smoke:
        timeouts = {"ilasp": 240, "opl": 60, "nopl": 120}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out_path = a.out + ".json"
    state = {"started": time.strftime("%Y-%m-%d %H:%M"), "args": vars(a)}
    for phase in a.phases.split(","):
        run_phase(phase, a.folds, timeouts, a.max_neg, out_path, state, smoke=a.smoke)
    state["status"] = "ALL DONE"
    _flush(out_path, state)
    print_report(state)
    print(f"\nresults -> {out_path}")


if __name__ == "__main__":
    main()
