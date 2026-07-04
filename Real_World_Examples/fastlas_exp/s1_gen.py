#!/usr/bin/env python3
"""Strategy 1: fix the choice + #modeh(false) + hard-shell #neg formulation that returns UNSAT.
Builds several variants to isolate the UNSAT cause. Uniquely s1_ prefixed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F

HERE = os.path.dirname(os.path.abspath(__file__))

cells = F.grounded_cells("D", "grounded")
negs = F.shell_negs(cells)
print(f"cells={len(cells)} negs={len(negs)}")

# Split negatives by kind: flips vs drops. A flip has same #committed args as its source cell;
# a drop has fewer. We reconstruct by comparing to source commits.
flip_negs, drop_negs = [], []
for c in cells:
    src = c["commit"]
    for neg in negs:
        if neg["attacks"] != c["attacks"]:
            continue
        # is neg a hamming-1 neighbour of THIS src?
        # flip: same keys, exactly one value differs
        if set(neg["commit"].keys()) == set(src.keys()):
            diff = sum(1 for k in src if src[k] != neg["commit"].get(k))
            if diff == 1:
                flip_negs.append(neg)
        elif set(neg["commit"].keys()) < set(src.keys()) and len(neg["commit"]) == len(src) - 1:
            # drop: exactly one key removed, rest identical
            if all(neg["commit"][k] == src[k] for k in neg["commit"]):
                drop_negs.append(neg)

# dedup preserving structure
def dedup(ns):
    seen, out = set(), []
    for n in ns:
        key = (tuple(sorted(n["attacks"])), tuple(sorted(n["commit"].items())))
        if key in seen:
            continue
        seen.add(key); out.append(n)
    return out
flip_negs = dedup(flip_negs)
drop_negs = dedup(drop_negs)
print(f"flip_negs={len(flip_negs)} drop_negs={len(drop_negs)}")


def write(name, text):
    p = os.path.join(HERE, name)
    with open(p, "w") as f:
        f.write(text)
    print("wrote", name, len(text.splitlines()), "lines")


def build(variant="choice", enrich=False, maxv=2, negs=None, constraints=False,
          guard=True, pos_weight=None, neg_weight=None):
    """Like F.build_task but with an option to OMIT the ':- false.' guard even when constraints=True."""
    bg = F.background(variant, enrich)
    if constraints and guard:
        bg += "\n:- false."
    lines = [bg, "", F.modes(enrich, constraints), "", F.BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        w = c.get("weight", pos_weight)
        lines.append(F.render_example("pos", f"p{i}", w, c["args"], c["attacks"], c["commit"]))
    for j, c in enumerate(negs or []):
        lines.append(F.render_example("neg", f"n{j}", neg_weight, c["args"], c["attacks"], c["commit"]))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import json
    meta = {"cells": len(cells), "negs": len(negs),
            "flip_negs": len(flip_negs), "drop_negs": len(drop_negs)}
    # A: choice, NO constraints, all negs  (baseline: does choice-only + negs go UNSAT or empty?)
    write("s1_A_choice_negs_noconstr.las", build("choice", negs=negs, constraints=False))
    # B: choice + constraints + guard + all negs (== original)
    write("s1_B_choice_c_guard_negs.las", build("choice", negs=negs, constraints=True, guard=True))
    # C: choice + constraints + NO guard + all negs
    write("s1_C_choice_c_noguard_negs.las", build("choice", negs=negs, constraints=True, guard=False))
    # D: choice + constraints + guard + FLIP negs only
    write("s1_D_choice_c_guard_flip.las", build("choice", negs=flip_negs, constraints=True, guard=True))
    # E: choice + constraints + guard + DROP negs only
    write("s1_E_choice_c_guard_drop.las", build("choice", negs=drop_negs, constraints=True, guard=True))
    # F: choice + constraints + NO guard + FLIP negs only
    write("s1_F_choice_c_noguard_flip.las", build("choice", negs=flip_negs, constraints=True, guard=False))
    print(json.dumps(meta))
