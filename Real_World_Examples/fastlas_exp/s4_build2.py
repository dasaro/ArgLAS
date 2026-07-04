#!/usr/bin/env python3
"""Strategy 4 variant 2: observe `violated` DIRECTLY (no NAF frame in the learning target).

grounded labelling  => violated must NOT hold  => #pos(..., {}, {violated}, ctx)
Hamming-1 neighbour => violated MUST hold       => #pos(..., {violated}, {}, ctx)

This keeps the target predicate `violated` observed directly, avoiding the `legal :- not violated`
negation frame that OPL's possibility evaluation trips over.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s4_verify as V
from s4_build import _ctx, modes, BIAS


def build(maxv=1, neg_feats=True, use_neg_examples=False):
    lines = [V.FEATURES, "", modes(neg_feats), "", BIAS, f"#maxv({maxv}).", ""]
    pi = 0
    for c in V.cells():
        args, attacks = c["args"], c["attacks"]
        g = V.full_grounded(args, attacks)
        # grounded: violated is FALSE -> exclude it
        lines.append(f"#pos(g{pi}, {{}}, {{violated}}, {{{_ctx(args, attacks, g)}}}).")
        pi += 1
        for nb in V.shell3(g):
            # neighbour: violated is TRUE -> include it
            lines.append(f"#pos(b{pi}, {{violated}}, {{}}, {{{_ctx(args, attacks, nb)}}}).")
            pi += 1
    return "\n".join(lines) + "\n", pi


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="s4_task2.las")
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--no-neg-feats", action="store_true")
    a = ap.parse_args()
    text, n = build(maxv=a.maxv, neg_feats=not a.no_neg_feats)
    with open(a.out, "w") as f:
        f.write(text)
    print(f"wrote {a.out}: {n} examples, maxv={a.maxv}, neg_feats={not a.no_neg_feats}")
