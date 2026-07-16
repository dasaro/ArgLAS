#!/usr/bin/env python3
"""Machine-check of thesis §4.2 (claimed by example only): the two-step ABA->AAF translation.
Step 1: the clingo program (assume/root choices + Domain heuristics + domRec) enumerates,
for each derivable root, the arguments = subset-MINIMAL assumption sets deriving it.
Step 2: att(X,Y) :- contr(P,Q), root(X,Q), as(Y,P) yields exactly the ABA attacks
(X attacks Y iff root(X) is the contrary of some assumption in Y).
Reference: brute-force forward chaining over random small flat ABA frameworks."""
import itertools, random
import clingo

def derives(rules, assumptions, subset):
    """forward chaining: closure of subset under rules (assumptions hold iff in subset)."""
    holds = set(subset)
    changed = True
    while changed:
        changed = False
        for head, body in rules:
            if head not in holds and all(b in holds for b in body):
                holds.add(head); changed = True
    return holds

def ref_arguments(atoms, rules, assumptions):
    """all (root, minimal assumption set) pairs; roots may be any derivable sentence."""
    args = []
    for r in range(len(assumptions) + 1):
        for sub in itertools.combinations(sorted(assumptions), r):
            cl = derives(rules, assumptions, set(sub))
            for root in cl:
                args.append((root, frozenset(sub)))
    # keep subset-minimal support per root
    out = set()
    for root, sup in args:
        if not any(r2 == root and s2 < sup for r2, s2 in args):
            out.add((root, sup))
    return out

def thesis_step1(atoms, rules, assumptions):
    prog = "".join(f"as({a}).\n" for a in sorted(assumptions))
    for head, body in rules:
        prog += f"holds({head})" + (" :- " + ", ".join(f"holds({b})" for b in body) if body else "") + ".\n"
    prog += ("0{assume(X)}1 :- as(X).\nholds(X) :- assume(X).\n1{root(X): holds(X)}1.\n"
             "#heuristic assume(X) : as(X). [1, false]\n#heuristic root(X) : holds(X). [1, true]\n"
             "#show root/1.\n#show assume/1.\n")
    ctl = clingo.Control(["0", "--warn=none", "--heuristic=Domain", "--enum-mode=domRec"])
    ctl.add("base", [], prog)
    ctl.ground([("base", [])])
    res = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            root = [str(a.arguments[0]) for a in m.symbols(shown=True) if a.name == "root"]
            sup = frozenset(str(a.arguments[0]) for a in m.symbols(shown=True) if a.name == "assume")
            res.add((root[0], sup))
    return res

def ref_attacks(args_list, contraries):
    """X attacks Y iff root(X) = contrary(p) for some assumption p in Y's support."""
    res = set()
    for i, (rx, sx) in enumerate(args_list):
        for j, (ry, sy) in enumerate(args_list):
            if any(contraries.get(p) == rx for p in sy):
                res.add((i + 1, j + 1))
    return res

def thesis_step2(args_list, contraries):
    prog = ""
    for i, (root, sup) in enumerate(args_list):
        prog += f"root({i+1},{root}).\n" + "".join(f"as({i+1},{p}).\n" for p in sorted(sup))
    prog += "".join(f"contr({p},{c}).\n" for p, c in contraries.items())
    prog += "att(X,Y) :- contr(P,Q), root(X,Q), as(Y,P).\n#show att/2.\n"
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog)
    ctl.ground([("base", [])])
    with ctl.solve(yield_=True) as h:
        for m in h:
            return {(int(str(a.arguments[0])), int(str(a.arguments[1]))) for a in m.symbols(shown=True)}
    return set()

def rand_aba(rng):
    atoms = [f"s{i}" for i in range(rng.randint(3, 6))]
    assumptions = set(rng.sample(atoms, rng.randint(1, min(3, len(atoms)))))
    non_assum = [a for a in atoms if a not in assumptions]
    rules = []
    for _ in range(rng.randint(1, 5)):
        if not non_assum: break
        head = rng.choice(non_assum)   # flat ABA: assumptions never in heads
        body = rng.sample(atoms, rng.randint(0, 2))
        rules.append((head, body))
    contraries = {p: rng.choice(atoms) for p in assumptions}
    return atoms, rules, assumptions, contraries

def main():
    rng = random.Random(20260705)
    bad1 = bad2 = 0
    N = 500
    for t in range(N):
        atoms, rules, assumptions, contraries = rand_aba(rng)
        ref = ref_arguments(atoms, rules, assumptions)
        got = thesis_step1(atoms, rules, assumptions)
        if got != ref:
            bad1 += 1
            if bad1 <= 3:
                print(f"  STEP1 CE: rules={rules} asm={sorted(assumptions)}")
                print(f"    thesis={sorted(got)}\n    ref   ={sorted(ref)}")
        alist = sorted(ref)
        if thesis_step2(alist, contraries) != ref_attacks(alist, contraries):
            bad2 += 1
            if bad2 <= 3: print(f"  STEP2 CE: contr={contraries} args={alist}")
    print(f"{N} random flat ABA frameworks: step-1 mismatches={bad1}, step-2 mismatches={bad2}")
    print("CLAIM HOLDS" if bad1 == bad2 == 0 else "CLAIM FAILS")

if __name__ == "__main__":
    main()

# ---- FIX validation: per-root domRec over assume only (root pinned via constraint) ----
def fixed_step1(atoms, rules, assumptions):
    base = "".join(f"as({a}).\n" for a in sorted(assumptions))
    for head, body in rules:
        base += f"holds({head})" + (" :- " + ", ".join(f"holds({b})" for b in body) if body else "") + ".\n"
    base += ("0{assume(X)}1 :- as(X).\nholds(X) :- assume(X).\n"
             "#heuristic assume(X) : as(X). [1, false]\n#show assume/1.\n")
    res = set()
    for root in atoms:
        ctl = clingo.Control(["0", "--warn=none", "--heuristic=Domain", "--enum-mode=domRec"])
        ctl.add("base", [], base + f":- not holds({root}).\n")
        ctl.ground([("base", [])])
        with ctl.solve(yield_=True) as h:
            for m in h:
                res.add((root, frozenset(str(a.arguments[0]) for a in m.symbols(shown=True))))
    return res

def validate_fix():
    rng = random.Random(20260705)
    bad = 0
    for t in range(500):
        atoms, rules, assumptions, contraries = rand_aba(rng)
        if fixed_step1(atoms, rules, assumptions) != ref_arguments(atoms, rules, assumptions):
            bad += 1
    print(f"FIXED step-1 (per-root domRec over assume): 500 frameworks, {bad} mismatches")
    print("FIX VALIDATED" if bad == 0 else "FIX INSUFFICIENT")

if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "--fix":
    validate_fix()
