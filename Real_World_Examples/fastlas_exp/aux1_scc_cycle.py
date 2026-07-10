#!/usr/bin/env python3
"""aux1 "scc-cycle": SCC / cycle-structure AUXILIARY predicates for the FastLAS-OPL verifier.

Hypothesis (representability analysis): CF2 (the human-best semantics) commits INSIDE cyclic SCCs
based on cycle structure, and the base Dung vocabulary (in/out/undec/defended/attacked_by_in/
attacked/in_cycle) cannot express odd-cycle / same-SCC behaviour. We add PURELY STRUCTURAL
predicates (from `att` only) so a `violated` constraint can key on cycle membership.

We reuse the shared harness EXACTLY (unified_compare.load_pooled / shared_folds / dedup_weighted /
shared_negatives) and only swap in our own feature background + modeb, mirroring
unified_compare.fastlas_task / predict_arm so the pipeline is byte-identical to the baseline apart
from the aux predicates. Baseline = the SAME harness with enrich=True (in_cycle) and NO aux preds.

Candidate aux predicates (structural, from att):
  reach(X,Y)            transitive closure of att
  in_cycle(X)           reach(X,X)                       (already in baseline _FEATS_ENR)
  mutual(X)             X sits in a 2-cycle: att(X,Y),att(Y,X)
  in_long_cycle(X)      in a cycle but not a 2-cycle  -> proxy for odd/3-cycles (condition G)
  same_cycle(X,Y)       reach(X,Y),reach(Y,X)            (binary; needs maxv>=2 to use in a rule)

To keep FastLAS-OPL tractable we expose a SMALL set of extra modeb (<=4). We test three variants:
  V-mutual      : add mutual/1
  V-long        : add in_long_cycle/1
  V-both        : add mutual/1 + in_long_cycle/1        (the full family, 2 extra unary preds)
All keep in_cycle (baseline enrich) available too.
"""
import os, sys, time, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U

# ------------------------------------------------------------------ aux backgrounds
# baseline features (label-dependent, from a GIVEN labelling) -- identical to G._FEATS
_BASE = G._FEATS
# structural closure + in_cycle (identical to G._FEATS_ENR) -- always included so baseline==enrich
_CLOSURE = """reach(X, Y) :- att(X, Y).
reach(X, Z) :- att(X, Y), reach(Y, Z).
in_cycle(X) :- reach(X, X)."""

# aux predicate definitions (purely structural from att)
_AUX_MUTUAL = "mutual(X) :- att(X, Y), att(Y, X)."
# in a cycle but NOT via a 2-cycle: reach(X,X) holds but X is not in any 2-cycle
_AUX_LONG = "in_long_cycle(X) :- in_cycle(X), not mutual(X)."

# modeb for the aux preds (both polarities), unary over arg
_MB_MUTUAL = ["#modeb(mutual(var(arg))).", "#modeb(not mutual(var(arg)))."]
_MB_LONG = ["#modeb(in_long_cycle(var(arg))).", "#modeb(not in_long_cycle(var(arg)))."]

# baseline (enrich) modeb = the 11 base + in_cycle both polarities (== G._MODEB + G._MODEB_ENR)
_MB_BASE = G._MODEB + G._MODEB_ENR


def feat_bg(variant):
    """Full feature background for a variant: base label features + structural closure + aux defs."""
    bg = [_BASE, _CLOSURE]
    if variant in ("mutual", "both"):
        bg.append(_AUX_MUTUAL)
    if variant in ("long", "both"):
        # in_long_cycle needs mutual to be defined
        if variant == "long":
            bg.append(_AUX_MUTUAL)  # defined but not in modeb -> aux stays structural helper
        bg.append(_AUX_LONG)
    return "\n".join(bg)


def modeb(variant):
    mb = list(_MB_BASE)
    if variant in ("mutual", "both"):
        mb += _MB_MUTUAL
    if variant in ("long", "both"):
        mb += _MB_LONG
    return mb


def build_task(cells, negs, neg_w, variant, maxv=1):
    lines = [feat_bg(variant), "", "#modeh(violated)."] + modeb(variant)
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ prediction (mirrors G.predict)
_GEN = """0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- in(X), out(X)."""


def predict(rules, args, attacks, reading, variant):
    if not rules:
        return {a: "undec" for a in args}
    import clingo
    prog = "\n".join([_GEN, feat_bg(variant)] + list(rules) + [":- violated."])
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + "\n" + facts + "\n#show in/1.\n#show out/1.\n")
    ctl.ground([("base", [])])
    labs = []

    def on_model(m):
        ins = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "in"}
        ous = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "out"}
        labs.append({a: ("in" if a in ins else "out" if a in ous else "undec") for a in args})

    ctl.solve(on_model=on_model)
    return D.project(labs, args, reading)


