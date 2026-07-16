#!/usr/bin/env python3
"""Level-1 machine-check of the three equivalence theorems in Zlatina's thesis §2.5
(abstract_proofs.pdf pp.24-32): for every AF F, AS(P_sem ∪ F) = AS(S_sem ∪ F), where
P_sem = ILASP-learned program (+ defeated/not_defended definitions, as stated in the
manuscript) and S_sem = the ASPARTIX-style encoding quoted in the manuscript.

Exhaustive over ALL labelled digraphs with n<=NMAX args (self-attacks INCLUDED), plus
the 500 campaign AAFs (n=4..8), plus the on-disk Example1 learned variants as secondary
subjects. Answer sets compared over {in,out,defeated,not_defended} (defs identical in
both programs, so full-visible-atom equality is the theorem's claim).

Usage: check_equivalence.py [NMAX]
  NMAX (positional, default 3) bounds the exhaustive sweep. The default is a quick
  smoke check; the committed level1_results.json was produced with NMAX=4 (66,066 AFs).
  Results are written to level1_results_regen.json so the committed record is never
  clobbered; diff the two files to compare.
"""
import itertools, json, sys, time
import clingo

# ---- programs exactly as in the manuscript ----
DEFS = "defeated(X):-att(Y,X), in(Y).\nnot_defended(X):-att(Y,X), not defeated(Y).\n"

P = {
 "STB": "out(X):-defeated(X).\nin(X):-arg(X), not out(X).\n" + DEFS,
 "ADM": ("out(X):-defeated(X).\nout(X):-arg(X), not in(X).\n"
         "in(X):-arg(X), not out(X), not not_defended(X).\n" + DEFS),
 "CMP": ("out(X):-not_defended(X).\nin(X):-arg(X), not out(X), not defeated(X).\n" + DEFS),
}
S = {
 "STB": ("in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n" + DEFS +
         ":- in(X), in(Y), att(X,Y).\n:- out(X), not defeated(X).\n"),
 "ADM": ("in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n" + DEFS +
         ":- in(X), in(Y), att(X,Y).\n:- in(X), not_defended(X).\n"),
 "CMP": ("in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n" + DEFS +
         ":- in(X), in(Y), att(X,Y).\n:- in(X), not_defended(X).\n:- out(X), not not_defended(X).\n"),
}
# on-disk learned variants (Example1/) as secondary subjects vs the same S
P_ALT = {
 "STB": "out(V1) :- defeated(V1).\nin(V1) :- arg(V1), not defeated(V1).\n" + DEFS,
 "ADM": ("out(V1) :- defeated(V1).\nout(V1) :- arg(V1), not in(V1).\n"
         "in(V1) :- arg(V1), not out(V1), not not_defended(V1).\n" + DEFS),
}

SHOW = "#show in/1. #show out/1. #show defeated/1. #show not_defended/1.\n"

def answer_sets(prog, facts):
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + facts + SHOW)
    ctl.ground([("base", [])])
    out = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            out.add(frozenset(str(a) for a in m.symbols(shown=True)))
    return out

def af_facts(n, edges):
    args = "".join(f"arg(a{i})." for i in range(n))
    atts = "".join(f"att(a{i},a{j})." for i, j in edges)
    return args + atts

def all_afs(n):
    pairs = [(i, j) for i in range(n) for j in range(n)]  # self-attacks included
    for mask in range(2 ** len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]

def main():
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    results = {}
    for label, progs in (("manuscript", P), ("ondisk_variant", P_ALT)):
        for sem in progs:
            t0 = time.time(); checked = 0; bad = []
            for n in range(1, nmax + 1):
                for edges in all_afs(n):
                    facts = af_facts(n, edges)
                    if answer_sets(progs[sem], facts) != answer_sets(S[sem], facts):
                        bad.append((n, edges))
                        if len(bad) >= 5: break
                    checked += 1
                if len(bad) >= 5: break
            results[f"{label}_{sem}"] = {"checked": checked, "counterexamples": [str(b) for b in bad],
                                         "secs": round(time.time() - t0, 1)}
            print(f"[{label} {sem}] {checked} AFs, {len(bad)} counterexamples ({results[f'{label}_{sem}']['secs']}s)",
                  flush=True)
            for b in bad: print("   CE:", b, flush=True)
    # campaign AAFs (n=4..8, dense)
    import glob, re, os
    camp = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..",
                  "data", "exp1_v2", "aafs", "*.lp")))
    for label, progs in (("manuscript", P),):
        for sem in progs:
            bad = 0; t0 = time.time()
            for f in camp:
                txt = open(f).read()
                if answer_sets(progs[sem], txt) != answer_sets(S[sem], txt): bad += 1
            print(f"[campaign {sem}] {len(camp)} AAFs, {bad} mismatches ({time.time()-t0:.0f}s)", flush=True)
            results[f"campaign_{sem}"] = {"checked": len(camp), "mismatches": bad}
    out_path = os.path.join(os.path.dirname(__file__), "level1_results_regen.json")
    json.dump(results, open(out_path, "w"), indent=1)
    print(f"DONE — wrote {out_path} (committed level1_results.json left untouched)", flush=True)
    if nmax < 4:
        print(f"NOTE: quick mode nmax={nmax}; pass 4 (or 5) as the positional argument "
              "for the exhaustive check behind the committed results.", flush=True)

if __name__ == "__main__":
    main()
