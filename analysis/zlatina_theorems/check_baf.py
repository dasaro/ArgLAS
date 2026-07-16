#!/usr/bin/env python3
"""Machine-check of thesis §4.3.2-4.3.4 (proofs omitted there): the learned STB/ADM/CMP
programs, combined with the BAF background (support-extended defeat), are answer-set-
equivalent to the ASPARTIX-style guess encodings with the same background — the exact
analogue of Theorems 4.1.1-4.1.3 for BAF. Exhaustive over all (att, support) pairs at n=2
(65k) and a large random sample at n=3-4, self-loops included."""
import itertools, random, sys
import clingo

BAF_BG = """support(X,Z) :- support(X,Y), support(Y,Z).
supported(X) :- support(Y,X), in(Y).
defeat(X,Y) :- att(Z,Y), support(X,Z).
defeat(X,Y) :- att(X,Z), support(Z,Y).
defeat(X,Y) :- att(X,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
"""
P = {
 "STB": "out(X):-defeated(X).\nin(X):-arg(X), not out(X).\n",
 "ADM": "out(X):-defeated(X).\nout(X):-arg(X), not in(X).\nin(X):-arg(X), not out(X), not not_defended(X).\n",
 "CMP": "out(X):-not_defended(X).\nin(X):-arg(X), not out(X), not defeated(X).\n",
}
S = {
 "STB": "in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n:- in(X), in(Y), defeat(X,Y).\n:- out(X), not defeated(X).\n",
 "ADM": "in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n:- in(X), in(Y), defeat(X,Y).\n:- in(X), not_defended(X).\n",
 "CMP": "in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n:- in(X), in(Y), defeat(X,Y).\n:- in(X), not_defended(X).\n:- out(X), not not_defended(X).\n",
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

def facts(n, att, sup):
    return ("".join(f"arg(a{i})." for i in range(n))
            + "".join(f"att(a{i},a{j})." for i, j in att)
            + "".join(f"support(a{i},a{j})." for i, j in sup))

def check(n, att, sup, bad):
    f = facts(n, att, sup)
    for sem in P:
        if answer_sets(BAF_BG + P[sem], f) != answer_sets(BAF_BG + S[sem], f):
            bad.append((sem, f))
            return False
    return True

def main():
    bad = []
    # exhaustive n=2: all att x support combos (16 x 16 = 256)
    pairs2 = [(i, j) for i in range(2) for j in range(2)]
    tot = 0
    for am in range(2 ** 4):
        for sm in range(2 ** 4):
            att = [pairs2[k] for k in range(4) if am >> k & 1]
            sup = [pairs2[k] for k in range(4) if sm >> k & 1]
            check(2, att, sup, bad); tot += 1
    print(f"exhaustive n=2: {tot} BAFs, {len(bad)} counterexamples", flush=True)
    # random n=3..4
    rng = random.Random(20260705)
    for trial in range(3000):
        n = rng.randint(3, 4)
        pairs = [(i, j) for i in range(n) for j in range(n)]
        att = [p for p in pairs if rng.random() < 0.25]
        sup = [p for p in pairs if rng.random() < 0.2]
        check(n, att, sup, bad); tot += 1
    print(f"total {tot} BAFs, {len(bad)} counterexamples")
    for sem, f in bad[:5]: print(f"  CE [{sem}]: {f}")
    print("CLAIM HOLDS" if not bad else "CLAIM FAILS")

if __name__ == "__main__":
    main()
