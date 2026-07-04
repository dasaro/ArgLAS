#!/usr/bin/env python3
"""aux2 -- "degree-salience" auxiliary predicates for the FastLAS-OPL verifier learner.

Hypothesis: humans weight an argument by HOW CONTESTED it is (counting attackers, not just
logical status). We add up to 3 PURELY-STRUCTURAL aux predicates (functions of arg/att only,
so they are ground EDB -- no target coupling, safe in both learn task background AND predict
program):

  unattacked(X)               : X has no attackers        (a source / undisputed)
  has_unattacked_attacker(X)  : some attacker of X is itself unattacked (a decisive attack on X)
  has_many_attackers(X)       : X has >= 2 distinct attackers (heavily contested)

These extend the base verifier vocabulary (in,out,undec,defended,attacked_by_in,attacked,
in_cycle). Everything else -- data, folds, dedup/negatives, scoring -- is imported verbatim
from the shared modules so the comparison is apples-to-apples with the no-aux baseline.

Run:
  python3 aux2_degree_salience.py            # gate + 5-fold CV (real) + baseline
"""
import os, sys, time, json
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import clingo

# ---------------- aux2 structural background ----------------
# purely structural: derived from arg/att only. Also emit the base feature background so the
# learned constraints can combine label-status features with degree-salience features.
# NO aggregates: FastLAS's grammar rejects '#count'. Encode degree buckets with plain rules.
#   attacked(X)               already provided by the base feature bg (att(Y,X) -> attacked)
#   unattacked(X)             = arg with no attacker (negation of attacked)
#   has_many_attackers(X)     = two DISTINCT attackers (Y != Z)
#   has_unattacked_attacker(X)= an attacker that is itself unattacked (a decisive attack)
_AUX_BG = """unattacked(X) :- arg(X), not attacked(X).
has_many_attackers(X) :- att(Y, X), att(Z, X), Y != Z.
has_unattacked_attacker(X) :- att(Y, X), unattacked(Y)."""

_AUX_MODEB = [
    "#modeb(unattacked(var(arg))).",
    "#modeb(has_unattacked_attacker(var(arg))).",
    "#modeb(has_many_attackers(var(arg))).",
    "#modeb(not unattacked(var(arg))).",
    "#modeb(not has_unattacked_attacker(var(arg))).",
    "#modeb(not has_many_attackers(var(arg))).",
]


def _feat_bg(enrich, with_aux):
    bg = G._feat_bg(enrich)
    if with_aux:
        bg += "\n" + _AUX_BG
    return bg


def build_task(cells, negs, neg_w, enrich=True, maxv=1, with_aux=True):
    """Same verifier formulation as unified_compare.fastlas_task, plus the aux2 background/modeb."""
    mb = G._MODEB + (G._MODEB_ENR if enrich else []) + (_AUX_MODEB if with_aux else [])
    lines = [_feat_bg(enrich, with_aux), "", "#modeh(violated)."] + mb
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


# ---------------- prediction: generate-and-constrain with aux2 background ----------------
def predict(rules, args, attacks, reading, enrich=True, with_aux=True):
    if not rules:
        return {a: "undec" for a in args}
    prog = "\n".join([G._GEN, _feat_bg(enrich, with_aux)] + list(rules) + [":- violated."])
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


# ---------------- learner arm (mirrors unified_compare.fastlas_fold) ----------------
def learn_fold(cells, negs, neg_w, mode, timeout, enrich=True, maxv=1, with_aux=True):
    task = build_task(cells, negs, neg_w, enrich=enrich, maxv=maxv, with_aux=with_aux)
    rules = G.run_fastlas(task, mode=mode, timeout=timeout)
    return ([] if rules is None else rules), (rules is None)


