#!/usr/bin/env python3
"""Level-2 machine-check of the thesis §2.5 equivalence theorems, via Fages + Z3.

ARGUMENT. All six programs (learned P_sem and ASPARTIX-style S_sem, for sem in
{STB, ADM, CMP}) are TIGHT: their positive dependency graphs are acyclic (in depends
positively only on arg; defeated on in; out on defeated/not_defended; not_defended on
att only — verified by the syntactic check below). By Fages' theorem, for tight
programs the answer sets of P ∪ F are exactly the Herbrand models of the Clark
completion Comp(P ∪ F). The facts F fix arg/att; the thesis assumes every domain
element carries an arg fact, so we work over a domain of arguments (arg ≡ true) with
att an arbitrary binary relation. Each theorem A ∈ AS(P∪F) ⇔ A ∈ AS(S∪F) for ALL F
therefore reduces to the FIRST-ORDER validity of Comp(P) ↔ Comp(S) over all
structures — which Z3 verifies below (each direction: assert Comp(A) ∧ ¬Comp(B),
expect unsat). This quantifies over ALL domains, not just finite test cases.
"""
from z3 import (Bools, BoolSort, Consts, DeclareSort, Exists, ForAll, Function,
                Implies, And, Or, Not, Solver, unsat, sat)

Arg = DeclareSort("Arg")
att = Function("att", Arg, Arg, BoolSort())
inn = Function("in", Arg, BoolSort())
out = Function("out", Arg, BoolSort())
defeated = Function("defeated", Arg, BoolSort())
not_defended = Function("not_defended", Arg, BoolSort())
X, Y = Consts("X Y", Arg)


def defs():
    """Completion of the shared definitions (identical in every program)."""
    return [
        ForAll([X], defeated(X) == Exists([Y], And(att(Y, X), inn(Y)))),
        ForAll([X], not_defended(X) == Exists([Y], And(att(Y, X), Not(defeated(Y))))),
    ]


def conflict_free():
    return ForAll([X, Y], Not(And(inn(X), inn(Y), att(X, Y))))


# ---- Clark completions of the six programs (arg(X) === true on the domain) ----
COMP = {
    # manuscript learned programs
    "P_STB": defs() + [
        ForAll([X], out(X) == defeated(X)),           # out :- defeated
        ForAll([X], inn(X) == Not(out(X))),           # in :- arg, not out
    ],
    "P_ADM": defs() + [
        ForAll([X], out(X) == Or(defeated(X), Not(inn(X)))),           # two out rules
        ForAll([X], inn(X) == And(Not(out(X)), Not(not_defended(X)))),
    ],
    "P_CMP": defs() + [
        ForAll([X], out(X) == not_defended(X)),
        ForAll([X], inn(X) == And(Not(out(X)), Not(defeated(X)))),
    ],
    # ASPARTIX-style programs as quoted in the manuscript (guess + constraints)
    "S_STB": defs() + [
        ForAll([X], inn(X) == Not(out(X))),
        ForAll([X], out(X) == Not(inn(X))),
        conflict_free(),
        ForAll([X], Implies(out(X), defeated(X))),    # :- out, not defeated
    ],
    "S_ADM": defs() + [
        ForAll([X], inn(X) == Not(out(X))),
        ForAll([X], out(X) == Not(inn(X))),
        conflict_free(),
        ForAll([X], Not(And(inn(X), not_defended(X)))),  # :- in, not_defended
    ],
    "S_CMP": defs() + [
        ForAll([X], inn(X) == Not(out(X))),
        ForAll([X], out(X) == Not(inn(X))),
        conflict_free(),
        ForAll([X], Not(And(inn(X), not_defended(X)))),
        ForAll([X], Implies(out(X), not_defended(X))),   # :- out, not not_defended
    ],
    # on-disk learned variants (Example1/)
    "PALT_STB": defs() + [
        ForAll([X], out(X) == defeated(X)),
        ForAll([X], inn(X) == Not(defeated(X))),      # in :- arg, not defeated
    ],
}


def entails(name_a, name_b, timeout_ms=120000):
    s = Solver()
    s.set("timeout", timeout_ms)
    for f in COMP[name_a]:
        s.add(f)
    s.add(Not(And(*COMP[name_b])))
    r = s.check()
    verdict = "PROVED" if r == unsat else ("REFUTED (countermodel exists)" if r == sat else "UNKNOWN")
    print(f"  {name_a} => {name_b}: {verdict}")
    if r == sat:
        print("    countermodel:", s.model())
    return r == unsat


def tightness_report():
    """Syntactic positive-dependency check (the Fages side condition)."""
    deps = {  # positive body dependencies per program family (arg omitted: extensional)
        "in": set(), "out": {"defeated", "not_defended"},
        "defeated": {"in", "att"}, "not_defended": {"att"},
    }
    # reachability: any cycle through these positive edges?
    def reach(p, seen):
        for q in deps.get(p, ()):
            if q == p or (q in seen) or reach(q, seen | {q}):
                return True
        return False
    cyc = [p for p in deps if reach(p, {p})]
    print(f"tightness (positive-dependency acyclicity): {'FAIL ' + str(cyc) if cyc else 'OK — all programs tight'}")
    return not cyc


if __name__ == "__main__":
    ok = tightness_report()
    print("\n== Theorem 1 (stable) ==")
    ok &= entails("P_STB", "S_STB") and entails("S_STB", "P_STB")
    print("== Theorem 2 (admissible) ==")
    ok &= entails("P_ADM", "S_ADM") and entails("S_ADM", "P_ADM")
    print("== Theorem 3 (complete) ==")
    ok &= entails("P_CMP", "S_CMP") and entails("S_CMP", "P_CMP")
    print("== On-disk stable variant (Example1/stable_learned.lp) ==")
    ok &= entails("PALT_STB", "S_STB") and entails("S_STB", "PALT_STB")
    print("\nALL PROVED" if ok else "\nNOT ALL PROVED — see above")
