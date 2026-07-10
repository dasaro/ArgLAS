#!/usr/bin/env python3
"""Apples-to-apples replication of the 2022 PLOS comparison (Guillaume, Cramer, van der
Torre, Schiltz, doi:10.1371/journal.pone.0273225), with the LEARNED predictor as a new
entrant.

Their method, reproduced exactly:
  - Each semantics -> a 3-valued SKEPTICAL justification status per argument (Strongly
    Accepted / Strongly Rejected / Undecided = in/out/undec) on a chosen AF.
  - Human response = accept/reject/undecided per argument.
  - Metric = % CORRECT (exact 3-valued match), pooled over all responses, vs 33.3% chance
    (exact two-sided binomial test).
  - 9 textbook predictors = {grounded, preferred, CF2} x {BaseAF=gold, IndAF=own att_final,
    GroupAF=att_group}, x response phase {first, group, final}.  (We also report stable +
    complete.)  Aggregate layer: per-argument majority choice + chi-square(2) vs uniform.
  - Predictor-vs-predictor significance: binomial on the responses where the two predictors
    DISAGREE (McNemar).
We add LEARNED (held-out, cell-level CV) read SKEPTICALLY (apples-to-apples) and CREDULOUSLY
(one step past 2022, since humans reason credulously), scored with the SAME % correct.

  python3 apples_to_apples.py reproduce                     # textbook table + Table-2 check
  python3 apples_to_apples.py learned --graph gold --phase final --out runs/ata_gold_final
"""
import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import discover_semantics as D
from extract_labeled_aafs import read_xlsx_sheet

VERSIONS = ["A", "B", "C", "D", "E", "F", "G"]
TB = ["grounded", "preferred", "stable", "complete", "cf2"]
PAPER_TB = ["grounded", "preferred", "cf2"]
# Paper Table 2 % correct (BaseAF / IndAF / GroupAF) x {first, group, final}. "-" = not reported.
PAPER = {
    ("gold", "first"): {"grounded": 44.4, "preferred": 57.8, "cf2": 59.6},
    ("gold", "group"): {"grounded": 49.4, "preferred": 68.6, "cf2": 73.6},
    ("gold", "final"): {"grounded": 49.2, "preferred": 68.0, "cf2": 72.4},
    ("ind", "first"): {"grounded": 48.6, "preferred": 54.6, "cf2": 55.4},
    ("ind", "final"): {"grounded": 55.4, "preferred": 63.4, "cf2": 63.6},
    ("group", "first"): {"grounded": 48.6, "preferred": 55.2, "cf2": 56.4},
    ("group", "group"): {"grounded": 57.6, "preferred": 67.8, "cf2": 69.8},
    ("group", "final"): {"grounded": 48.6, "preferred": 55.2, "cf2": 56.4},
}


# ---- statistics (stdlib closed forms) ----
def binom_two_sided(k, n, p=1.0 / 3.0):
    if n == 0:
        return float("nan")
    pmf = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    thr = pmf[k] * (1 + 1e-9)
    return min(1.0, sum(x for x in pmf if x <= thr))


def chi2_uniform(counts):
    n = sum(counts)
    k = len(counts)
    if n == 0:
        return 0.0, k - 1, float("nan")
    exp = n / k
    stat = sum((c - exp) ** 2 / exp for c in counts)
    df = k - 1
    p = math.exp(-stat / 2) if df == 2 else (math.erfc(math.sqrt(stat / 2)) if df == 1 else float("nan"))
    return stat, df, p


def mcnemar(b, c):
    """Two-sided exact binomial on the discordant pairs (b learned-only-correct, c
    textbook-only-correct)."""
    n = b + c
    return binom_two_sided(min(b, c), n, 0.5) if n else float("nan")


# ---- textbook status (no training) ----
def textbook_status(sem, args, attacks):
    return D.project(D.textbook_labellings(sem, args, attacks), args, "skeptical")


def textbook_responses(sem, graph, phase):
    """Per (participant, arg) tuples (human, predicted) pooled over all conditions."""
    out = []
    for v in VERSIONS:
        for r in D.load_recs(v, graph, phase):
            st = textbook_status(sem, r["args"], r["attacks"])
            for a, h in r["labels"].items():
                out.append((v, r["pid"], a, h, st.get(a, "undec")))
    return out


def pct_correct(rows):
    n = len(rows)
    k = sum(1 for (_, _, _, h, p) in rows if h == p)
    return (100.0 * k / n if n else float("nan")), k, n


