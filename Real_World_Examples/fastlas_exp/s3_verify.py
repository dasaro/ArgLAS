#!/usr/bin/env python3
"""Strategy-3 verification harness (clingo-backed, fixpoint / grounded semantics).

GROUNDED semantics = least fixpoint of the characteristic operator.  A learned theory
defines in/1 and out/1 from the deterministic structural features (defeated, supported,
not_defended, att, ...).  To reproduce grounded we iterate the theory to a fixpoint:
each round we take the CURRENT in/out facts, add the det background + learned rules, and
let CLINGO compute the new in/out (a single deterministic step, because with in/out given
as facts the det features are fully determined and the learned rules are definite).  We
repeat until no change.  The fixpoint is compared to the grounded labelling (== commit).

This is exactly the operational meaning of grounded semantics, and every step is a real
clingo call, so success is clingo-verified, not merely trusted from FastLAS output.
"""
import subprocess, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F

# det background WITHOUT the ":- in,out" constraint (we compute a fixpoint, mono step)
DET_FEATURES = """defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
not_supported(X) :- att(Y, X), not out(Y).
supported(X) :- arg(X), not not_supported(X)."""


def graph_facts(c):
    return " ".join([f"arg({a})." for a in c["args"]] +
                    [f"att({s},{t})." for s, t in c["attacks"]])


def fixpoint(theory, c, max_rounds=20):
    """Iterate the learned theory to a least fixpoint. Returns (in_set, out_set) or None
    if any step is inconsistent (in&out for same arg)."""
    cur_in, cur_out = set(), set()
    facts = graph_facts(c)
    for _ in range(max_rounds):
        cur_facts = " ".join([f"in({a})." for a in cur_in] + [f"out({a})." for a in cur_out])
        prog = (DET_FEATURES + "\n" + theory + "\n" + facts + "\n" + cur_facts +
                "\n#show in/1.\n#show out/1.\n")
        # cautious (intersection of all stable models) = deterministic consequence for this step
        r = subprocess.run(["clingo", "--models=0", "--enum-mode=cautious"],
                           input=prog, capture_output=True, text=True)
        out = r.stdout
        if "UNSATISFIABLE" in out:
            return None
        ans = re.findall(r"Answer:.*\n(.*)", out)
        model = ans[-1] if ans else ""
        new_in = set(re.findall(r"in\((\w+)\)", model))
        new_out = set(re.findall(r"out\((\w+)\)", model))
        # inconsistency guard
        if new_in & new_out:
            return None
        if new_in == cur_in and new_out == cur_out:
            return cur_in, cur_out
        cur_in, cur_out = new_in, new_out
    return cur_in, cur_out


def expected(c):
    ins = {a for a, s in c["commit"].items() if s == "in"}
    outs = {a for a, s in c["commit"].items() if s == "out"}
    return ins, outs


def verify(theory, verbose=True):
    cells = F.grounded_cells("D", "grounded")
    ok = True
    for i, c in enumerate(cells):
        ei, eo = expected(c)
        res = fixpoint(theory, c)
        if res is None:
            gi, go = None, None
        else:
            gi, go = res
        match = (gi == ei and go == eo)
        ok = ok and match
        if verbose:
            print(f"cell {i} att={c['attacks']}")
            print(f"    expected in={sorted(ei)} out={sorted(eo)}")
            print(f"    got      in={sorted(gi) if gi is not None else None} "
                  f"out={sorted(go) if go is not None else None}  "
                  f"{'OK' if match else 'MISMATCH'}")
    if verbose:
        print("ALL-MATCH:", ok)
    return ok


if __name__ == "__main__":
    theory = "in(X) :- supported(X).\nout(X) :- defeated(X)."
    if len(sys.argv) > 1:
        theory = open(sys.argv[1]).read()
    print("THEORY:\n" + theory)
    verify(theory)
