#!/usr/bin/env python3
"""aux9 -- COMBINED best-of-families auxiliary vocabulary for the FastLAS-OPL verifier.

COMBINE PHASE. From the four aux families tested, the two that HELPED (beat baseline
and whose predicates actually appeared in learned theories) were:

  aux3 (reinstatement/defense)  committed_only=0.6581  [reinstated, floating, undefended_in]
  aux2 (degree-salience)        committed_only=0.6484  [has_many_attackers, has_unattacked_attacker, unattacked]

aux4 (reachability-position) was NEUTRAL (0.6065, barely > baseline) -> dropped.
aux1 (scc-cycle) was INCONCLUSIVE (0.594, aux_used=False) -> dropped.

FastLAS OPL blows up past ~5 aux predicates, so we cannot keep all 6.  We keep the FULL
aux3 triple (strongest family, all three appeared) plus the two strongest aux2 salience
predicates by learned-theory frequency (has_many_attackers=41, has_unattacked_attacker=33;
unattacked=37 but it is a plain source-marker that is largely subsumed by
has_unattacked_attacker's decisive-attack semantics).  Total = 5 aux modeh-visible predicates.

  --- aux3 (label-dependent; labelling in/out GIVEN as verifier context) ---
  reinstated(X)     : X attacked, every attacker itself attacked by an in-arg (floating reinst.)
  floating(X)       : X attacked, no attacker is unattacked (mutual/odd-cycle structure)
  undefended_in(X)  : X labelled in but some attacker is not out (defense violation)
  --- aux2 (purely structural, from arg/att only) ---
  has_many_attackers(X)      : >= 2 distinct attackers (heavily contested)
  has_unattacked_attacker(X) : an attacker that is itself unattacked (a decisive attack)

Helper preds used in bodies but kept OUT of modeb (so FastLAS only searches over the 5):
  att_not_killed_by_in, att_unattacked (aux3);  unattacked (aux2 helper).
attacked / attacked_by_in / in / out come from the base feature bg.

Everything else -- data, folds, dedup, negatives, scoring, committed-only -- imported verbatim
from the shared audited modules (unified_compare, fl_discover, discover_semantics).

Run:
  python3 aux9_combined.py --gate                    # synthetic grounded-recovery gate
  python3 aux9_combined.py --cv --phase final        # leak-free 5-fold CV, aux ON
  python3 aux9_combined.py --cv --baseline           # + no-aux control (should ~0.594)
"""
import os, sys, time, json, argparse
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import clingo

# ---------------------------------------------------------------------------
# combined aux background.  FastLAS grammar rejects ':' conditional literals ->
# every "for all attackers" is encoded via a not_x helper + negation.
# ---------------------------------------------------------------------------
AUX9_BG = """% --- aux3: reinstatement / defense structure (over att + given in/out) ---
att_not_killed_by_in(X) :- att(Y, X), not attacked_by_in(Y).
reinstated(X) :- attacked(X), not att_not_killed_by_in(X).
att_unattacked(X) :- att(Y, X), not attacked(Y).
floating(X) :- attacked(X), not att_unattacked(X).
undefended_in(X) :- in(X), att(Y, X), not out(Y).
% --- aux2: degree-salience (purely structural, from arg/att only) ---
unattacked(X) :- arg(X), not attacked(X).
has_many_attackers(X) :- att(Y, X), att(Z, X), Y != Z.
has_unattacked_attacker(X) :- att(Y, X), unattacked(Y)."""

AUX9_MODEB = [
    "#modeb(reinstated(var(arg))).", "#modeb(not reinstated(var(arg))).",
    "#modeb(floating(var(arg))).", "#modeb(not floating(var(arg))).",
    "#modeb(undefended_in(var(arg))).", "#modeb(not undefended_in(var(arg))).",
    "#modeb(has_many_attackers(var(arg))).", "#modeb(not has_many_attackers(var(arg))).",
    "#modeb(has_unattacked_attacker(var(arg))).", "#modeb(not has_unattacked_attacker(var(arg))).",
]

AUX9_PREDS = ["reinstated", "floating", "undefended_in",
              "has_many_attackers", "has_unattacked_attacker"]


def feat_bg(enrich, with_aux):
    bg = G._feat_bg(enrich)
    if with_aux:
        bg = bg + "\n" + AUX9_BG
    return bg


