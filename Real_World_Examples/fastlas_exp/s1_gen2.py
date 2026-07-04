#!/usr/bin/env python3
"""Strategy 1 (round 2): the flip-only choice task learns ONLY out-rules because `in` is
guessed for free by the `in` choice rule. Fix: make `in` NON-guessable so a positive with
in(c) can only be covered by a LEARNED in-rule. Test asymmetric-choice variants, all with
flip-only negatives (drops trigger the uncoverable disj(0) possibility -> UNSAT)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F

HERE = os.path.dirname(os.path.abspath(__file__))
cells = F.grounded_cells("D", "grounded")
negs_all = F.shell_negs(cells)

# recompute flip-only / drop-only split (same logic as s1_gen)
def split(cells, negs):
    flip, drop = [], []
    for c in cells:
        src = c["commit"]
        for neg in negs:
            if neg["attacks"] != c["attacks"]:
                continue
            if set(neg["commit"].keys()) == set(src.keys()):
                if sum(1 for k in src if src[k] != neg["commit"].get(k)) == 1:
                    flip.append(neg)
            elif set(neg["commit"].keys()) < set(src.keys()) and len(neg["commit"]) == len(src) - 1:
                if all(neg["commit"][k] == src[k] for k in neg["commit"]):
                    drop.append(neg)
    def dd(ns):
        seen, out = set(), []
        for n in ns:
            k = (tuple(sorted(n["attacks"])), tuple(sorted(n["commit"].items())))
            if k not in seen:
                seen.add(k); out.append(n)
        return out
    return dd(flip), dd(drop)

flip_negs, drop_negs = split(cells, negs_all)
print(f"cells={len(cells)} flip={len(flip_negs)} drop={len(drop_negs)}")

# Background variants with asymmetric choice
BG_DERIVED = F._DERIVED  # defeat/defeated/not_defended/not_supported/supported + cf constraint
CH_IN = "0 { in(X) } 1 :- arg(X)."
CH_OUT = "0 { out(X) } 1 :- arg(X)."


def modes(constraints=False, heads=("in", "out")):
    mh = [f"#modeh({h}(var(arg)))." for h in heads]
    if constraints:
        mh.append("#modeh(false).")
    mb = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).",
          "#modeb(att(var(arg), var(arg))).",
          "#modeb(defeated(var(arg))).", "#modeb(not_defended(var(arg))).",
          "#modeb(supported(var(arg)))."]
    return "\n".join(mh + mb)


def build(choice="", constraints=False, guard=False, negs=None, maxv=2, heads=("in", "out"),
          pos_weight=None, neg_weight=None):
    bg = BG_DERIVED
    if choice:
        bg += "\n" + choice
    if constraints and guard:
        bg += "\n:- false."
    lines = [bg, "", modes(constraints, heads), "", F.BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(F.render_example("pos", f"p{i}", pos_weight, c["args"], c["attacks"], c["commit"]))
    for j, c in enumerate(negs or []):
        lines.append(F.render_example("neg", f"n{j}", neg_weight, c["args"], c["attacks"], c["commit"]))
    return "\n".join(lines) + "\n"


def write(name, text):
    with open(os.path.join(HERE, name), "w") as f:
        f.write(text)
    print("wrote", name)


if __name__ == "__main__":
    # G: choice on OUT only, no constraints, flip negs -> force learned in-rule
    write("s1_G_chOUT_flip.las", build(choice=CH_OUT, negs=flip_negs))
    # H: choice on IN only, flip negs -> force learned out-rule (symmetric)
    write("s1_H_chIN_flip.las", build(choice=CH_IN, negs=flip_negs))
    # I: NO choice (det), both heads learned, flip negs only
    write("s1_I_det_flip.las", build(choice="", negs=flip_negs))
    # J: NO choice, both heads learned, ALL negs (flip+drop) -> does det avoid disj(0)?
    write("s1_J_det_allnegs.las", build(choice="", negs=negs_all))
    # K: choice on OUT only, flip negs, no in-choice, constraints+guard (belt & braces)
    write("s1_K_chOUT_c_guard_flip.las", build(choice=CH_OUT, constraints=True, guard=True, negs=flip_negs))
    # L: choice on OUT only, ALL negs (flip+drop) -> do drops still break w/o in-choice?
    write("s1_L_chOUT_allnegs.las", build(choice=CH_OUT, negs=negs_all))
