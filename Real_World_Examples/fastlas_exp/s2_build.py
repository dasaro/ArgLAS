#!/usr/bin/env python3
"""STRATEGY 2 (constraints-only): learn COMPLETE-labelling pruning constraints via #modeh(false).

Formulation:
  - Background: the `det` derived predicates (defeat/defeated/not_defended/supported) so those
    features are available in every context. NO choice rules inside the task (FastLAS evaluates
    each labelling as a fixed context; the choice is conceptual — at DEPLOY time the learned
    constraints sit on top of 0{in}1/0{out}1 in clingo).
  - Examples: for each D graph, enumerate EVERY 3^n in/out/undec labelling. A labelling that is a
    COMPLETE labelling -> #pos with `false` in EXCLUSION (must stay consistent). A labelling that is
    NOT complete -> #pos with `false` in INCLUSION (a learned constraint MUST reject it).
  - modeh = #modeh(false); modeb over in/out/att/supported/defeated/not_defended.
  - Learned `false :- body` constraints reject exactly the non-complete labellings.

Grounded (the paper target) = COMPLETE + minimality; recovered at verify time by adding
`#minimize { in;out }` to the learned constraints (a FIXED background directive, not learned).
"""
import itertools
import fl_build as F

# derived predicates (det variant), shared background so features exist in every context
DERIVED = F.background("det")  # defeat/defeated/not_defended/not_supported/supported + no-both IC


def all_labellings(args):
    """Every assignment of {in,out,undec} to args, as a commit dict (undec = arg absent)."""
    for combo in itertools.product(("in", "out", "u"), repeat=len(args)):
        yield {a: s for a, s in zip(args, combo) if s in ("in", "out")}


def is_complete(args, attacks, commit):
    """True iff `commit` is a COMPLETE labelling of (args,attacks).
    in(X)  <=> every attacker of X is out            (X defended / supported)
    out(X) <=> some attacker of X is in              (X defeated)
    undec  <=> not all-out and not some-in
    """
    lab = {a: commit.get(a, "u") for a in args}
    attackers = {a: [s for (s, t) in attacks if t == a] for a in args}
    for x in args:
        atk = attackers[x]
        all_out = all(lab[y] == "out" for y in atk)     # supported / defended
        some_in = any(lab[y] == "in" for y in atk)       # defeated
        if lab[x] == "in":
            if not all_out:
                return False
        elif lab[x] == "out":
            if not some_in:
                return False
        else:  # undecided: must be justified (not forced in nor out)
            if all_out:      # would be forced in -> not complete (over-abstains)
                return False
            if some_in:      # would be forced out
                return False
    return True


def build(cells, maxv=3, include_derived_modeb=True):
    lines = [DERIVED, ""]
    # modes: learn ONLY constraints
    mh = ["#modeh(false)."]
    mb = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).",
          "#modeb(not in(var(arg))).", "#modeb(not out(var(arg))).",
          "#modeb(att(var(arg), var(arg)))."]
    if include_derived_modeb:
        mb += ["#modeb(supported(var(arg))).", "#modeb(defeated(var(arg))).",
               "#modeb(not_defended(var(arg))).",
               "#modeb(not supported(var(arg))).", "#modeb(not defeated(var(arg)))."]
    lines += mh + mb + ["", f"#maxv({maxv}).", ""]
    lines.append('#bias("penalty(1, head).").')
    lines.append('#bias("penalty(1, body(X)) :- in_body(X).").')
    lines.append("")

    eid = 0
    n_valid = n_invalid = 0
    for c in cells:
        args, attacks = c["args"], c["attacks"]
        base = [f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks]
        for commit in all_labellings(args):
            # KEY: labelling atoms (in/out) go in the CONTEXT as facts; only `false` in
            # inclusion (invalid: must derive false) / exclusion (valid: must not).
            lab = []
            for a in args:
                s = commit.get(a)
                if s == "in":
                    lab.append(f"in({a}).")
                elif s == "out":
                    lab.append(f"out({a}).")
            ctx = " ".join(base + lab)
            if is_complete(args, attacks, commit):
                lines.append(f"#pos(e{eid}, {{}}, {{false}}, {{{ctx}}}).")
                n_valid += 1
            else:
                lines.append(f"#pos(e{eid}, {{false}}, {{}}, {{{ctx}}}).")
                n_invalid += 1
            eid += 1
    return "\n".join(lines) + "\n", n_valid, n_invalid


if __name__ == "__main__":
    import sys
    cells = F.grounded_cells("D", "grounded")
    maxv = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    derived = "noderived" not in sys.argv
    txt, nv, ni = build(cells, maxv=maxv, include_derived_modeb=derived)
    out = sys.argv[1] if len(sys.argv) > 1 else "s2_complete.las"
    open(out, "w").write(txt)
    print(f"wrote {out}: {nv} valid(complete) + {ni} invalid examples, maxv={maxv}, "
          f"derived_modeb={derived}")