# ---------------- 5-fold leak-free CV on the real pool ----------------
def real_cv(phase="final", k=5, mode="opl", timeout=120, max_neg=150, enrich=True,
            maxv=1, with_aux=True, verbose=True):
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, k)
    conf = {rd: Counter() for rd in D.READINGS}
    theories = []
    n_to = 0
    t_all = time.time()
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        t0 = time.time()
        rules, to = learn_fold(cells, negs, neg_w, mode, timeout, enrich=enrich,
                               maxv=maxv, with_aux=with_aux)
        n_to += int(to)
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                p = predict(rules, r["args"], r["attacks"], rd, enrich=enrich, with_aux=with_aux)
                conf[rd] += D.score(p, r["labels"])
        if verbose:
            print(f"  fold {fi+1}/{len(folds)}: {time.time()-t0:.1f}s "
                  f"{'TO' if to else ''} rules={rules}", flush=True)
    co, ncom = G.committed_only_acc(conf["credulous"])
    sk_acc3 = D.metrics_from_conf(conf["skeptical"])["acc3"]
    cr_acc3 = D.metrics_from_conf(conf["credulous"])["acc3"]
    return {"committed_only": co, "n_committed": ncom, "skeptical_acc3": sk_acc3,
            "credulous_acc3": cr_acc3, "theories": theories, "timeouts": n_to,
            "secs": round(time.time() - t_all, 1), "conf": conf}


# ---------------- SYNTHETIC GATE ----------------
def synthetic_gate(phase="final", mode="opl", timeout=120, max_neg=150):
    """Feed CLEAN grounded labels through the exact aux2 learn+predict path; confirm grounded
    recovery survives (skeptical acc3 ~1.0). Uses the real IndAF graphs but replaces every human
    labelling with the textbook GROUNDED labelling of that graph."""
    recs = U.load_pooled(phase)
    # relabel every record with grounded of its own graph
    clean = []
    for r in recs:
        labs = D.textbook_labellings("grounded", r["args"], r["attacks"])
        gl = D.project(labs, r["args"], "grounded")  # grounded is a single labelling
        rr = dict(r)
        rr["labels"] = {a: gl[a] for a in r["args"]}
        rr["commit"] = D.committed(gl)
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
        rules, to = learn_fold(cells, negs, neg_w, mode, timeout, with_aux=True)
        for r in test:
            for rd in D.READINGS:
                p = predict(rules, r["args"], r["attacks"], rd, with_aux=True)
                conf[rd] += D.score(p, r["labels"])
    return {rd: D.metrics_from_conf(conf[rd])["acc3"] for rd in D.READINGS}, conf


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "opl"
    print(f"=== aux2 degree-salience  (mode={mode}) ===\n")

    print("[GATE] synthetic grounded recovery with aux2 predicates ...", flush=True)
    gate, gconf = synthetic_gate(mode=mode)
    print(f"  gate acc3: {gate}")
    gate_pass = gate["skeptical"] >= 0.98
    print(f"  gate_passed = {gate_pass}\n")

    print("[BASELINE] no-aux, same harness ...", flush=True)
    base = real_cv(mode=mode, with_aux=False)
    print(f"  committed_only={base['committed_only']:.4f} skept_acc3={base['skeptical_acc3']:.4f} "
          f"({base['secs']}s, {base['timeouts']}TO)\n")

    print("[AUX2] with degree-salience predicates ...", flush=True)
    aux = real_cv(mode=mode, with_aux=True)
    print(f"  committed_only={aux['committed_only']:.4f} skept_acc3={aux['skeptical_acc3']:.4f} "
          f"({aux['secs']}s, {aux['timeouts']}TO)\n")

    used = any(any(p in r for r in th for p in
                   ("unattacked", "has_unattacked_attacker", "has_many_attackers"))
               for th in aux["theories"])
    out = {
        "gate": gate, "gate_passed": gate_pass,
        "baseline_committed_only": base["committed_only"],
        "baseline_skept_acc3": base["skeptical_acc3"],
        "aux_committed_only": aux["committed_only"],
        "aux_skept_acc3": aux["skeptical_acc3"],
        "aux_used": used,
        "aux_theories": aux["theories"],
        "base_theories": base["theories"],
        "aux_secs": aux["secs"], "aux_timeouts": aux["timeouts"],
    }
    with open(os.path.join(HERE, f"aux2_results_{mode}.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("aux predicates used in learned theory:", used)
    print(f"beats baseline (committed): {aux['committed_only']} vs {base['committed_only']}")
    print(f"-> results/aux2_results_{mode}.json")