# ------------------------------------------------------------------ CV harness (leak-free, shared)
def run_cv(phase="final", variant="both", k=5, maxv=1, mode="opl", timeout=120, max_neg=150,
           recs=None, verbose=True):
    """Leak-free 5-fold CV on the IndAF pool with aux `variant`. Uses the SHARED
    load_pooled/shared_folds/dedup_weighted/shared_negatives so it is apples-to-apples with the
    unified baseline. Returns pooled confusions + fold theories."""
    if recs is None:
        recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    conf = {rd: Counter() for rd in D.READINGS}
    theories, n_to, n_empty, secs = [], 0, 0, []
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        task = build_task(cells, negs, neg_w, variant, maxv=maxv)
        t0 = time.time()
        rules = G.run_fastlas(task, mode=mode, timeout=timeout)
        secs.append(time.time() - t0)
        if rules is None:
            n_to += 1; rules = []
        elif rules == []:
            n_empty += 1
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                conf[rd] += D.score(predict(rules, r["args"], r["attacks"], rd, variant), r["labels"])
        if verbose:
            co, _ = G.committed_only_acc(conf["credulous"])
            print(f"  [{variant}] fold {fi+1}/{len(folds)} {secs[-1]:.1f}s "
                  f"({len(rules)}r{'!TO' if rules==[] and n_to else ''}) running co={co:.3f}", flush=True)
    cc, ncom = G.committed_only_acc(conf["credulous"])
    sc, _ = G.committed_only_acc(conf["skeptical"])
    return {"variant": variant, "phase": phase, "maxv": maxv, "mode": mode,
            "committed_only_cred": cc, "committed_only_skept": sc, "n_committed": ncom,
            "acc3_cred": D.metrics_from_conf(conf["credulous"])["acc3"],
            "acc3_skept": D.metrics_from_conf(conf["skeptical"])["acc3"],
            "timeouts": n_to, "empty": n_empty, "theories": theories,
            "secs": round(sum(secs), 1), "conf": conf}


# ------------------------------------------------------------------ baseline (no aux, same harness)
def build_task_base(cells, negs, neg_w, maxv=1):
    lines = [_BASE, _CLOSURE, "", "#modeh(violated)."] + _MB_BASE
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


def predict_base(rules, args, attacks, reading):
    return predict(rules, args, attacks, reading, "none_base")  # variant with no aux defs


def run_cv_base(phase="final", k=5, maxv=1, mode="opl", timeout=120, max_neg=150, recs=None, verbose=True):
    if recs is None:
        recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    conf = {rd: Counter() for rd in D.READINGS}
    theories, n_to, n_empty, secs = [], 0, 0, []
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        task = build_task_base(cells, negs, neg_w, maxv=maxv)
        t0 = time.time()
        rules = G.run_fastlas(task, mode=mode, timeout=timeout)
        secs.append(time.time() - t0)
        if rules is None:
            n_to += 1; rules = []
        elif rules == []:
            n_empty += 1
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                # base prediction uses only _BASE+_CLOSURE feats (no aux) -> use G.predict(enrich=True)
                conf[rd] += D.score(G.predict(rules, r["args"], r["attacks"], rd, enrich=True), r["labels"])
        if verbose:
            co, _ = G.committed_only_acc(conf["credulous"])
            print(f"  [BASE] fold {fi+1}/{len(folds)} {secs[-1]:.1f}s ({len(rules)}r) running co={co:.3f}", flush=True)
    cc, ncom = G.committed_only_acc(conf["credulous"])
    sc, _ = G.committed_only_acc(conf["skeptical"])
    return {"variant": "BASE", "committed_only_cred": cc, "committed_only_skept": sc,
            "n_committed": ncom, "acc3_cred": D.metrics_from_conf(conf["credulous"])["acc3"],
            "acc3_skept": D.metrics_from_conf(conf["skeptical"])["acc3"],
            "timeouts": n_to, "empty": n_empty, "theories": theories, "secs": round(sum(secs), 1)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="both")
    ap.add_argument("--phase", default="final")
    ap.add_argument("--mode", default="opl")
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--base", action="store_true")
    a = ap.parse_args()
    if a.base:
        r = run_cv_base(phase=a.phase, mode=a.mode, maxv=a.maxv, timeout=a.timeout)
    else:
        r = run_cv(phase=a.phase, variant=a.variant, mode=a.mode, maxv=a.maxv, timeout=a.timeout)
    print(json.dumps({k: v for k, v in r.items() if k != "conf"}, indent=1, default=str))
