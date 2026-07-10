"""Route P1 verification: PRF as (admissible|complete) core + fixed subset-maximal
convention, symmetric with ASPARTIX/preferred.lp.

Checks (against an independent Python brute-force oracle on AAFs of size 4-8):
  A. ASPARTIX preferred.lp + domRec == brute-force preferred (in-sets).
  B. ASPARTIX preferred.lp PLAIN clingo == brute-force COMPLETE (the Exp2 bug demo).
  C. [choice BG + TRUE adm core + completion + #heuristic in + domRec] == preferred.
  D. same with TRUE complete core == preferred.
  E. same as C but WITHOUT completion rules (choice only) -- diagnostic.
  F. same as C but WITHOUT the convention block/args == all admissible (sanity).
"""
import os
import random
import sys
from itertools import combinations

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention")
sys.path.insert(0, REPO)

from arglas import train_test as T  # noqa: E402
from arglas.solver_runtime import solve_models  # noqa: E402

PREFERRED_LP = os.path.join(REPO, "ASPARTIX", "preferred.lp")
BG = os.path.join(REPO, "config/background_knowledge.lp")
BG_CONV = os.path.join(LAB, "bg_learned_prf.lp")
ADM_CORE = os.path.join(LAB, "true_adm_core.lp")
CMP_CORE = os.path.join(LAB, "true_cmp_core.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")


def parse_aaf(path):
    args, atts = set(), set()
    for ln in open(path):
        ln = ln.strip()
        if ln.startswith("arg("):
            args.add(ln[4:-2])
        elif ln.startswith("att("):
            body = ln[4:-2]
            a, b = [t.strip() for t in body.split(",")]
            atts.add((a, b))
    return sorted(args), atts


def brute_admissible(args, atts):
    """All admissible in-sets."""
    attackers = {a: {y for (y, x) in atts if x == a} for a in args}
    out = []
    for r in range(len(args) + 1):
        for S in combinations(args, r):
            S = frozenset(S)
            if any((x, y) in atts for x in S for y in S):
                continue  # not conflict-free
            ok = True
            for x in S:
                for y in attackers[x]:
                    if not any((z, y) in atts for z in S):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                out.append(S)
    return out


def brute_preferred(args, atts):
    adm = brute_admissible(args, atts)
    return {S for S in adm if not any(S < S2 for S2 in adm)}


def brute_complete(args, atts):
    adm = brute_admissible(args, atts)
    attackers = {a: {y for (y, x) in atts if x == a} for a in args}
    comp = set()
    for S in adm:
        defended = {
            x for x in args
            if all(any((z, y) in atts for z in S) for y in attackers[x])
        }
        if defended <= S:
            comp.add(S)
    return comp


def insets(models):
    return {frozenset(a[3:-1] for a in m if a.startswith("in(")) for m in models}


def main():
    rng = random.Random(20260704)
    files = sorted(f for f in os.listdir(AAF_DIR) if f.endswith(".lp"))
    sample = rng.sample(files, 60)
    # hand AAFs exercising undec / odd cycles / mutual attacks
    hand_dir = os.path.join(LAB, "hand_aafs")
    os.makedirs(hand_dir, exist_ok=True)
    hands = {
        "hand_mutual_self.lp": "arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,c).",
        "hand_odd_cycle.lp": "arg(a). arg(b). arg(c). att(a,b). att(b,c). att(c,a).",
        "hand_chain.lp": "arg(a). arg(b). arg(c). att(a,b). att(b,c).",
        "hand_prf_vs_card.lp": (
            "arg(a). arg(b). arg(c). arg(d). arg(e). "
            "att(a,b). att(b,a). att(a,c). att(b,c). att(c,d). att(d,e). att(e,c)."
        ),
        "hand_empty_pref.lp": "arg(a). att(a,a).",
    }
    for name, content in hands.items():
        with open(os.path.join(hand_dir, name), "w") as f:
            f.write(content.replace(". ", ".\n") + "\n")
    paths = [os.path.join(hand_dir, n) for n in hands] + [
        os.path.join(AAF_DIR, f) for f in sample
    ]

    stats = {k: [0, 0] for k in "ABCDEF"}
    plain_differs = 0
    mismatch_examples = []
    for p in paths:
        args, atts = parse_aaf(p)
        pref = brute_preferred(args, atts)
        comp = brute_complete(args, atts)
        adm = {frozenset(s) for s in brute_admissible(args, atts)}

        got_a = insets(solve_models([PREFERRED_LP, p], clingo_args=DOMREC,
                                    show_predicates=["in/1"]))
        got_b = insets(solve_models([PREFERRED_LP, p], clingo_args=[],
                                    show_predicates=["in/1"]))
        got_c = insets(T.run_learned_model_with_api(
            ADM_CORE, p, BG_CONV, clingo_args=DOMREC, completion_rules=True,
            show_predicates=["in/1"]))
        got_d = insets(T.run_learned_model_with_api(
            CMP_CORE, p, BG_CONV, clingo_args=DOMREC, completion_rules=True,
            show_predicates=["in/1"]))
        got_e = insets(T.run_learned_model_with_api(
            ADM_CORE, p, BG_CONV, clingo_args=DOMREC, completion_rules=False,
            show_predicates=["in/1"]))
        got_f = insets(T.run_learned_model_with_api(
            ADM_CORE, p, BG, clingo_args=[], completion_rules=True,
            show_predicates=["in/1"]))

        for key, got, want in [("A", got_a, pref), ("B", got_b, comp),
                               ("C", got_c, pref), ("D", got_d, pref),
                               ("E", got_e, pref), ("F", got_f, adm)]:
            stats[key][1] += 1
            if got == want:
                stats[key][0] += 1
            elif len(mismatch_examples) < 12:
                mismatch_examples.append(
                    (key, os.path.basename(p),
                     sorted(map(sorted, got)), sorted(map(sorted, want))))
        if got_b != pref:
            plain_differs += 1

    for k in "ABCDEF":
        ok, tot = stats[k]
        print(f"check {k}: {ok}/{tot} exact")
    print(f"plain-clingo preferred.lp != preferred on {plain_differs}/{len(paths)} "
          f"AAFs (Exp2-bug visibility)")
    for m in mismatch_examples:
        print("MISMATCH", m)


if __name__ == "__main__":
    main()
