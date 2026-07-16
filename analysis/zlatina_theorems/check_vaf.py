#!/usr/bin/env python3
"""Sanity check for the VAF equivalence theorem (paper §4, Theorem 4 / Corollary 2).

(a) Theorem form: pref an ARBITRARY input relation; defeat(X,Y) :- att(X,Y), not pref(Y,X)
    on both sides; learned P_sigma + D-style defs vs guess-style S_sigma reading defeat.
    Answer sets restricted to {in,out} must coincide.
(b) Corollary form: pref derived by the recursive VAF background (valpref closure ->
    audience preference -> pref closure) on both sides.

Exhaustive over all digraphs with n<=3 (self-attacks included); for each graph,
several value assignments and valpref/pref configurations.
"""
import itertools, random, sys
import clingo

DEFEAT_INPUT = "defeat(X,Y) :- att(X,Y), not pref(Y,X).\n"
VAF_DERIVE = """valpref(X,Y) :- valpref(X,Z), valpref(Z,Y).
pref(X,Y) :- valpref(U,V), val(X,U), val(Y,V).
pref(X,Y) :- pref(X,Z), pref(Z,Y).
defeat(X,Y) :- att(X,Y), not pref(Y,X).
"""
DEFS = "defeated(X) :- in(Y), defeat(Y,X).\nnot_defended(X) :- defeat(Y,X), not defeated(Y).\n"

LEARNED = {
    "STB": "out(X):-defeated(X).\nin(X):-arg(X), not out(X).\n",
    "ADM": "out(X):-defeated(X).\nout(X):-arg(X), not in(X).\n"
           "in(X):-arg(X), not out(X), not not_defended(X).\n",
    "CMP": "out(X):-not_defended(X).\nin(X):-arg(X), not out(X), not defeated(X).\n",
}
GUESS = {
    "STB": "in(X) :- not out(X), arg(X).\nout(X) :- not in(X), arg(X).\n"
           ":- in(X), in(Y), defeat(X,Y).\ndefeated(X) :- in(Y), defeat(Y,X).\n"
           ":- out(X), not defeated(X).\n",
    "ADM": "in(X) :- not out(X), arg(X).\nout(X) :- not in(X), arg(X).\n"
           ":- in(X), in(Y), defeat(X,Y).\ndefeated(X) :- in(Y), defeat(Y,X).\n"
           "not_defended(X) :- defeat(Y,X), not defeated(Y).\n:- in(X), not_defended(X).\n",
    "CMP": "in(X) :- not out(X), arg(X).\nout(X) :- not in(X), arg(X).\n"
           ":- in(X), in(Y), defeat(X,Y).\ndefeated(X) :- in(Y), defeat(Y,X).\n"
           "not_defended(X) :- defeat(Y,X), not defeated(Y).\n:- in(X), not_defended(X).\n"
           ":- out(X), not not_defended(X).\n",
}
SHOW = "#show in/1.\n#show out/1.\n"


def answer_sets(prog, facts):
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + facts + SHOW)
    ctl.ground([("base", [])])
    out = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            out.add(frozenset(str(a) for a in m.symbols(shown=True)))
    return out


def main():
    rng = random.Random(20260716)
    checked = bad = 0
    for n in (1, 2, 3):
        args = [f"a{i}" for i in range(n)]
        arg_facts = "".join(f"arg({a}). " for a in args)
        pairs = [(x, y) for x in args for y in args]
        for att_bits in range(2 ** len(pairs)):
            atts = [p for i, p in enumerate(pairs) if att_bits >> i & 1]
            att_facts = "".join(f"att({x},{y}). " for x, y in atts)
            # (a) arbitrary input pref: empty, full, and 2 random subsets
            pref_configs = [[], list(pairs)]
            for _ in range(2):
                pref_configs.append([p for p in pairs if rng.random() < 0.4])
            for pref in pref_configs:
                pf = "".join(f"pref({x},{y}). " for x, y in pref)
                facts = arg_facts + att_facts + pf
                for sem in LEARNED:
                    a = answer_sets(LEARNED[sem] + DEFS + DEFEAT_INPUT, facts)
                    b = answer_sets(GUESS[sem] + DEFEAT_INPUT, facts)
                    checked += 1
                    if a != b:
                        bad += 1
                        print("MISMATCH(a)", sem, facts)
            # (b) derived pref: values + valpref
            vals = ["v0", "v1"]
            val_facts = "".join(f"val({a},{vals[i % 2]}). " for i, a in enumerate(args))
            for vp in ([], [("v0", "v1")], [("v0", "v1"), ("v1", "v0")]):
                vpf = "".join(f"valpref({u},{v}). " for u, v in vp)
                facts = arg_facts + att_facts + val_facts + vpf
                for sem in LEARNED:
                    a = answer_sets(LEARNED[sem] + DEFS + VAF_DERIVE, facts)
                    b = answer_sets(GUESS[sem] + VAF_DERIVE, facts)
                    checked += 1
                    if a != b:
                        bad += 1
                        print("MISMATCH(b)", sem, facts)
    print(f"checked {checked} program pairs, mismatches: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
