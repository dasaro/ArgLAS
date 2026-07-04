#!/usr/bin/env python3
"""Machine-check of thesis §4.5.2-4.5.4: the UNIFIED background (10 rules) is equivalent to
each specialized background (AAF/BAF/VAF) given contexts of the right signature. Checked by
comparing answer sets of [background + learned program + context] over in/out/defeated/
not_defended for the three learned semantic programs x random contexts of each type."""
import itertools, random, sys
import clingo

UNIFIED = """support(X,Z) :- support(X,Y), support(Y,Z).
supported(X) :- support(Y,X), in(Y).
valpref(X,Y) :- valpref(X,Z), valpref(Z,Y).
pref(X,Y) :- valpref(U,V), val(X,U), val(Y,V).
pref(X,Y) :- pref(X,Z), pref(Z,Y).
defeat(X,Y) :- att(Z,Y), support(X,Z).
defeat(X,Y) :- att(X,Z), support(Z,Y).
defeat(X,Y) :- att(X,Y), not pref(Y,X).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
"""
AAF_BG = "defeated(X) :- in(Y), att(Y,X).\nnot_defended(X) :- att(Y,X), not defeated(Y).\n"
BAF_BG = """support(X,Z) :- support(X,Y), support(Y,Z).
supported(X) :- support(Y,X), in(Y).
defeat(X,Y) :- att(Z,Y), support(X,Z).
defeat(X,Y) :- att(X,Z), support(Z,Y).
defeat(X,Y) :- att(X,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
"""
VAF_BG = """valpref(X,Y) :- valpref(X,Z), valpref(Z,Y).
pref(X,Y) :- valpref(U,V), val(X,U), val(Y,V).
pref(X,Y) :- pref(X,Z), pref(Z,Y).
defeat(X,Y) :- att(X,Y), not pref(Y,X).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
"""
LEARNED = {
 "STB": "out(X):-defeated(X).\nin(X):-arg(X), not out(X).\n",
 "ADM": "out(X):-defeated(X).\nout(X):-arg(X), not in(X).\nin(X):-arg(X), not out(X), not not_defended(X).\n",
 "CMP": "out(X):-not_defended(X).\nin(X):-arg(X), not out(X), not defeated(X).\n",
}
SHOW = "#show in/1. #show out/1. #show defeated/1. #show not_defended/1.\n"

def answer_sets(prog, facts):
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + facts + SHOW)
    ctl.ground([("base", [])])
    res = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            res.add(frozenset(str(a) for a in m.symbols(shown=True)))
    return res

def rand_ctx(kind, n, rng):
    A = [f"a{i}" for i in range(n)]
    f = "".join(f"arg({a})." for a in A)
    for x in A:
        for y in A:
            if rng.random() < 0.3: f += f"att({x},{y})."
    if kind == "BAF":
        for x in A:
            for y in A:
                if x != y and rng.random() < 0.2: f += f"support({x},{y})."
    if kind == "VAF":
        vals = ["v1", "v2", "v3"]
        for a in A: f += f"val({a},{rng.choice(vals)})."
        for u, v in itertools.permutations(vals, 2):
            if rng.random() < 0.3: f += f"valpref({u},{v})."
    return f

def main():
    rng = random.Random(20260705)
    spec = {"AAF": AAF_BG, "BAF": BAF_BG, "VAF": VAF_BG}
    bad = 0; tot = 0
    for kind in ("AAF", "BAF", "VAF"):
        for sem, prog in LEARNED.items():
            for trial in range(200):
                ctx = rand_ctx(kind, rng.randint(2, 5), rng)
                tot += 1
                if answer_sets(UNIFIED + prog, ctx) != answer_sets(spec[kind] + prog, ctx):
                    bad += 1
                    if bad <= 3: print(f"  CE [{kind} {sem}]: {ctx[:120]}")
        print(f"[{kind}] done", flush=True)
    print(f"unified-vs-specialized: {tot} checks, {bad} mismatches")
    print("CLAIM HOLDS" if bad == 0 else "CLAIM FAILS")

if __name__ == "__main__":
    main()