def cmd_reproduce(a):
    print("=" * 96)
    print("APPLES-TO-APPLES vs 2022 (Guillaume et al.) — textbook %correct, pooled over all responses")
    print("skeptical justification status; chance = 33.3%; * p<.05 vs chance (exact binomial)")
    print("=" * 96)
    for graph, glabel in [("gold", "BaseAF"), ("ind", "IndAF"), ("group", "GroupAF")]:
        print(f"\n### {glabel} ({graph}) ###")
        print(f"{'phase':<8}" + "".join(f"{s:<22}" for s in PAPER_TB) + "stable  complete")
        for phase in ("first", "group", "final"):
            cells = []
            extra = []
            for sem in PAPER_TB:
                pc, k, n = pct_correct(textbook_responses(sem, graph, phase))
                p = binom_two_sided(k, n)
                paper = PAPER.get((graph, phase), {}).get(sem)
                star = "*" if (p == p and p < 0.05) else " "
                tag = f"(2022:{paper})" if paper is not None else ""
                cells.append(f"{pc:5.1f}{star}{tag:<11}")
            for sem in ("stable", "complete"):
                pc, k, n = pct_correct(textbook_responses(sem, graph, phase))
                extra.append(f"{pc:5.1f}")
            print(f"{phase:<8}" + "".join(f"{c:<22}" for c in cells) + "  ".join(extra))
    # reproduction error vs paper on the gold/BaseAF cells
    print("\n### Table-2 reproduction error (ours - 2022), gold BaseAF ###")
    maxerr = 0.0
    for phase in ("first", "group", "final"):
        for sem in PAPER_TB:
            pc, k, n = pct_correct(textbook_responses(sem, "gold", phase))
            paper = PAPER[("gold", phase)][sem]
            err = pc - paper
            maxerr = max(maxerr, abs(err))
            print(f"  {phase:<6} {sem:<10} ours={pc:5.1f}  2022={paper:5.1f}  Δ={err:+5.1f}")
    print(f"  >>> max |Δ| = {maxerr:.1f} pp  ({'REPRODUCES' if maxerr < 5 else 'CHECK'} the published table)")
    # aggregate / majority layer (per condition, final phase)
    print("\n### Majority layer (final phase): per-argument human majority + chi2(2) vs uniform ###")
    for v in VERSIONS:
        recs = D.load_recs(v, "gold", "final")
        per = defaultdict(Counter)
        for r in recs:
            for a, h in r["labels"].items():
                per[a][h] += 1
        line = []
        for a in sorted(per):
            c = per[a]
            counts = [c.get("in", 0), c.get("out", 0), c.get("undec", 0)]
            maj = max(("in", "out", "undec"), key=lambda x: c.get(x, 0))
            stat, df, p = chi2_uniform(counts)
            line.append(f"{a}:{maj}{'*' if p < 0.05 else ''}(χ²={stat:.1f})")
        print(f"  {v}: " + "  ".join(line))


# ---- learned predictor (held-out, cell-level CV) ----
def cell_folds(recs, k, seed=20260627):
    cells = defaultdict(list)
    for r in recs:
        key = (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))
        cells[key].append(r)
    keys = sorted(cells)
    if len(keys) < 2:
        return None  # degenerate: cannot hold out
    k = min(k, len(keys))
    folds = [[] for _ in range(k)]
    for i, key in enumerate(keys):
        folds[(i * 7 + seed) % k].extend(cells[key])
    return [f for f in folds if f]


