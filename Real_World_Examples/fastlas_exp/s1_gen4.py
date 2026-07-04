#!/usr/bin/env python3
"""Strategy 1 (round 4): probe WHY --opl is UNSAT on the winning feats-as-facts formulation,
and whether any OPL-friendly variant works. Reuses s1_gen3 builders."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1_gen3 as G

HERE = os.path.dirname(os.path.abspath(__file__))


def write(name, text):
    with open(os.path.join(HERE, name), "w") as f:
        f.write(text)
    print("wrote", name)


if __name__ == "__main__":
    # Q: feats-as-facts, NO negatives at all (positives only), no choice, maxv1
    write("s1_Q_feats_posonly.las", G.build(negs=None, maxv=1))
    # R: feats-as-facts, no negs, no cf constraint (pure)
    write("s1_R_feats_posonly_nocf.las", G.build(negs=None, maxv=1, cf=False))
    # S: feats-as-facts, flip negs, no cf constraint
    write("s1_S_feats_flip_nocf.las", G.build(negs=G.flip_negs, maxv=1, cf=False))
