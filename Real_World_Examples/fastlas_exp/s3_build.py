#!/usr/bin/env python3
"""Strategy 3: aaai_2020_task-style LATENT-predicate learning for grounded semantics.

Pattern (from FastLAS's own working aaai_2020_task.las):
  - a TOP-LEVEL observed predicate `valid/invalid` is supervised;
  - `valid :- not invalid.`  and  `invalid :- <observed thing>, not <latent>(...).`
  - the LATENT predicate (`valid_move`) is what FastLAS learns via #modeh, never observed.

Here the "observed thing" is a LABELLING of the context graph provided as `lab(X,in)` /
`lab(X,out)` facts; the top-level supervised predicate is `ok` (legal labelling) / `bad`.
We supervise `ok` on the TRUE grounded labelling of each graph, and `bad` on Hamming-1
perturbations of it.  FastLAS must learn the LATENT justification predicates `just_in(X)`,
`just_out(X)` (the acceptance conditions) so that ok<->the labelling is the grounded one.

The deterministic structural features are computed from the OBSERVED `lab`, so they are
always available (no dependence on a to-be-derived target) -- this is exactly what the
aaai pattern buys us and what the det/OPL formulation lacked.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F
import discover_semantics as D  # noqa

# ---------------------------------------------------------------------------
# Background: structural features over the OBSERVED labelling `lab/2`, plus the
# legality machinery.  `just_in`, `just_out` are LATENT (learned).
# ---------------------------------------------------------------------------
BG = """% --- structural features over the observed labelling lab/2 ---
defeat(X, Y) :- att(X, Y).
defeated(X) :- lab(Y, in), defeat(Y, X).
not_supported(X) :- att(Y, X), not lab(Y, out).
supported(X) :- arg(X), not not_supported(X).

% --- legality: the labelling is bad if any label is not justified, OR a decidable
%     argument was left undecided (grounded completeness). ---
undec(X) :- arg(X), not lab(X, in), not lab(X, out).
bad :- lab(X, in),  not just_in(X).
bad :- lab(X, out), not just_out(X).
bad :- undec(X), just_in(X).
bad :- undec(X), just_out(X).
ok :- not bad.
"""

MODES = """#modeh(just_in(var(arg))).
#modeh(just_out(var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(att(var(arg), var(arg))).
#modeb(not supported(var(arg))).
#modeb(not defeated(var(arg))).
"""

BIAS = ('#bias("penalty(1, head) :- in_head(X).").\n'
        '#bias("penalty(1, body(X)) :- in_body(X).").')


def lab_ctx(args, attacks, commit):
    """Context = graph facts + the labelling `lab(X,in|out)` for decided args."""
    facts = [f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks]
    for a in args:
        s = commit.get(a)
        if s in ("in", "out"):
            facts.append(f"lab({a},{s}).")
    return " ".join(facts)


def example(kind, eid, top, args, attacks, commit):
    """top in {'ok','bad'}.  Supervise ONLY the top-level predicate."""
    incl = [top]
    excl = ["bad" if top == "ok" else "ok"]
    ctx = lab_ctx(args, attacks, commit)
    return f"#{kind}({eid}, {{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx}}})."


def perturbations(commit, args):
    """Hamming-1 relabellings of `commit` (flip a decided arg to the other/undec, or
    decide an undecided arg).  Returns list of commit dicts != commit."""
    labels = ["in", "out", None]
    out = []
    seen = {tuple(sorted((k, v) for k, v in commit.items()))}
    for a in args:
        cur = commit.get(a)
        for new in labels:
            if new == cur:
                continue
            nc = dict(commit)
            if new is None:
                nc.pop(a, None)
            else:
                nc[a] = new
            key = tuple(sorted((k, v) for k, v in nc.items()))
            if key in seen:
                continue
            seen.add(key)
            out.append(nc)
    return out


def build(cells, maxv=2, negs_per_cell=None, with_neg=True):
    lines = [BG, "", MODES, "", BIAS, f"#maxv({maxv}).", ""]
    eid = 0
    for c in cells:
        lines.append(example("pos", f"p{eid}", "ok", c["args"], c["attacks"], c["commit"]))
        eid += 1
    if with_neg:
        for c in cells:
            perts = perturbations(c["commit"], c["args"])
            if negs_per_cell:
                perts = perts[:negs_per_cell]
            for nc in perts:
                lines.append(example("pos", f"n{eid}", "bad", c["args"], c["attacks"], nc))
                eid += 1
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    cells = F.grounded_cells("D", "grounded")
    task = build(cells)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_grounded.las")
    with open(path, "w") as f:
        f.write(task)
    print("wrote", path)
    print(task)
