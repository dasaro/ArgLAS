#!/usr/bin/env python3
"""Strategy 3 (STRONG): same aaai-style latent-legality formulation, but the negative
examples include EVERY non-grounded labelling that the plain complete-legality check would
wrongly accept -- i.e. also the stable/complete extensions that sit Hamming-distance >1 from
the grounded labelling on cyclic graphs.  This forces FastLAS to distinguish GROUNDED from
merely COMPLETE, so that `ok` characterises the grounded labelling UNIQUELY.

We enumerate ALL 3^n labellings per graph; the single grounded one is the `ok` positive,
every other labelling is a `bad` positive.  (This is the full supervision, still supervising
only the top-level ok/bad -- the in/out justification stays latent.)

To pin down grounded (the MINIMAL complete labelling) we must let the hypothesis reason about
minimality.  We add a body feature that lets a rule say "X is justified-in only if it is
grounded-forced", encoded structurally: an argument is grounded-in iff it is supported AND
every attacker is *definitely* out (defeated), which for these graphs is what `supported`
already gives once out is only from `defeated`.  We keep the SAME mode bias; if grounded is
not separable from complete with these features, FastLAS returns UNSAT -- an informative
negative result about feature adequacy.
"""
import os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F
import s3_build as S


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


def build(cells, maxv=2, full=True):
    lines = [S.BG, "", S.MODES, "", S.BIAS, f"#maxv({maxv}).", ""]
    eid = 0
    for c in cells:
        args, attacks = c["args"], c["attacks"]
        gl = grounded_of(args, attacks)
        # positive: the grounded labelling is ok
        lines.append(S.example("pos", f"p{eid}", "ok", args, attacks, gl)); eid += 1
        if full:
            # every OTHER labelling is bad
            for combo in itertools.product(["in", "out", None], repeat=len(args)):
                lab = {a: v for a, v in zip(args, combo) if v is not None}
                if lab == gl:
                    continue
                lines.append(S.example("pos", f"n{eid}", "bad", args, attacks, lab)); eid += 1
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    cells = F.grounded_cells("D", "grounded")
    task = build(cells)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_grounded_strong.las")
    with open(path, "w") as f:
        f.write(task)
    print("wrote", path, "(%d lines)" % len(task.splitlines()))
