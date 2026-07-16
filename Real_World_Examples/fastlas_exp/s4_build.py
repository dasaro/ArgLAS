#!/usr/bin/env python3
"""Strategy 4: build a FastLAS OPL VERIFIER task.

Learn a target-INDEPENDENT `violated` predicate over a GIVEN 3-valued labelling. Frame
`legal :- not violated.` sits in the background. Positives: grounded labelling => legal.
Negatives: each Hamming-1 3-valued neighbour => NOT legal (so `violated` must fire there).

Because in/out/undec are CONTEXT facts (not the learned target), the derived features
defended/attacked_by_in ARE available in candidate bodies => OPL space does not collapse.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s4_verify as V

FEATURES = V.FEATURES
FRAME = V.FRAME


def _ctx(args, attacks, lab):
    facts = ([f"arg({a})." for a in args] +
             [f"att({s},{t})." for s, t in attacks] +
             [f"{s}({a})." for a, s in lab.items()])
    return " ".join(facts)


def modes(neg_feats=True):
    mh = ["#modeh(violated)."]
    mb = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).", "#modeb(undec(var(arg))).",
          "#modeb(defended(var(arg))).", "#modeb(attacked_by_in(var(arg))).",
          "#modeb(attacked(var(arg))).", "#modeb(att(var(arg), var(arg)))."]
    if neg_feats:
        mb += ["#modeb(not defended(var(arg))).", "#modeb(not attacked_by_in(var(arg))).",
               "#modeb(not attacked(var(arg))).", "#modeb(not in(var(arg))).",
               "#modeb(not out(var(arg))).", "#modeb(not undec(var(arg)))."]
    return "\n".join(mh + mb)


BIAS = ('#bias("penalty(1, head) :- in_head(X).").\n'
        '#bias("penalty(1, body(X)) :- in_body(X).").')


def build(maxv=1, neg_feats=True, pos_weight=None, neg_weight=None):
    lines = [FEATURES, FRAME, "", modes(neg_feats), "", BIAS, f"#maxv({maxv}).", ""]
    pi = 0
    ni = 0
    for c in V.cells():
        args, attacks = c["args"], c["attacks"]
        g = V.full_grounded(args, attacks)
        # positive: grounded labelling is legal
        pid = f"p{pi}@{pos_weight}" if pos_weight else f"p{pi}"
        lines.append(f"#pos({pid}, {{legal}}, {{}}, {{{_ctx(args, attacks, g)}}}).")
        pi += 1
        # negatives: every Hamming-1 3-valued neighbour is NOT legal
        for nb in V.shell3(g):
            nid = f"n{ni}@{neg_weight}" if neg_weight else f"n{ni}"
            lines.append(f"#neg({nid}, {{legal}}, {{}}, {{{_ctx(args, attacks, nb)}}}).")
            ni += 1
    return "\n".join(lines) + "\n", pi, ni


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="s4_task.las")
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--no-neg-feats", action="store_true")
    ap.add_argument("--pos-weight", type=int, default=None)
    ap.add_argument("--neg-weight", type=int, default=None)
    a = ap.parse_args()
    text, npos, nneg = build(maxv=a.maxv, neg_feats=not a.no_neg_feats,
                             pos_weight=a.pos_weight, neg_weight=a.neg_weight)
    with open(a.out, "w") as f:
        f.write(text)
    print(f"wrote {a.out}: {npos} pos, {nneg} neg, maxv={a.maxv}, neg_feats={not a.no_neg_feats}")
