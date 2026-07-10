#!/usr/bin/env python3
"""aux3 — REINSTATEMENT / DEFENSE-STRUCTURE auxiliary predicates for the FastLAS-OPL verifier.

Family hypothesis: the floating-reinstatement conditions (A/B/C) are exactly where humans diverge
from grounded. Features about DEFENSE CHAINS may capture their committal behaviour.

We add label-dependent structural predicates (the labelling in/out is GIVEN as context in the
verifier, so these are fine as stratified ASP over att + in/out):

  reinstated(X)     : X is attacked, and EVERY attacker of X is itself attacked by an in-arg
                      (floating reinstatement -- all attackers defeated by an in-arg).
  floating(X)       : X is attacked, and EVERY attacker of X is itself attacked (by anything)
                      -- captures the mutual/odd-cycle "no unattacked attacker" structure.
  undefended_in(X)  : X labelled in, but some attacker of X is NOT out (a defense violation).

These mirror G.predict / unified_compare.fastlas_task exactly, but with the aux background wired
into BOTH the learn task and the prediction program. Everything else (folds, dedup, negatives,
scoring, committed-only) is imported from the shared, audited modules -- NOT reimplemented.

Run:  python3 aux3_reinstatement.py --gate     # synthetic recovery gate
      python3 aux3_reinstatement.py --cv        # leak-free 5-fold CV on IndAF final, aux vs baseline
"""
import os, sys, time, argparse, tempfile, subprocess
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import clingo

# ---------------------------------------------------------------------------
# aux3 feature background (label-dependent; labelling given as context in the verifier).
# FastLAS grammar rejects ':' conditional literals -> use not_x helpers + negation.
# ---------------------------------------------------------------------------
AUX3_BG = """% --- reinstatement / defense structure (over att + given in/out) ---
% attacker of X that is NOT defeated by any in-arg
att_not_killed_by_in(X) :- att(Y, X), not attacked_by_in(Y).
% reinstated: X attacked, and every attacker is itself attacked by an in-arg
reinstated(X) :- attacked(X), not att_not_killed_by_in(X).
% attacker of X that is itself unattacked
att_unattacked(X) :- att(Y, X), not attacked(Y).
% floating: X attacked, but no attacker is unattacked (every attacker is attacked)
floating(X) :- attacked(X), not att_unattacked(X).
% undefended_in: X is IN but has an attacker that is not OUT (defense violation)
undefended_in(X) :- in(X), att(Y, X), not out(Y)."""

# helper preds that the aux uses but must be visible: attacked_by_in / attacked come from G._FEATS.

AUX3_MODEB = [
    "#modeb(reinstated(var(arg))).", "#modeb(not reinstated(var(arg))).",
    "#modeb(floating(var(arg))).", "#modeb(not floating(var(arg))).",
    "#modeb(undefended_in(var(arg))).", "#modeb(not undefended_in(var(arg))).",
]

AUX3_PREDS = ["reinstated", "floating", "undefended_in",
              "att_not_killed_by_in", "att_unattacked"]


def feat_bg(enrich, with_aux):
    bg = G._feat_bg(enrich)
    if with_aux:
        bg = bg + "\n" + AUX3_BG
    return bg


# ---------------------------------------------------------------------------
# learn task (mirrors unified_compare.fastlas_task, + optional aux modeb/background)
# ---------------------------------------------------------------------------
def build_task(cells, negs, neg_w, maxv=1, enrich=True, with_aux=True):
    mb = list(G._MODEB) + (list(G._MODEB_ENR) if enrich else []) + (AUX3_MODEB if with_aux else [])
    lines = [feat_bg(enrich, with_aux), "", "#modeh(violated)."] + mb
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# predict (mirrors G.predict, + aux background injected)
# ---------------------------------------------------------------------------
def predict(rules, args, attacks, reading, enrich=True, with_aux=True):
    if not rules:
        return {a: "undec" for a in args}
    prog = "\n".join([G._GEN, feat_bg(enrich, with_aux)] + list(rules) + [":- violated."])
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


def learn_fold(cells, negs, neg_w, mode, timeout, maxv=1, enrich=True, with_aux=True):
    task = build_task(cells, negs, neg_w, maxv=maxv, enrich=enrich, with_aux=with_aux)
    rules = G.run_fastlas(task, mode=mode, timeout=timeout)
    timed_out = rules is None
    return ([] if timed_out else rules), timed_out


def aux_used(rules):
    if not rules:
        return False
    body = "\n".join(rules)
    return any(p in body for p in ("reinstated", "floating", "undefended_in"))


