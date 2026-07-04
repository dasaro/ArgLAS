#!/usr/bin/env python3
"""aux4 family: REACHABILITY-POSITION auxiliary background predicates for the Exp2 FastLAS
verifier learner. Hypothesis: GLOBAL graph position (not just the local in/out/undec
neighbourhood) informs human argument acceptance -> gives the agnostic learner vocabulary to
express CF2-like SCC/reachability behaviour it currently lacks.

The four aux predicates are PURELY STRUCTURAL (defined from arg/att alone, label-independent):
  reaches_cycle(X)      : X can reach (via >=1 attack edges) some argument that lies on a cycle.
  source(X)             : X has no attackers (an unattacked / root argument).
  sink(X)               : X attacks nothing (a leaf / terminal argument).
  attacked_by_source(X) : X is attacked by some source (an unattacked attacker).
Binary reach/2 and in_cycle stay OUT of the modeb candidate space (they blow OPL up); only the
derived UNARY predicates are exposed. Because they are structural EDB (not derived from the
learned target), they are ground input in BOTH the learn task and the predict program -> no
feature/target coupling -> OPL-safe.

Everything mirrors unified_compare's leak-free apples-to-apples harness (U.load_pooled,
U.shared_folds, U.dedup_weighted, U.shared_negatives) so the ONLY difference vs the published
59.4% committed-only baseline is these aux predicates. The no-aux baseline is recomputed here
through the identical path as the control.
"""
import os, sys, time, argparse, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import clingo

# ---- aux4 STRUCTURAL feature background (from arg/att only; label-independent) ----
# reach/2 is transitive closure of att; in_cycle via reach(X,X); the exposed preds are unary.
_AUX_BG = """reach(X, Y) :- att(X, Y).
reach(X, Z) :- att(X, Y), reach(Y, Z).
in_cycle(X) :- reach(X, X).
reaches_cycle(X) :- arg(X), reach(X, Y), in_cycle(Y).
has_attacker(X) :- att(Y, X).
source(X) :- arg(X), not has_attacker(X).
attacks_something(X) :- att(X, Y).
sink(X) :- arg(X), not attacks_something(X).
attacked_by_source(X) :- att(Y, X), source(Y)."""

_AUX_MODEB = [
    "#modeb(reaches_cycle(var(arg))).", "#modeb(not reaches_cycle(var(arg))).",
    "#modeb(source(var(arg))).", "#modeb(not source(var(arg))).",
    "#modeb(sink(var(arg))).", "#modeb(not sink(var(arg))).",
    "#modeb(attacked_by_source(var(arg))).", "#modeb(not attacked_by_source(var(arg))).",
]


def _feat_bg(enrich, aux):
    bg = G._feat_bg(enrich)
    if aux:
        bg = bg + "\n" + _AUX_BG
    return bg


def build_task(cells, negs, neg_w, maxv=1, enrich=True, aux=True):
    """FastLAS verifier task: SAME weighted cells + soft negative shell as unified_compare, but
    with the aux4 structural background + aux modeb added (when aux=True). enrich=True keeps the
    base in_cycle-free enrichment feats (reach/in_cycle are already in _AUX_BG, so when aux=True
    we DROP the base enrich to avoid duplicate reach/in_cycle rules)."""
    base_feats = G._FEATS + ("" if aux else ("\n" + G._FEATS_ENR if enrich else ""))
    bg = base_feats + ("\n" + _AUX_BG if aux else "")
    mb = list(G._MODEB) + (G._MODEB_ENR if (enrich and not aux) else [])
    if aux:
        mb = mb + _AUX_MODEB
    lines = [bg, "", "#modeh(violated)."] + mb
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


_GEN = """0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- in(X), out(X)."""


