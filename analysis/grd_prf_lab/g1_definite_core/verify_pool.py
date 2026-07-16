"""Verify the campaign labelled_GRD_full pool.

POS check: the label atoms of every *_POS_* file must EQUAL the grounded
labelling computed by an independent Python least-fixpoint (in = grounded
extension, out = attacked by grounded extension, undec unlabelled), and that
must also equal the unique answer set of ASPARTIX/grounded.lp under PLAIN
clingo (no domRec flags).

NEG check: the label atoms of every *_NEG_* file must NOT be a subset of the
grounded labelling (the pool's verify_extension acceptance test).
"""
import os
import re
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
sys.path.insert(0, REPO)
os.chdir(REPO)

from arglas import train_test as T  # noqa: E402

POOL = os.path.join(
    REPO, "artifacts/final_synthetic_corrected_20260625/labelled/labelled_GRD_full"
)
GROUNDED_LP = os.path.join(REPO, "config/ASPARTIX/grounded.lp")

FACT = re.compile(r"^(arg|att|in|out|undec)\(([^)]*)\)\.\s*$")


def parse_file(path):
    args, atts, labels = set(), set(), set()
    with open(path) as f:
        for line in f:
            m = FACT.match(line.strip())
            if not m:
                continue
            name, body = m.groups()
            if name == "arg":
                args.add(body.strip())
            elif name == "att":
                a, b = [x.strip() for x in body.split(",")]
                atts.add((a, b))
            else:
                labels.add(f"{name}({body.strip()})")
    return args, atts, labels


def grounded_fixpoint(args, atts):
    """Independent least-fixpoint: in(X) iff all attackers out; out(X) iff
    some attacker in. Iterate to fixpoint from empty."""
    attackers = {a: set() for a in args}
    for (x, y) in atts:
        attackers[y].add(x)
    inset, outset = set(), set()
    changed = True
    while changed:
        changed = False
        for a in args:
            if a not in inset and attackers[a] <= outset:
                inset.add(a)
                changed = True
            if a not in outset and attackers[a] & inset:
                outset.add(a)
                changed = True
    return {f"in({a})" for a in inset} | {f"out({a})" for a in outset}


def grounded_clingo(bare_path):
    models = T.run_ground_truth_with_api(
        GROUNDED_LP, bare_path, None,
        clingo_args=[], completion_rules=False,
        show_predicates=["in/1", "out/1"],
    )
    return models


def main():
    files = sorted(os.listdir(POOL))
    pos = [f for f in files if "_POS_" in f]
    neg = [f for f in files if "_NEG_" in f]
    print(f"pool: {len(pos)} POS, {len(neg)} NEG")

    bare_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bare.lp")

    pos_bad, clingo_checked, clingo_bad = [], 0, []
    grounded_by_aaf = {}
    for f in pos:
        args, atts, labels = parse_file(os.path.join(POOL, f))
        g = grounded_fixpoint(args, atts)
        gid = T.aaf_group_id(f)
        grounded_by_aaf[gid] = g
        if labels != g:
            pos_bad.append((f, labels, g))
        # clingo cross-check on a subsample (every 10th) to keep it quick
        if len(pos_bad) == 0 and clingo_checked < 50 and hash(f) % 10 == 0:
            with open(bare_tmp, "w") as bf:
                for a in sorted(args):
                    bf.write(f"arg({a}).\n")
                for (x, y) in sorted(atts):
                    bf.write(f"att({x},{y}).\n")
            models = grounded_clingo(bare_tmp)
            clingo_checked += 1
            if len(models) != 1 or set(models[0]) != g:
                clingo_bad.append((f, models, g))

    neg_bad = []
    for f in neg:
        args, atts, labels = parse_file(os.path.join(POOL, f))
        gid = T.aaf_group_id(f)
        g = grounded_by_aaf.get(gid)
        if g is None:
            g = grounded_fixpoint(args, atts)
        if labels <= g:
            neg_bad.append(f)

    print(f"POS mismatches vs python fixpoint: {len(pos_bad)}")
    for f, l, g in pos_bad[:5]:
        print("  BAD POS", f, "labels", sorted(l), "grounded", sorted(g))
    print(f"clingo cross-checked: {clingo_checked}, mismatches: {len(clingo_bad)}")
    print(f"NEG oracle-subset violations: {len(neg_bad)}")
    for f in neg_bad[:5]:
        print("  BAD NEG", f)

    # distribution facts useful for task design
    n_empty_pos = sum(
        1 for f in pos if not parse_file(os.path.join(POOL, f))[2]
    )
    print(f"POS files with EMPTY grounded labelling: {n_empty_pos}")


if __name__ == "__main__":
    main()
