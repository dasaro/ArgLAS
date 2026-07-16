#!/usr/bin/env python3
"""Verify a learned theory reproduces the GROUNDED labelling on all D graphs, via clingo.
Ground truth per graph = unique stable model of (det background + {in:-supported. out:-defeated.}
+ graph facts). We solve (det background + LEARNED rules + graph facts) and check the in/out
projection equals the grounded target on every arg for every distinct D graph.

Usage: python3 s1_verify.py "<rule1> <rule2> ..."  (rules separated by newlines/periods)
or import verify(rules_text) -> dict.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import discover_semantics as D
import fl_build as F
import clingo

# The det background WITHOUT choice (the derivation engine). Learned in/out rules are added.
DET_BG = F.background("det", enrich=False)
# For enrichment support if a learned theory used in_cycle, add reach too:
DET_BG_ENR = F.background("det", enrich=True)

# grounded reference theory
GROUNDED = "in(X) :- supported(X).\nout(X) :- defeated(X)."


def _labelling(program, args, attacks):
    """Return list of {arg: in/out/undec} models of program+facts. Empty if UNSAT/no model."""
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], program + "\n" + facts + "\n#show in/1.\n#show out/1.\n")
    ctl.ground([("base", [])])
    models = []
    def on_model(m):
        ins = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "in"}
        outs = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "out"}
        models.append({a: ("in" if a in ins else "out" if a in outs else "undec") for a in args})
    ctl.solve(on_model=on_model)
    return models


def grounded_target(args, attacks):
    """Ground truth = the (unique) grounded labelling from the ASPARTIX grounded encoding,
    the SAME source grounded_cells uses. in = grounded extension; out = attacked by in;
    undec = rest. (Brute stable models of det+GROUNDED are NOT unique on even cycles because
    the supported/defeated definitions loop through negation; the grounded fixpoint is the
    intended target.)"""
    D.PHASE = "att_first__lab_first"; D.GRAPH = "own"
    labs = D.textbook_labellings("grounded", args, attacks)
    lab = D.project(labs, args, "skeptical")  # grounded is unique -> projection is itself
    return {a: lab.get(a, "undec") for a in args}


def all_D_graphs():
    """All distinct D graphs (dedup by attack set), each with its grounded target."""
    D.PHASE = "att_first__lab_first"; D.GRAPH = "own"
    recs = D.load_version("D")
    seen, graphs = set(), []
    for r in recs:
        key = tuple(sorted(r["attacks"]))
        if key in seen:
            continue
        seen.add(key)
        graphs.append({"args": r["args"], "attacks": r["attacks"],
                       "grounded": grounded_target(r["args"], r["attacks"])})
    return graphs


def _skeptical(program, args, attacks):
    """Skeptical (cautious) in/out per arg = label true in EVERY stable model; else undec.
    This equals the well-founded / grounded reading for these programs. Returns None if the
    program has NO stable model (UNSAT) -> a broken theory."""
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], program + "\n" + facts + "\n#show in/1.\n#show out/1.\n")
    ctl.ground([("base", [])])
    in_all, out_all = None, None
    any_model = [False]
    def on_model(m):
        any_model[0] = True
        ins = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "in"}
        outs = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "out"}
        nonlocal in_all, out_all
        in_all = ins if in_all is None else (in_all & ins)
        out_all = outs if out_all is None else (out_all & outs)
    ctl.solve(on_model=on_model)
    if not any_model[0]:
        return None
    return {a: ("in" if a in in_all else "out" if a in out_all else "undec") for a in args}


def verify(rules_text, enrich=False, strict_unique=False):
    """Reproduces grounded iff the theory's SKEPTICAL (well-founded) in/out equals grounded on
    every distinct D graph. strict_unique also demands a single stable model (stronger claim)."""
    bg = DET_BG_ENR if enrich else DET_BG
    graphs = all_D_graphs()
    n_ok, n_unique = 0, 0
    fails = []
    for g in graphs:
        prog = bg + "\n" + rules_text
        skept = _skeptical(prog, g["args"], g["attacks"])
        models = _labelling(prog, g["args"], g["attacks"])
        target = g["grounded"]
        ok = (skept is not None and skept == target)
        if ok:
            n_ok += 1
        if len(models) == 1 and models[0] == target:
            n_unique += 1
        if not ok:
            fails.append({"attacks": g["attacks"], "target": target,
                          "skeptical": skept, "n_models": len(models),
                          "sample_models": models[:3]})
    all_ok = (n_ok == len(graphs)) if not strict_unique else (n_unique == len(graphs))
    return {"n_graphs": len(graphs), "n_ok_skeptical": n_ok, "n_ok_unique": n_unique,
            "all_ok": all_ok, "fails": fails[:6]}


if __name__ == "__main__":
    import json
    rules = sys.argv[1] if len(sys.argv) > 1 else GROUNDED
    enrich = "--enrich" in sys.argv
    res = verify(rules, enrich=enrich)
    print(json.dumps(res, indent=2))