def build_task(cells, negs, neg_w, maxv=1, enrich=True, with_aux=True):
    mb = list(G._MODEB) + (list(G._MODEB_ENR) if enrich else []) + (AUX9_MODEB if with_aux else [])
    lines = [feat_bg(enrich, with_aux), "", "#modeh(violated)."] + mb
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


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
    return ([] if rules is None else rules), (rules is None)


def aux_used(rules):
    if not rules:
        return False
    body = "\n".join(rules)
    return any(p in body for p in AUX9_PREDS)


# ---------------------------------------------------------------------------
# leak-free 5-fold CV
# ---------------------------------------------------------------------------
def cv(phase="final", k=5, mode="opl", timeout=120, enrich=True, maxv=1,
       max_neg=150, with_aux=True, verbose=True):
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    conf = {rd: Counter() for rd in D.READINGS}
    theories, n_to = [], 0
    t_all = time.time()
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
                  f"{'!TO' if to else ''}  aux_used={aux_used(rules)}", flush=True)
    co, ncom = G.committed_only_acc(conf["credulous"])
    sk = D.metrics_from_conf(conf["skeptical"])["acc3"]
    return {"committed_only": co, "n_committed": ncom, "skeptical_acc3": sk,
            "cred_acc3": D.metrics_from_conf(conf["credulous"])["acc3"],
            "theories": theories, "n_timeouts": n_to,
            "secs": round(time.time() - t_all, 1),
            "aux_used_any": any(aux_used(t) for t in theories)}


# ---------------------------------------------------------------------------
# SYNTHETIC GATE (mirrors aux2/aux3 gate: relabel real graphs with grounded, recover)
# ---------------------------------------------------------------------------
def synthetic_gate(phase="final", mode="opl", timeout=120, max_neg=150, with_aux=True):
    recs = U.load_pooled(phase)
    clean = []
    for r in recs:
        labs = D.textbook_labellings("grounded", r["args"], r["attacks"])
        gl = D.project(labs, r["args"], "grounded")
        rr = dict(r)
        rr["labels"] = {a: gl[a] for a in r["args"]}
        rr["commit"] = {a: gl[a] for a in r["args"] if gl[a] in ("in", "out")}
        clean.append(rr)
    folds = U.shared_folds(clean, 5)
    conf = {rd: Counter() for rd in D.READINGS}
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        rules, to = learn_fold(cells, negs, neg_w, mode, timeout, with_aux=with_aux)
        for r in test:
            for rd in D.READINGS:
                p = predict(rules, r["args"], r["attacks"], rd, with_aux=with_aux)
                conf[rd] += D.score(p, r["labels"])
    return {rd: D.metrics_from_conf(conf[rd])["acc3"] for rd in D.READINGS}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--cv", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--mode", default="opl")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--phase", default="final")
    a = ap.parse_args()
    out = {}

    if a.gate:
        print("=== SYNTHETIC GATE (aux ON) ===", flush=True)
        g = synthetic_gate(phase=a.phase, mode=a.mode, timeout=a.timeout, with_aux=True)
        print("  gate acc3:", g, " gate_passed=", g["skeptical"] >= 0.98, flush=True)
        out["gate"] = g

    if a.cv:
        print(f"=== CV aux ON · phase={a.phase} mode={a.mode} ===", flush=True)
        r = cv(phase=a.phase, mode=a.mode, timeout=a.timeout, with_aux=True)
        print(f"  committed_only={r['committed_only']:.4f}  skeptical_acc3={r['skeptical_acc3']:.4f}"
              f"  cred_acc3={r['cred_acc3']:.4f}  aux_used_any={r['aux_used_any']}"
              f"  TO={r['n_timeouts']}  ({r['secs']}s)", flush=True)
        out["aux"] = {k: r[k] for k in ("committed_only", "skeptical_acc3", "cred_acc3",
                                        "aux_used_any", "n_timeouts", "secs")}
        out["aux_theories"] = r["theories"]

    if a.baseline:
        print(f"=== CV aux OFF (baseline control) · phase={a.phase} ===", flush=True)
        r0 = cv(phase=a.phase, mode=a.mode, timeout=a.timeout, with_aux=False)
        print(f"  committed_only={r0['committed_only']:.4f}  skeptical_acc3={r0['skeptical_acc3']:.4f}"
              f"  ({r0['secs']}s)", flush=True)
        out["baseline"] = {k: r0[k] for k in ("committed_only", "skeptical_acc3", "cred_acc3")}

    with open(os.path.join(HERE, f"aux9_results_{a.phase}.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"-> aux9_results_{a.phase}.json", flush=True)