# ---------------------------------------------------------------------------
# leak-free 5-fold CV on the IndAF final pool (aux vs no-aux, identical everything else)
# ---------------------------------------------------------------------------
def cv(phase="final", k=5, mode="opl", timeout=120, enrich=True, maxv=1,
       max_neg=150, with_aux=True, verbose=True):
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    conf = {rd: Counter() for rd in D.READINGS}
    theories, n_to = [], 0
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        t0 = time.time()
        rules, to = learn_fold(cells, negs, neg_w, mode, timeout,
                               maxv=maxv, enrich=enrich, with_aux=with_aux)
        dt = time.time() - t0
        n_to += int(to)
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                p = predict(rules, r["args"], r["attacks"], rd, enrich=enrich, with_aux=with_aux)
                conf[rd] += D.score(p, r["labels"])
        if verbose:
            print(f"  fold {fi+1}/{len(folds)}  {dt:.1f}s  {len(rules)}r"
                  f"{'!TO' if to else ''}  aux_used={aux_used(rules)}  rules={rules}", flush=True)
    co, ncom = G.committed_only_acc(conf["credulous"])
    sk = D.metrics_from_conf(conf["skeptical"])["acc3"]
    return {"committed_only": co, "n_committed": ncom, "skeptical_acc3": sk,
            "cred_acc3": D.metrics_from_conf(conf["credulous"])["acc3"],
            "theories": theories, "n_timeouts": n_to, "conf": conf,
            "aux_used_any": any(aux_used(t) for t in theories)}


# ---------------------------------------------------------------------------
# SYNTHETIC GATE: feed CLEAN grounded labels through the exact learn+predict path;
# confirm aux background does not break grounded recovery (skeptical acc3 ~ 1.0).
# ---------------------------------------------------------------------------
def synthetic_gate(mode="opl", timeout=120, with_aux=True):
    """Build a small set of graphs, compute their GROUNDED labelling, treat each as a positive
    training cell, mine the H1 shell as negatives, learn, then predict grounded and check we
    recover the grounded labelling exactly (committed-only=1.0, skeptical acc3=1.0)."""
    import itertools
    # a handful of structurally varied graphs (chains, 2-cycle, 3-cycle, reinstatement, floating)
    graphs = [
        (["a", "b"], [("a", "b")]),                                   # simple attack
        (["a", "b", "c"], [("a", "b"), ("b", "c")]),                  # reinstatement chain
        (["a", "b"], [("a", "b"), ("b", "a")]),                       # 2-cycle
        (["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")]),      # 3-cycle
        (["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")]), # longer chain
        (["a", "b", "c"], [("a", "c"), ("b", "c")]),                  # two attackers
        (["a", "b", "c", "d"], [("a", "b"), ("c", "b"), ("b", "d")]), # floating-ish
    ]
    # build "records" whose commit = grounded committed labelling
    recs = []
    for gi, (args, atts) in enumerate(graphs):
        gl = D.textbook_labellings("grounded", args, atts)[0]  # grounded is unique
        commit = {a: gl[a] for a in args if gl[a] in ("in", "out")}
        recs.append({"args": args, "attacks": atts, "commit": commit,
                     "labels": gl, "version": "SYN"})
    cells = U.dedup_weighted(recs)
    negs, neg_w = U.shared_negatives(recs, 150)
    rules, to = learn_fold(cells, negs, neg_w, mode, timeout,
                           maxv=1, enrich=True, with_aux=with_aux)
    # predict grounded reading, score vs grounded labelling (resubstitution -- this is a RECOVERY
    # gate, not a generalization test)
    conf = Counter()
    conf_co = Counter()
    for r in recs:
        p = predict(rules, r["args"], r["attacks"], "skeptical", enrich=True, with_aux=with_aux)
        conf += D.score(p, r["labels"])
    sk_acc3 = D.metrics_from_conf(conf)["acc3"]
    co, ncom = G.committed_only_acc(conf)
    return {"rules": rules, "timed_out": to, "skeptical_acc3": sk_acc3,
            "committed_only": co, "aux_used": aux_used(rules)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--cv", action="store_true")
    ap.add_argument("--baseline", action="store_true", help="run no-aux control too")
    ap.add_argument("--mode", default="opl")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--phase", default="final")
    a = ap.parse_args()

    if a.gate:
        print("=== SYNTHETIC GATE (aux ON) ===")
        g = synthetic_gate(mode=a.mode, timeout=a.timeout, with_aux=True)
        print(g)
        print("=== SYNTHETIC GATE (aux OFF, control) ===")
        g0 = synthetic_gate(mode=a.mode, timeout=a.timeout, with_aux=False)
        print(g0)

    if a.cv:
        print(f"=== CV aux ON · phase={a.phase} mode={a.mode} ===")
        r = cv(phase=a.phase, mode=a.mode, timeout=a.timeout, with_aux=True)
        print(f"  committed_only={r['committed_only']:.4f}  skeptical_acc3={r['skeptical_acc3']:.4f}"
              f"  cred_acc3={r['cred_acc3']:.4f}  aux_used_any={r['aux_used_any']}  TO={r['n_timeouts']}")

    if a.baseline:
        print(f"=== CV aux OFF (baseline control) · phase={a.phase} mode={a.mode} ===")
        r0 = cv(phase=a.phase, mode=a.mode, timeout=a.timeout, with_aux=False)
        print(f"  committed_only={r0['committed_only']:.4f}  skeptical_acc3={r0['skeptical_acc3']:.4f}"
              f"  cred_acc3={r0['cred_acc3']:.4f}  TO={r0['n_timeouts']}")
