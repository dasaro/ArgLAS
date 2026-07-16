#!/usr/bin/env python3
"""STRATEGY 2 gadget encoding: force GENERAL complete-labelling constraints with minimal,
atomic violation examples (one violated constraint per invalid example), sudoku-style.

Each example is (args, attacks, commit, valid?). valid -> #pos with false EXCLUDED;
invalid -> #pos with false INCLUDED. Small contexts keep the learned rule general.
"""
import fl_build as F

DERIVED = F.background("det")


def render(eid, args, attacks, commit, valid):
    # labelling atoms (in/out) go in the CONTEXT as facts; only `false` in inclusion/exclusion.
    # valid -> false in EXCLUSION (must not fire); invalid -> false in INCLUSION (must fire).
    lab = []
    for a in args:
        s = commit.get(a)
        if s == "in":
            lab.append(f"in({a}).")
        elif s == "out":
            lab.append(f"out({a}).")
    ctx = " ".join([f"arg({a})." for a in args] +
                   [f"att({s},{t})." for s, t in attacks] + lab)
    incl = "false" if not valid else ""
    excl = "false" if valid else ""
    return f"#pos({eid}, {{{incl}}}, {{{excl}}}, {{{ctx}}})."


# --- gadget examples ------------------------------------------------------------
# Each: (args, attacks, commit, valid)
GADGETS = [
    # ---- VALID reference labellings (must NOT fire false) ----
    # single attack a->b: grounded a in, b out, c(free) in
    (["a", "b", "c"], [("a", "b")], {"a": "in", "b": "out", "c": "in"}, True),
    # 2-cycle a<->b + free c: grounded c in, a,b undecided
    (["a", "b", "c"], [("a", "b"), ("b", "a")], {"c": "in"}, True),
    # chain c->b->a : c in, b out, a in
    (["a", "b", "c"], [("b", "a"), ("c", "b")], {"a": "in", "b": "out", "c": "in"}, True),
    # lone arg accepted
    (["a"], [], {"a": "in"}, True),
    # attacked-by-out is in: b out (attacked by in a), a in
    (["a", "b"], [("a", "b")], {"a": "in", "b": "out"}, True),

    # ---- INVALID: violate C1  false :- in(X), not supported(X) ----
    # x in but attacker y undecided
    (["x", "y"], [("y", "x")], {"x": "in"}, False),
    # x in, attacker y in (y not out) -> x not supported
    (["x", "y"], [("y", "x")], {"x": "in", "y": "in"}, False),

    # ---- INVALID: violate C2  false :- supported(X), not in(X) ----
    # x unattacked (supported) but undecided
    (["x"], [], {}, False),
    # x's only attacker y is out (x supported) but x undecided
    (["x", "y"], [("y", "x")], {"y": "out"}, False),

    # ---- INVALID: violate C3  false :- out(X), not defeated(X) ----
    # x out but unattacked (not defeated)
    (["x"], [], {"x": "out"}, False),
    # x out, attacker y is out (no in-attacker) -> x not defeated
    (["x", "y"], [("y", "x")], {"x": "out", "y": "out"}, False),

    # ---- INVALID: violate C4  false :- defeated(X), not out(X) ----
    # x's attacker y is in (x defeated) but x undecided
    (["x", "y"], [("y", "x")], {"y": "in"}, False),
    # x defeated (y in) but x labelled in
    (["x", "y"], [("y", "x")], {"x": "in", "y": "in"}, False),  # also C1; still must fire
]


def build(maxv=2, gadgets=GADGETS):
    lines = [DERIVED, ""]
    mh = ["#modeh(false)."]
    mb = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).",
          "#modeb(not in(var(arg))).", "#modeb(not out(var(arg))).",
          "#modeb(supported(var(arg))).", "#modeb(defeated(var(arg))).",
          "#modeb(not supported(var(arg))).", "#modeb(not defeated(var(arg)))."]
    lines += mh + mb + ["", f"#maxv({maxv}).", ""]
    lines.append('#bias("penalty(1, head).").')
    lines.append('#bias("penalty(1, body(X)) :- in_body(X).").')
    lines.append("")
    nv = ni = 0
    for i, (args, attacks, commit, valid) in enumerate(gadgets):
        lines.append(render(f"g{i}", args, attacks, commit, valid))
        if valid:
            nv += 1
        else:
            ni += 1
    return "\n".join(lines) + "\n", nv, ni


if __name__ == "__main__":
    import sys
    maxv = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    txt, nv, ni = build(maxv=maxv)
    out = sys.argv[1] if len(sys.argv) > 1 else "s2_gadgets.las"
    open(out, "w").write(txt)
    print(f"wrote {out}: {nv} valid + {ni} invalid gadgets, maxv={maxv}")
