#!/usr/bin/env python3
"""FastLAS task construction for the argumentation semantics-learning task.

Design vs the ILASP pipeline (discover_semantics.py):
- FastLAS learns NORMAL rules (head :- body), not choice rules / constraints (except via the
  #modeh(false) trick). So we do NOT put 0{in}1/0{out}1 choice rules in the background. Instead
  in/out are DERIVED by the learned definite rules over deterministic structural features. With
  no choice, BG+H has a unique model per graph => in/out are directly observed => the task is a
  candidate for OPL (fast). The ILASP formulation needed choice+recursion => NOPL-only.
- Examples reuse the ILASP CDPI shape #pos(id, {inc}, {exc}, {ctx}); optional soft penalty id@w.
- Enrichment (reach/in_cycle) is cheap here because FastLAS searches the space differently.

Two background variants:
  det   : deterministic derived predicates, NO choice (Formulation C, aims OPL).
  choice: adds 0{in}1/0{out}1 (Formulation A, the ILASP-style; expected NOPL-only) -- for
          contrast experiments.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import discover_semantics as D  # loaders, GOLD, textbook_labellings, project, score, metrics

# ---- background variants (plain ASP, passed to clingo by FastLAS) ----
# NB: FastLAS's grammar rejects `:` conditional literals, so "all attackers out" is encoded via
# not_supported (X has some attacker not labelled out) + negation, not `out(Y):att(Y,X)`.
_DERIVED = """defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
not_supported(X) :- att(Y, X), not out(Y).
supported(X) :- arg(X), not not_supported(X).
:- arg(X), in(X), out(X)."""

_REACH = """reach(X, Y) :- att(X, Y).
reach(X, Z) :- att(X, Y), reach(Y, Z).
in_cycle(X) :- reach(X, X)."""

_CHOICE = """0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X)."""


def background(variant="det", enrich=False):
    parts = [_DERIVED]
    if enrich:
        parts.append(_REACH)
    if variant == "choice":
        parts.append(_CHOICE)
    return "\n".join(parts)


def modes(enrich=False, constraints=False):
    mh = ["#modeh(in(var(arg))).", "#modeh(out(var(arg)))."]
    if constraints:  # #modeh(false) lets FastLAS learn CONSTRAINTS (false :- body), needed to
        mh.append("#modeh(false).")  # PRUNE bad labellings that the choice rules would guess.
    mb = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).",
          "#modeb(att(var(arg), var(arg))).",
          "#modeb(defeated(var(arg))).", "#modeb(not_defended(var(arg))).",
          "#modeb(supported(var(arg)))."]
    if enrich:
        mb.append("#modeb(in_cycle(var(arg))).")
    return "\n".join(mh + mb)


BIAS = ('#bias("penalty(1, head) :- in_head(X).").\n'
        '#bias("penalty(1, body(X)) :- in_body(X).").')


def render_example(kind, eid, weight, args, attacks, commit):
    """kind in {pos,neg}. weight None -> plain; else soft id@weight. commit: {arg:in|out}."""
    incl, excl = [], []
    for a in args:
        s = commit.get(a)
        if s == "in":
            incl.append(f"in({a})"); excl.append(f"out({a})")
        elif s == "out":
            incl.append(f"out({a})"); excl.append(f"in({a})")
        else:
            excl.append(f"in({a})"); excl.append(f"out({a})")
    ctx = " ".join([f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks])
    idw = f"{eid}@{weight}" if weight else eid
    return f"#{kind}({idw}, {{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx}}})."


def shell_negs(cells):
    """Hamming-1 hard shell of each cell's labelling (reuses discover_semantics.hard_shell),
    deduped and minus any labelling that IS a positive. Rendered as #neg to force a pruning theory."""
    pos_keys = {(tuple(sorted(c["attacks"])), tuple(sorted(c["commit"].items()))) for c in cells}
    seen, negs = set(), []
    for c in cells:
        for neg in D.hard_shell(c["commit"]):
            key = (tuple(sorted(c["attacks"])), tuple(sorted(neg.items())))
            if key in pos_keys or key in seen:
                continue
            seen.add(key)
            negs.append({"args": c["args"], "attacks": c["attacks"], "commit": neg})
    return negs


def build_task(cells, variant="det", enrich=False, maxv=2, pos_weight=None, negs=None,
               neg_weight=None, constraints=False):
    """cells: list of dicts {args, attacks, commit[, weight]}. Returns the .las text.
    negs: optional list of dicts {args, attacks, commit} rendered as #neg.
    constraints=True adds #modeh(false) + a `:- false.` guard so pruning constraints are learnable."""
    bg = background(variant, enrich)
    if constraints:
        bg += "\n:- false."
    lines = [bg, "", modes(enrich, constraints), "", BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        w = c.get("weight", pos_weight)
        lines.append(render_example("pos", f"p{i}", w, c["args"], c["attacks"], c["commit"]))
    for j, c in enumerate(negs or []):
        lines.append(render_example("neg", f"n{j}", neg_weight, c["args"], c["attacks"], c["commit"]))
    return "\n".join(lines) + "\n"


def grounded_cells(v, kind="grounded", graph="own", label_phase="first", limit=None, dedup=True):
    """Synthetic CLEAN cells: each participant's own graph, labelled by the textbook `kind`
    (skeptical projection over its extensions -> a single well-defined labelling). For the
    recovery unit test (can FastLAS recover a known semantics)."""
    D.PHASE = {"first": "att_first__lab_first", "final": "att_final__lab_final",
               "group": "att_group__lab_group"}[label_phase]
    D.GRAPH = graph
    recs = D.load_version(v)
    seen, cells = set(), []
    for r in recs:
        args, attacks = r["args"], r["attacks"]
        labs = D.textbook_labellings(kind, args, attacks)
        if not labs:            # e.g. no stable extension on an odd cycle -> skip
            continue
        lab = D.project(labs, args, "skeptical")   # single well-defined target
        commit = {a: s for a, s in lab.items() if s in ("in", "out")}
        key = (tuple(sorted(attacks)), tuple(sorted(commit.items())))
        if dedup and key in seen:
            continue
        seen.add(key)
        cells.append({"args": args, "attacks": attacks, "commit": commit})
        if limit and len(cells) >= limit:
            break
    return cells
