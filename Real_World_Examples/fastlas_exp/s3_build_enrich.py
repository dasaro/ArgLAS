#!/usr/bin/env python3
"""Strategy 3 (ENRICHED): try to recover GROUNDED under the UNIQUE-ok reading by giving the
learner a feature that captures the minimality/least-fixpoint distinction between grounded and
the other complete labellings.

Grounded semantics = LEAST complete labelling.  The pairs that the plain `supported/defeated`
features cannot separate are the two symmetric stable extensions of an even cycle (a<->b),
where grounded leaves both UNDEC.  The distinguishing structural fact is: an argument is
grounded-IN only if it is *unattacked or defended by grounded-in args* -- a recursive
least-fixpoint notion.  We expose two extra background features computed by a DETERMINISTIC
(stratified) least fixpoint that does NOT reference the observed lab (so it is always available):

  fp_in(X)  : X is in the GROUNDED extension of the context graph (computed structurally)
  fp_out(X) : X is out in the grounded extension

If FastLAS is allowed these as body features, it can learn just_in(X):-fp_in(X) etc., which
DO pin down grounded uniquely.  This tests whether the pattern can express grounded once a
minimality-aware feature is supplied (the memory's 'needs minimality heuristics' point).
"""
import os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F
import s3_build as S

# The grounded fixpoint is provided as PRECOMPUTED FACTS per example context (fp_in/fp_out),
# computed in Python (guaranteed correct; avoids the stable-vs-well-founded gap in-language).
FP = ""  # no background rules needed; feature comes in as context facts

BG2 = S.BG

MODES2 = S.MODES + """#modeb(fp_in(var(arg))).
#modeb(fp_out(var(arg))).
"""


def grounded_of(args, attacks):
    label = {}
    changed = True
    while changed:
        changed = False
        for x in args:
            if x in label:
                continue
            atk = [y for (y, z) in attacks if z == x]
            if all(label.get(y) == "out" for y in atk):
                label[x] = "in"; changed = True
            elif any(label.get(y) == "in" for y in atk):
                label[x] = "out"; changed = True
    return label


def example(kind, eid, top, args, attacks, commit):
    """Like S.example but ALSO injects precomputed fp_in/fp_out facts into the context."""
    incl = [top]
    excl = ["bad" if top == "ok" else "ok"]
    ctx = S.lab_ctx(args, attacks, commit)
    gl = grounded_of(args, attacks)
    fp = " ".join([f"fp_in({a})." for a, s in gl.items() if s == "in"] +
                  [f"fp_out({a})." for a, s in gl.items() if s == "out"])
    return f"#{kind}({eid}, {{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx} {fp}}})."


def build(cells, maxv=2):
    lines = [BG2, "", MODES2, "", S.BIAS, f"#maxv({maxv}).", ""]
    eid = 0
    for c in cells:
        args, attacks = c["args"], c["attacks"]
        gl = grounded_of(args, attacks)
        lines.append(example("pos", f"p{eid}", "ok", args, attacks, gl)); eid += 1
        for combo in itertools.product(["in", "out", None], repeat=len(args)):
            lab = {a: v for a, v in zip(args, combo) if v is not None}
            if lab == gl:
                continue
            lines.append(example("pos", f"n{eid}", "bad", args, attacks, lab)); eid += 1
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    cells = F.grounded_cells("D", "grounded")
    # sanity: check the FP feature computes grounded in clingo (unique)
    task = build(cells)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_grounded_enrich.las")
    with open(path, "w") as f:
        f.write(task)
    print("wrote", path, "(%d lines)" % len(task.splitlines()))
