#!/usr/bin/env python3
"""Strategy 4 helpers: OPL VERIFIER formulation for grounded argumentation semantics.

The labelling is GIVEN in the context (in/out/undec facts per arg). We learn a
target-INDEPENDENT `violated`/`legal` predicate (non-recursive => genuinely OPL).
This module also clingo-verifies separability and that a learned theory recovers grounded.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clingo
import fl_build as F
import discover_semantics as D

D.PHASE = "att_first__lab_first"; D.GRAPH = "own"

# Target-independent derived features over a GIVEN 3-valued labelling (in/out/undec).
FEATURES = """attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y)."""

# The frame that turns learned `violated` into `legal`.
FRAME = "legal :- not violated."

# Ground-truth violation theory we WANT FastLAS to (re)learn.
GT_VIOL = """violated :- in(X), not defended(X).
violated :- out(X), not attacked_by_in(X).
violated :- undec(X), defended(X).
violated :- undec(X), attacked_by_in(X)."""


def full_grounded(args, attacks):
    labs = D.textbook_labellings("grounded", args, attacks)
    lab = D.project(labs, args, "skeptical")
    return {a: lab.get(a, "undec") for a in args}


def shell3(lab):
    out = []
    for a, s in lab.items():
        for v in ("in", "out", "undec"):
            if v != s:
                nb = dict(lab); nb[a] = v; out.append(nb)
    return out


def cells():
    return F.grounded_cells("D", "grounded")


def solve0(prog, args, attacks, shows=("legal", "violated")):
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + "\n" + facts + "\n" + "".join(f"#show {s}/0.\n" for s in shows))
    ctl.ground([("base", [])])
    res = {s: False for s in shows}
    found = [False]
    def on_model(m):
        found[0] = True
        for x in m.symbols(shown=True):
            if x.name in res:
                res[x.name] = True
    ctl.solve(on_model=on_model)
    res["_sat"] = found[0]
    return res


def labfacts(lab):
    return "".join(f"{s}({a}). " for a, s in lab.items())


def verify_separation(viol_theory):
    """Given a `violated` theory (str), check on ALL D graphs: grounded -> legal & no viol;
    every 3-valued Hamming-1 neighbour -> NOT legal. Returns (ok, details)."""
    prog_head = FEATURES + "\n" + FRAME + "\n" + viol_theory + "\n"
    ok = True; details = []
    for c in cells():
        args, attacks = c["args"], c["attacks"]
        g = full_grounded(args, attacks)
        rg = solve0(prog_head + labfacts(g), args, attacks)
        gok = rg["legal"] and not rg["violated"]
        bad_nbs = []
        for nb in shell3(g):
            rn = solve0(prog_head + labfacts(nb), args, attacks)
            if rn["legal"]:
                bad_nbs.append(nb)
        if not gok or bad_nbs:
            ok = False
        details.append({"attacks": attacks, "grounded": g, "grounded_legal": gok,
                        "leaky_neighbours": bad_nbs})
    return ok, details


def recovers_grounded_via_generate(viol_theory):
    """Independent end-to-end check: GENERATE all complete-ish labellings via choice, keep
    only `legal` ones (learned constraint), and confirm the UNIQUE surviving labelling equals
    the true grounded labelling on ALL D graphs."""
    gen = """{ in(X) } :- arg(X).
{ out(X) } :- arg(X).
{ undec(X) } :- arg(X).
:- arg(X), in(X), out(X).
:- arg(X), in(X), undec(X).
:- arg(X), out(X), undec(X).
lab(X) :- in(X).
lab(X) :- out(X).
lab(X) :- undec(X).
:- arg(X), not lab(X)."""
    # grounded = the COMPLETE labelling with the MAXIMAL undec set. The verifier learns
    # "complete labelling"; selecting the grounded one among complete labellings is the fixed
    # generate-step policy (#maximize undec). (minimize-in is NOT equivalent: some non-grounded
    # complete labellings tie on in-count; maximize-undec is the unique grounded selector.)
    prog = (FEATURES + "\n" + FRAME + "\n" + viol_theory + "\n" + gen +
            "\n:- violated.\n#maximize { 1@1, X : undec(X) }.\n")
    ok = True; details = []
    for c in cells():
        args, attacks = c["args"], c["attacks"]
        g = full_grounded(args, attacks)
        facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
        ctl = clingo.Control(["0", "--warn=none", "--opt-mode=optN"])
        ctl.add("base", [], prog + "\n" + facts + "\n#show in/1.\n#show out/1.\n#show undec/1.\n")
        ctl.ground([("base", [])])
        models = []
        def on_model(m):
            if not m.optimality_proven:
                return
            d = {}
            for x in m.symbols(shown=True):
                d[str(x.arguments[0])] = x.name
            models.append({a: d.get(a, "undec") for a in args})
        ctl.solve(on_model=on_model)
        uniq = len(models) == 1
        match = uniq and models[0] == g
        if not match:
            ok = False
        details.append({"attacks": attacks, "n_legal_models": len(models),
                        "grounded": g, "recovered": models[0] if models else None,
                        "match": match})
    return ok, details


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "gt"
    if what == "gt":
        ok, det = verify_separation(GT_VIOL)
        print("GROUND-TRUTH separation ok:", ok)
        for d in det:
            print(" ", d["attacks"], "glegal", d["grounded_legal"], "leaks", d["leaky_neighbours"])
        ok2, det2 = recovers_grounded_via_generate(GT_VIOL)
        print("GROUND-TRUTH generate-and-test recovers grounded:", ok2)
        for d in det2:
            print(" ", d["attacks"], "nmodels", d["n_legal_models"], "match", d["match"])
