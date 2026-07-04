#!/usr/bin/env python3
"""Machine-check of the thesis's UNPROVED claims (§4.1.5, §4.1.6): the learned heuristic
encodings, run under clingo --heuristic=Domain --enum-mode=domRec, enumerate exactly the
grounded / preferred extensions. The thesis states these are 'empirically evaluated' only —
this script checks them exhaustively (all AFs n<=3, all n=4, 500 campaign AAFs), comparing
IN-SETS against independent references (grounded: least fixpoint; preferred: subset-maximal
admissible computed by brute force)."""
import glob, itertools, os, re, sys
import clingo

DEFS = "defeated(X):-in(Y), att(Y,X).\nnot_defended(X):-att(Y,X), not defeated(Y).\n"
GRD_THESIS = ("in(X) :- arg(X), not not_defended(X).\nout(X) :- not_defended(X).\n" + DEFS +
              "#heuristic in(X) : arg(X). [1@1, false]\n")
PRF_THESIS = ("in(X) :- arg(X), not defeated(X), not not_defended(X).\nout(X) :- not_defended(X).\n" + DEFS +
              "#heuristic out(X) : arg(X). [1@1, false]\n")

def models_insets(prog, facts, domrec):
    args = ["0", "--warn=none"] + (["--heuristic=Domain", "--enum-mode=domRec"] if domrec else [])
    ctl = clingo.Control(args)
    ctl.add("base", [], prog + facts + "#show in/1.\n")
    ctl.ground([("base", [])])
    out = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            out.add(frozenset(str(a.arguments[0]) for a in m.symbols(shown=True)))
    return out

def parse_args_atts(facts):
    A = re.findall(r"arg\((\w+)\)", facts); T = re.findall(r"att\((\w+),(\w+)\)", facts)
    return A, T

def grounded_inset(facts):
    A, T = parse_args_atts(facts)
    inn = set(); out = set()
    while True:
        new_in = {a for a in A if a not in inn | out and all(y in out for y, x in T if x == a)}
        if not new_in: break
        inn |= new_in
        out |= {x for y, x in T if y in inn}
    return frozenset(inn)

def preferred_insets(facts):
    A, T = parse_args_atts(facts)
    att = set(T)
    adm = []
    for r in range(len(A) + 1):
        for S in itertools.combinations(A, r):
            Sset = set(S)
            if any((x, y) in att for x in Sset for y in Sset): continue
            if all(all(any((z, y) in att for z in Sset) for y, xx in att if xx == x and (y,xx) in att) for x in Sset):
                # defended: every attacker y of x is attacked by S
                if all(all(any((z, y) in att for z in Sset) for (y, xx) in att if xx == x) for x in Sset):
                    adm.append(frozenset(Sset))
    return {s for s in adm if not any(s < t for t in adm)}

def af_facts(n, edges):
    return "".join(f"arg(a{i})." for i in range(n)) + "".join(f"att(a{i},a{j})." for i, j in edges)

def check(facts):
    g = models_insets(GRD_THESIS, facts, domrec=True)
    ok_g = g == {grounded_inset(facts)}
    p = models_insets(PRF_THESIS, facts, domrec=True)
    ok_p = p == preferred_insets(facts)
    return ok_g, ok_p, g, p

def main():
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    badg, badp, tot = [], [], 0
    for n in range(1, nmax + 1):
        pairs = [(i, j) for i in range(n) for j in range(n)]
        for mask in range(2 ** len(pairs)):
            edges = [pairs[k] for k in range(len(pairs)) if mask >> k & 1]
            facts = af_facts(n, edges)
            ok_g, ok_p, g, p = check(facts)
            tot += 1
            if not ok_g and len(badg) < 5:
                badg.append((facts, sorted(map(sorted, g)), sorted(grounded_inset(facts))))
            if not ok_p and len(badp) < 5:
                badp.append((facts, sorted(map(sorted, p)), sorted(map(sorted, preferred_insets(facts)))))
    print(f"exhaustive n<={nmax}: {tot} AFs")
    print(f"  GRD-heuristic claim: {'HOLDS on all' if not badg else 'FAILS'}")
    for f, got, want in badg: print(f"    CE: {f}\n      domRec in-sets={got}  grounded={want}")
    print(f"  PRF-heuristic claim: {'HOLDS on all' if not badp else 'FAILS'}")
    for f, got, want in badp: print(f"    CE: {f}\n      domRec in-sets={got}  preferred={want}")
    # campaign AAFs
    camp = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..",
                  "artifacts", "final_synthetic_v2", "aafs", "*.lp")))
    bg = bp = 0
    for f in camp:
        txt = open(f).read()
        ok_g, ok_p, _, _ = check(txt)
        bg += (not ok_g); bp += (not ok_p)
    print(f"campaign 500 AAFs: GRD mismatches={bg}  PRF mismatches={bp}")
    print("DONE")

if __name__ == "__main__":
    main()
