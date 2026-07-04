#!/usr/bin/env python3
"""V2 diagnosis of the stable-gate failure.

H0: the harness machinery is fine; the failure is the PROJECTION-as-positive construction.
For multi-extension graphs the skeptical projection (undec where extensions disagree) matches
NO answer set of the true stable theory, and 0-extension graphs match nothing at all, so the
true theory is penalized on its own data and ILASP retreats to grounded-ish theories.

Test: positives = one stable EXTENSION per participant (round-robin over the graph's
extensions = the credulous generative model; real humans also emit ONE labelling each).
Held-out scoring vs the stable-skeptical projection (the recoverable target through the
harness's skeptical predict_arm path). Same U.dedup_weighted/shared_negatives/ilasp_fold.

Also quantifies H0 directly: how much penalty does the TRUE stable theory pay on the
projection positives vs the extension positives?
"""
import os, sys, time, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G

SEM = "stable"
TRUE_THEORY = ["in(V1) :- arg(V1); not defeated(V1).", "out(V1) :- defeated(V1)."]


def graphs_and_labs(recs):
    cache = {}
    for r in recs:
        key = (tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))
        if key not in cache:
            cache[key] = D.textbook_labellings(SEM, r["args"], r["attacks"])
    return cache


def build(mode):
    """mode='projection' (what the gate did) or 'extension' (credulous generative model)."""
    base = U.load_pooled("final")
    cache = graphs_and_labs(base)
    counters = Counter()
    out = []
    for r in base:
        key = (tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))
        labs = cache[key]
        if mode == "projection" or not labs:
            lab = D.project(labs, r["args"], "skeptical")
        else:
            lab = sorted(labs, key=lambda l: tuple(sorted(l.items())))[counters[key] % len(labs)]
            counters[key] += 1
        labels = {a: lab.get(a, "undec") for a in r["args"]}
        # test target is ALWAYS the skeptical projection (what predict_arm can emit)
        proj = D.project(labs, r["args"], "skeptical")
        out.append({"pid": r["pid"], "args": r["args"], "attacks": r["attacks"],
                    "labels": labels, "commit": D.committed(labels),
                    "target": {a: proj.get(a, "undec") for a in r["args"]}})
    return out


def coverage_of_true_theory(cells):
    """How many weighted positives does the TRUE stable theory fail to cover?
    Covered = SOME answer set (under the learning BG with choice rules) extends the example.
    We check with clingo: BG + theory + ctx + incl/excl as constraints."""
    import clingo
    bad_w = tot_w = 0
    for c in cells:
        prog = D.BG + "\n" + "\n".join(TRUE_THEORY) + "\n"
        prog += "".join(f"arg({a}). " for a in c["args"])
        prog += "".join(f"att({s},{t}). " for s, t in c["attacks"]) + "\n"
        for a in c["args"]:
            s = c["commit"].get(a)
            if s == "in":
                prog += f":- not in({a}). :- out({a}).\n"
            elif s == "out":
                prog += f":- not out({a}). :- in({a}).\n"
            else:
                prog += f":- in({a}). :- out({a}).\n"
        ctl = clingo.Control(["1", "--warn=none"])
        ctl.add("base", [], prog)
        ctl.ground([("base", [])])
        sat = ctl.solve().satisfiable
        tot_w += c["weight"]
        if not sat:
            bad_w += c["weight"]
    return bad_w, tot_w


def run(mode):
    recs = build(mode)
    folds = U.shared_folds(recs, 2)
    print(f"\n===== stable positives = {mode} =====")
    print(f"recs={len(recs)} folds={[len(f) for f in folds]}")
    conf = Counter()
    conf_true = Counter()
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, 150)
        bad_w, tot_w = coverage_of_true_theory(cells)
        print(f" fold {fi}: train={len(train)} cells={len(cells)} negs={len(negs)} neg_w={neg_w} | "
              f"TRUE stable theory uncovered pos-mass {bad_w}/{tot_w}")
        t0 = time.time()
        rules, to = U.ilasp_fold(cells, negs, neg_w, 240)
        print(f"   ilasp {time.time()-t0:.1f}s TO={to} rules:")
        for rl in (rules or ["(EMPTY)"]):
            print(f"      {rl}")
        for r in test:
            p = U.predict_arm("ilasp_maxv1", rules, r["args"], r["attacks"], "skeptical")
            conf += D.score(p, r["target"])
            pt = D.project(D.learned_labellings(TRUE_THEORY, r["args"], r["attacks"]), r["args"], "skeptical")
            conf_true += D.score(pt, r["target"])
    m = D.metrics_from_conf(conf)
    mt = D.metrics_from_conf(conf_true)
    errs = {f"{h}>{p}": n for (h, p), n in conf.items() if h != p}
    print(f" POOLED heldout vs stable-skeptical target: ilasp acc3={m['acc3']:.4f} "
          f"(n={m['n_args']}) GATE(>=0.95): {'PASS' if m['acc3'] >= 0.95 else 'FAIL'}  errors={errs}")
    print(f" (sanity: TRUE maxv=1 stable theory through same predict path: acc3={mt['acc3']:.4f})")
    return m["acc3"]


if __name__ == "__main__":
    a_ext = run("extension")
    a_proj = run("projection")
    print(f"\nSUMMARY: extension-positives acc3={a_ext:.4f} vs projection-positives acc3={a_proj:.4f}")
