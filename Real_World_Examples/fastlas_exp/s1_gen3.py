#!/usr/bin/env python3
"""Strategy 1 (round 3): the choice+flip formulation can learn `out(X):-att(Y,X),in(Y)` but
NOT `in(X):-supported(X)`, because `supported` is a negation-as-failure feature over attackers
that FastLAS drops from candidate bodies (README's core limitation, pinned to the `in` head).

FIX: pre-compute supported/defeated/not_defended per example FROM THAT EXAMPLE'S OWN LABELLING
and inject them as CONTEXT FACTS. Then FastLAS sees them as EDB (facts, not target-dependent
IDB), so `in(X):-supported(X)` and `out(X):-defeated(X)` become learnable directly.

We DERIVE these features in the per-example context using the labelling that the example fixes.
For a #pos with commit {a:in, b:out, ...}: in/out are known, so supported/defeated are well
defined and we compute them with clingo, then emit them as ground context facts.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl_build as F
import clingo

HERE = os.path.dirname(os.path.abspath(__file__))
cells = F.grounded_cells("D", "grounded")
negs_all = F.shell_negs(cells)


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

# ---- compute derived structural features from a FIXED labelling (commit) ----
# supported(X): every attacker of X is out.  defeated(X): some in-arg attacks X.
# not_defended(X): X is attacked by some Y that is not defeated.
# We compute these deterministically in python from the commit (undecided args count as
# neither in nor out).

def features(args, attacks, commit):
    lab = {a: commit.get(a) for a in args}  # in/out/None
    ins = {a for a in args if lab[a] == "in"}
    outs = {a for a in args if lab[a] == "out"}
    attackers = {a: [s for (s, t) in attacks if t == a] for a in args}
    defeated = {a for a in args if any(s in ins for s in attackers[a])}
    # supported: all attackers out (vacuously true if no attackers)
    supported = {a for a in args if all(s in outs for s in attackers[a])}
    not_defended = {a for a in args if any(s not in defeated for s in attackers[a])}
    return supported, defeated, not_defended


def render_example_with_feats(kind, eid, args, attacks, commit):
    """Like F.render_example but ADD supported/defeated/not_defended ground facts to context."""
    incl, excl = [], []
    for a in args:
        s = commit.get(a)
        if s == "in":
            incl.append(f"in({a})"); excl.append(f"out({a})")
        elif s == "out":
            incl.append(f"out({a})"); excl.append(f"in({a})")
        else:
            excl.append(f"in({a})"); excl.append(f"out({a})")
    sup, dft, ndf = features(args, attacks, commit)
    ctx_atoms = [f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks]
    ctx_atoms += [f"supported({a})." for a in sorted(sup)]
    ctx_atoms += [f"defeated({a})." for a in sorted(dft)]
    ctx_atoms += [f"not_defended({a})." for a in sorted(ndf)]
    ctx = " ".join(ctx_atoms)
    return f"#{kind}({eid}, {{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx}}})."


# Background: NO derived-predicate rules (features are now context facts) and NO choice for the
# head we want to LEARN. We keep a conflict-freeness constraint. We learn BOTH in and out from
# their structural features. supported/defeated are EDB facts per example.
def modes():
    mh = ["#modeh(in(var(arg))).", "#modeh(out(var(arg)))."]
    mb = ["#modeb(supported(var(arg))).", "#modeb(defeated(var(arg))).",
          "#modeb(not_defended(var(arg))).",
          "#modeb(att(var(arg), var(arg))).",
          "#modeb(in(var(arg))).", "#modeb(out(var(arg)))."]
    return "\n".join(mh + mb)


def build(choice_in=False, choice_out=False, negs=None, maxv=1, cf=True):
    parts = []
    if cf:
        parts.append(":- arg(X), in(X), out(X).")
    if choice_in:
        parts.append("0 { in(X) } 1 :- arg(X).")
    if choice_out:
        parts.append("0 { out(X) } 1 :- arg(X).")
    bg = "\n".join(parts)
    lines = [bg, "", modes(), "", F.BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(render_example_with_feats("pos", f"p{i}", c["args"], c["attacks"], c["commit"]))
    for j, c in enumerate(negs or []):
        lines.append(render_example_with_feats("neg", f"n{j}", c["args"], c["attacks"], c["commit"]))
    return "\n".join(lines) + "\n"


def write(name, text):
    with open(os.path.join(HERE, name), "w") as f:
        f.write(text)
    print("wrote", name)


if __name__ == "__main__":
    # M: features as facts, NO choice at all, flip negs, learn both in and out (maxv 1)
    write("s1_M_feats_det_flip.las", build(negs=flip_negs, maxv=1))
    # N: features as facts, NO choice, ALL negs (flip+drop)
    write("s1_N_feats_det_allnegs.las", build(negs=negs_all, maxv=1))
    # O: features as facts, NO choice, flip negs, maxv 2
    write("s1_O_feats_det_flip_v2.las", build(negs=flip_negs, maxv=2))
    # P: features + choice on BOTH (belt&braces), flip negs
    write("s1_P_feats_chBOTH_flip.las", build(choice_in=True, choice_out=True, negs=flip_negs, maxv=1))
