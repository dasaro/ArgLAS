#!/usr/bin/env python3
"""STRATEGY 2 verification: does BG + learned constraints (+choice+minimize) reproduce
GROUNDED on ALL 5 D graphs? clingo is the oracle."""
import subprocess
import fl_build as F

BG = F.background("det")

# the theory FastLAS learned (OPL == NOPL), constraints-only:
LEARNED = """false :- supported(X), not in(X).
false :- defeated(X), not out(X).
:- false."""

# deploy-time scaffolding (FIXED, not learned): choice generate + grounded = minimal complete
DEPLOY = """0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- arg(X), in(X), out(X).
#minimize { 1,X : in(X) ; 1,X : out(X) }.
#show in/1.
#show out/1."""


def grounded_via_theory(args, attacks):
    facts = " ".join([f"arg({a})." for a in args] +
                     [f"att({s},{t})." for s, t in attacks])
    prog = "\n".join([BG, LEARNED, DEPLOY, facts])
    r = subprocess.run(["clingo", "--outf=0", "--opt-mode=optN", "-n", "0"],
                       input=prog, capture_output=True, text=True)
    optima = []
    capture = False
    for line in r.stdout.splitlines():
        if line.startswith("Answer:") or line.startswith("Optimization:"):
            continue
        if "in(" in line or "out(" in line or line.strip() == "":
            d = {}
            for at in line.split():
                if at.startswith("in("):
                    d[at[3:-1]] = "in"
                elif at.startswith("out("):
                    d[at[4:-1]] = "out"
            if any(k in line for k in ("in(", "out(")):
                optima.append(d)
    # under optN clingo prints each improving model; the final printed model(s) are optimal.
    # Re-run with plain optimum to get THE grounded model deterministically:
    r2 = subprocess.run(["clingo", "--outf=0"], input=prog, capture_output=True, text=True)
    best = {}
    for line in r2.stdout.splitlines():
        if "in(" in line or "out(" in line:
            best = {}
            for at in line.split():
                if at.startswith("in("):
                    best[at[3:-1]] = "in"
                elif at.startswith("out("):
                    best[at[4:-1]] = "out"
    unsat = "UNSATISFIABLE" in r2.stdout
    return best, unsat


if __name__ == "__main__":
    cells = F.grounded_cells("D", "grounded")
    ok = 0
    print("cell | attacks | GROUNDED (gold) | theory-derived | match")
    for i, c in enumerate(cells):
        derived, unsat = grounded_via_theory(c["args"], c["attacks"])
        gold = c["commit"]
        match = (derived == gold) and not unsat
        ok += match
        print(f"  {i}  | {c['attacks']} | {gold} | {derived} | "
              f"{'OK' if match else 'FAIL'}")
    print(f"\nRECOVERED {ok}/{len(cells)} grounded labellings via BG + learned C2+C4 + choice + minimize")