def cmd_learned(a):
    os.makedirs(a.out, exist_ok=True)
    prog = os.path.join(a.out, "progress.json")
    results = {}
    st = {"graph": a.graph, "phase": a.phase, "versions": VERSIONS, "total": len(VERSIONS),
          "done": 0, "current": None, "start": time.time(), "status": "running"}
    json.dump(st, open(prog, "w"))
    for v in VERSIONS:
        recs = D.load_recs(v, a.graph, a.phase)
        folds = cell_folds(recs, a.folds)
        st["current"] = v
        if folds is None:
            results[v] = {"n_cells": 1, "note": "degenerate (1 distinct labelling) — no held-out"}
            st["done"] += 1
            json.dump(st, open(prog, "w"))
            continue
        # collect per-response predictions held-out
        rows = {"learned_skeptical": [], "learned_credulous": []}
        tb_rows = {s: [] for s in PAPER_TB}
        for fi in range(len(folds)):
            test = folds[fi]
            train = [r for j, f in enumerate(folds) if j != fi for r in f if r["commit"]]
            if not train or not test:
                continue
            rules = D.run_ilasp(D.build_task(train)[0], timeout=a.ilasp_timeout)
            for r in test:
                labs = D.learned_labellings(rules, r["args"], r["attacks"])
                sk = D.project(labs, r["args"], "skeptical")
                cr = D.project(labs, r["args"], "credulous")
                tbst = {s: textbook_status(s, r["args"], r["attacks"]) for s in PAPER_TB}
                for arg, h in r["labels"].items():
                    rows["learned_skeptical"].append((h, sk.get(arg, "undec")))
                    rows["learned_credulous"].append((h, cr.get(arg, "undec")))
                    for s in PAPER_TB:
                        tb_rows[s].append((h, tbst[s].get(arg, "undec")))
        out = {"n_cells": len(folds)}
        for name, rr in rows.items():
            k = sum(1 for (h, p) in rr if h == p)
            out[name] = {"pct": 100.0 * k / len(rr) if rr else float("nan"), "k": k, "n": len(rr),
                         "binom_p": binom_two_sided(k, len(rr))}
        for s in PAPER_TB:
            rr = tb_rows[s]
            k = sum(1 for (h, p) in rr if h == p)
            out["tb_" + s] = {"pct": 100.0 * k / len(rr) if rr else float("nan"), "k": k, "n": len(rr)}
        # McNemar vs the best textbook, computed for BOTH learned readings (skeptical is the
        # like-for-like apples-to-apples test; credulous is the favorable one-step-past read).
        best = max(PAPER_TB, key=lambda s: out["tb_" + s]["pct"])
        ts = tb_rows[best]
        out["best_textbook"] = best
        for rd in ("learned_skeptical", "learned_credulous"):
            lc = rows[rd]
            b = sum(1 for i in range(len(lc)) if lc[i][0] == lc[i][1] and ts[i][0] != ts[i][1])
            c = sum(1 for i in range(len(lc)) if lc[i][0] != lc[i][1] and ts[i][0] == ts[i][1])
            out[f"mcnemar_{rd}"] = {"learned_only_correct": b, "textbook_only_correct": c, "p": mcnemar(b, c)}
        results[v] = out
        st["done"] += 1
        json.dump(st, open(prog, "w"))
        json.dump(results, open(os.path.join(a.out, "results.json"), "w"))
        print(f"[done] {v} cells={out['n_cells']} | learned skep={out['learned_skeptical']['pct']:.1f}% "
              f"cred={out['learned_credulous']['pct']:.1f}% vs best-tb {best}={out['tb_'+best]['pct']:.1f}% "
              f"| McNemar(skep) p={out['mcnemar_learned_skeptical']['p']:.3f} (cred) p={out['mcnemar_learned_credulous']['p']:.3f}", flush=True)
    st["status"] = "done"
    json.dump(st, open(prog, "w"))
    print("ALL DONE")


# ---- POOLED own-graph (IndAF), cross-condition, confidence-weighted, cell-level CV ----
def pooled_cell_folds(recs, k, seed=20260627):
    cells = defaultdict(list)
    for r in recs:
        cells[(tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))].append(r)
    keys = sorted(cells)
    k = min(k, len(keys))
    folds = [[] for _ in range(k)]
    for i, key in enumerate(keys):
        folds[(i * 7 + seed) % k].extend(cells[key])
    return [f for f in folds if f]


