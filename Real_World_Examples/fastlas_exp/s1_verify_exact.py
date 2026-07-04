#!/usr/bin/env python3
"""Stronger check: the LEARNED theory and the REFERENCE grounded theory produce the IDENTICAL
set of stable models (as in/out labellings) on every distinct D graph. If so they are
behaviourally equivalent given the det background, which is the strongest recovery claim."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F
import discover_semantics as D
import clingo

DET_BG = F.background("det", enrich=False)
REF = "in(X) :- supported(X).\nout(X) :- defeated(X)."
LEARNED = "out(V0) :- defeated(V0), arg(V0).\nin(V0) :- supported(V0), arg(V0)."


def modelset(program, args, attacks):
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], program + "\n" + facts + "\n#show in/1.\n#show out/1.\n")
    ctl.ground([("base", [])])
    ms = set()
    def on(m):
        ins = frozenset(("in", str(x.arguments[0])) for x in m.symbols(shown=True) if x.name == "in")
        outs = frozenset(("out", str(x.arguments[0])) for x in m.symbols(shown=True) if x.name == "out")
        ms.add(ins | outs)
    ctl.solve(on_model=on)
    return frozenset(ms)


def all_D_graphs():
    D.PHASE = "att_first__lab_first"; D.GRAPH = "own"
    recs = D.load_version("D")
    seen, gs = set(), []
    for r in recs:
        k = tuple(sorted(r["attacks"]))
        if k in seen:
            continue
        seen.add(k); gs.append(r)
    return gs


if __name__ == "__main__":
    gs = all_D_graphs()
    all_equal = True
    for g in gs:
        ref_ms = modelset(DET_BG + "\n" + REF, g["args"], g["attacks"])
        lrn_ms = modelset(DET_BG + "\n" + LEARNED, g["args"], g["attacks"])
        eq = ref_ms == lrn_ms
        all_equal &= eq
        print(f"attacks={g['attacks']} models_ref={len(ref_ms)} models_learned={len(lrn_ms)} EQUAL={eq}")
    print("\nALL GRAPHS: learned == reference (identical stable-model sets):", all_equal)