def predict(rules, args, attacks, reading, enrich=True, aux=True):
    """generate-and-constrain with the aux4 background included (mirrors G.predict)."""
    if not rules:
        return {a: "undec" for a in args}
    base_feats = G._FEATS + ("" if aux else ("\n" + G._FEATS_ENR if enrich else ""))
    bg = base_feats + ("\n" + _AUX_BG if aux else "")
    prog = "\n".join([_GEN, bg] + list(rules) + [":- violated."])
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


def run_cv(phase="final", k=5, max_neg=150, timeout=120, mode="opl", aux=True, enrich=True,
           maxv=1, verbose=True):
    """Leak-free 5-fold CV on the IndAF pool, apples-to-apples with unified_compare but for the
    single 'learned' arm (+ cf2/grounded textbook anchors). aux=True adds aux4 predicates;
    aux=False is the control that should reproduce the 59.4% committed-only baseline."""
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    ANCHORS = ("cf2", "grounded")
    arms = ("learned",) + ANCHORS
    conf = {(a, rd): Counter() for a in arms for rd in D.READINGS}
    theories = []
    n_to = n_empty = 0
    t_learn = 0.0
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        task = build_task(cells, negs, neg_w, maxv=maxv, enrich=enrich, aux=aux)
        t0 = time.time()
        rules = G.run_fastlas(task, mode=mode, timeout=timeout)
        t_learn += time.time() - t0
        if rules is None:
            n_to += 1
            rules = []
        elif rules == []:
            n_empty += 1
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                conf[("learned", rd)] += D.score(
                    predict(rules, r["args"], r["attacks"], rd, enrich=enrich, aux=aux), r["labels"])
            for anch in ANCHORS:
                labs = D.textbook_labellings(anch, r["args"], r["attacks"])
                for rd in D.READINGS:
                    conf[(anch, rd)] += D.score(D.project(labs, r["args"], rd), r["labels"])
        if verbose:
            print(f"  [{phase}|aux={aux}] fold {fi+1}/{len(folds)} "
                  f"{time.time()-t0:.1f}s {len(rules)}r{'!TO' if rules==[] and n_to else ''}",
                  flush=True)
    co_cred, ncom = G.committed_only_acc(conf[("learned", "credulous")])
    skept_acc3 = D.metrics_from_conf(conf[("learned", "skeptical")])["acc3"]
    res = {"phase": phase, "aux": aux, "mode": mode, "enrich": enrich, "maxv": maxv,
           "n_responses": sum(len(r["labels"]) for r in recs), "n_committed": ncom,
           "committed_only_cred": co_cred, "skeptical_acc3": skept_acc3,
           "fastlas_timeouts": n_to, "empty_folds": n_empty, "learn_secs": round(t_learn, 1),
           "theories": theories}
    for anch in ANCHORS:
        cc, _ = G.committed_only_acc(conf[(anch, "credulous")])
        res[f"{anch}_committed_only_cred"] = cc
        res[f"{anch}_skeptical_acc3"] = D.metrics_from_conf(conf[(anch, "skeptical")])["acc3"]
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="final")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--max-neg", type=int, default=150)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--mode", default="opl", choices=("opl", "nopl"))
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "aux4_reachpos.json"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out = {}
    for aux in (False, True):
        tag = "aux" if aux else "baseline"
        print(f"\n===== {tag} (aux={aux}) phase={a.phase} mode={a.mode} maxv={a.maxv} =====")
        r = run_cv(phase=a.phase, k=a.folds, max_neg=a.max_neg, timeout=a.timeout,
                   mode=a.mode, aux=aux, maxv=a.maxv)
        out[tag] = r
        print(f"  committed_only_cred = {r['committed_only_cred']:.4f}  "
              f"skeptical_acc3 = {r['skeptical_acc3']:.4f}  "
              f"({r['fastlas_timeouts']}TO/{r['empty_folds']}empty, {r['learn_secs']}s)")
        print(f"  cf2 committed_only = {r['cf2_committed_only_cred']:.4f}  "
              f"grounded committed_only = {r['grounded_committed_only_cred']:.4f}")
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nresults -> {a.out}")