def cmd_pooled(a):
    os.makedirs(a.out, exist_ok=True)
    prog = os.path.join(a.out, "progress.json")
    conf_lut = {(x["VERSION"], str(x["PARTICIPANT"]), x["ITEM"].strip().lower()): x["2ND_CONFIDENCE"]
                for x in read_xlsx_sheet(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "Raw_Data_original.xlsx"), "PART_B")}
    recs = []
    for v in VERSIONS:
        for r in D.load_recs(v, "ind", a.phase):  # ind = participant's own drawn graph (IndAF)
            part = r["pid"][1:]
            cs = [int(conf_lut[(v, part, arg)]) for arg in r["commit"]
                  if str(conf_lut.get((v, part, arg), "NA")) not in ("NA", "")]
            mc = (sum(cs) / len(cs)) if cs else 2.5
            r["version"] = v
            r["weight"] = 100 if a.no_confidence else max(1, int(round(100 * mc / 4.0)))
            recs.append(r)
    folds = pooled_cell_folds(recs, a.folds)
    preds = ("learned_skeptical", "learned_credulous") + tuple(TB)
    responses = []
    st = {"mode": "pooled", "phase": a.phase, "confidence": not a.no_confidence, "n_examples": len(recs),
          "total": len(folds), "done": 0, "start": time.time(), "status": "running"}
    json.dump(st, open(prog, "w"))
    for fi in range(len(folds)):
        test = folds[fi]
        train_raw = [r for j, f in enumerate(folds) if j != fi for r in f if r["commit"]]
        # dedup identical (graph, commit-labelling) examples into one weighted positive
        # (identical examples add no constraint to ILASP; weight = summed confidence mass).
        # Shrinks the task ~2x -> tractable, same learned theory.
        cellw = {}
        for r in train_raw:
            key = (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))
            if key not in cellw:
                cellw[key] = {"args": r["args"], "attacks": r["attacks"], "commit": r["commit"], "weight": 0}
            cellw[key]["weight"] += r["weight"]
        train = list(cellw.values())
        if train and test:
            rules = D.run_ilasp(D.build_task(train, max_neg=a.max_neg)[0], timeout=a.ilasp_timeout)
            for r in test:
                labs = D.learned_labellings(rules, r["args"], r["attacks"])
                sk = D.project(labs, r["args"], "skeptical")
                cr = D.project(labs, r["args"], "credulous")
                tbst = {s: textbook_status(s, r["args"], r["attacks"]) for s in TB}
                for arg, h in r["labels"].items():
                    responses.append({"cond": r["version"], "h": h,
                                      "learned_skeptical": sk.get(arg, "undec"),
                                      "learned_credulous": cr.get(arg, "undec"),
                                      **{s: tbst[s].get(arg, "undec") for s in TB}})
            print(f"[fold {fi+1}/{len(folds)}] trained on {len(train)} examples; {len(test)} held-out", flush=True)
        st["done"] += 1
        json.dump(st, open(prog, "w"))
        json.dump(responses, open(os.path.join(a.out, "responses.json"), "w"))

    def conf_of(rows, pred):
        c = Counter()
        for r in rows:
            c[(r["h"], r[pred])] += 1
        return c
    table = {p: {**D.metrics_from_conf(conf_of(responses, p))} for p in preds}
    best = max(TB, key=lambda s: table[s]["acc3"])
    out = {"n_examples": len(recs), "n_cells": len(folds), "n_responses": len(responses),
           "phase": a.phase, "confidence": not a.no_confidence, "best_textbook": best,
           "pooled": {p: {"pct_correct": table[p]["acc3"] * 100, "macroF1": table[p]["macroF1"],
                          "commit": table[p]["commit_rate"]} for p in preds}}
    for rd in ("learned_skeptical", "learned_credulous"):
        b = sum(1 for r in responses if r["h"] == r[rd] and r["h"] != r[best])
        c = sum(1 for r in responses if r["h"] != r[rd] and r["h"] == r[best])
        out[f"mcnemar_{rd}_vs_{best}"] = {"learned_only": b, "textbook_only": c, "p": mcnemar(b, c)}
    out["by_condition"] = {v: {p: D.metrics_from_conf(conf_of([r for r in responses if r["cond"] == v], p))["acc3"] * 100
                               for p in preds} for v in VERSIONS if any(r["cond"] == v for r in responses)}
    json.dump(out, open(os.path.join(a.out, "results.json"), "w"))
    st["status"] = "done"
    json.dump(st, open(prog, "w"))
    print(f"\n=== POOLED own-graph (IndAF) · phase={a.phase} · confidence={'on' if not a.no_confidence else 'off'} ===")
    print(f"examples={len(recs)}  cells={len(folds)}  held-out responses={len(responses)}")
    print(f"{'predictor':<20}{'%correct':<10}{'macroF1':<9}{'commit':<8}")
    for p in preds:
        t = out["pooled"][p]
        print(f"{p:<20}{t['pct_correct']:<10.1f}{t['macroF1']:<9.3f}{t['commit']:<8.2f}")
    print(f"best textbook = {best} ({out['pooled'][best]['pct_correct']:.1f}%)")
    for rd in ("learned_credulous", "learned_skeptical"):
        m = out[f"mcnemar_{rd}_vs_{best}"]
        print(f"McNemar {rd} vs {best}: p={m['p']:.3f} (learned-only {m['learned_only']}, tb-only {m['textbook_only']})")
    print("ALL DONE")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reproduce").set_defaults(fn=cmd_reproduce)
    pl = sub.add_parser("pooled")
    pl.add_argument("--phase", default="final", choices=("first", "group", "final"))
    pl.add_argument("--folds", type=int, default=5)
    pl.add_argument("--ilasp-timeout", type=int, default=2400)
    pl.add_argument("--max-neg", type=int, default=100, help="cap on sampled hard-negative shell per fold.")
    pl.add_argument("--no-confidence", action="store_true", help="uniform weights (ablation).")
    pl.add_argument("--out", default="/tmp/ata_pooled")
    pl.set_defaults(fn=cmd_pooled)
    lr = sub.add_parser("learned")
    lr.add_argument("--graph", default="gold", choices=("gold", "ind", "group"))
    lr.add_argument("--phase", default="final", choices=("first", "group", "final"))
    lr.add_argument("--folds", type=int, default=5)
    lr.add_argument("--ilasp-timeout", type=int, default=1800)
    lr.add_argument("--out", default="/tmp/ata")
    lr.set_defaults(fn=cmd_learned)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
