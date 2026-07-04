"""Generate the GRD_full labelled pool for route G2 (workdir only; the repo
pool is untouched).

Per campaign AAF (500, sizes 4-8):
  POS_1 : the grounded labelling as computed by ASPARTIX/grounded.lp on the
          bare AAF (in = grounded ext, out = attacked by it, undec unlabelled).
          FULL labelling (p_partial = 1.0).
  NEG_k : (hard) every complete labelling that is not the grounded one, in the
          SAME 3-valued convention (in(E) + out(attacked-by-E) only -- NOT the
          ASPARTIX complete.lp complement-out convention), capped at 7;
          (fallback) if the AAF has a unique complete extension, 2 seeded
          single-arg corruptions of the grounded labelling (guaranteed != it).

File naming matches the pipeline (aaf_<N>_<i>_GRD_{POS,NEG}_<k>.lp) so
train_test.build_grouped_folds / build_grouped_balanced_test work unchanged.
"""
import os
import random
import sys

sys.path.insert(0, "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude/analysis/grd_prf_lab/g2_weak")
import g2lib as G

SEED = 20260704
MAX_HARD_NEG = 7


def corrupt(labels, arglist, rng):
    """Flip one argument's 3-valued label to a different value."""
    for _ in range(50):
        a = rng.choice(arglist)
        cur = "in" if f"in({a})" in labels else ("out" if f"out({a})" in labels else "undec")
        new = rng.choice([v for v in ("in", "out", "undec") if v != cur])
        lab = set(labels)
        lab.discard(f"in({a})")
        lab.discard(f"out({a})")
        if new != "undec":
            lab.add(f"{new}({a})")
        if lab != labels:
            return lab
    return None


def main():
    rng = random.Random(SEED)
    os.makedirs(G.POOL_DIR, exist_ok=True)
    for f in os.listdir(G.POOL_DIR):
        os.remove(os.path.join(G.POOL_DIR, f))

    n_pos = n_hard = n_rand = 0
    for size, idx, path in G.all_aafs():
        bare = G.read_bare_aaf(path)
        bare_lines = bare.splitlines()
        arglist = G.args_of(bare)

        gt = G.grounded_gt_models(bare)
        assert len(gt) == 1, (size, idx)
        g_lab = frozenset(gt[0])

        comp = [frozenset(m) for m in G.complete_labellings(bare)]
        assert g_lab in comp, (size, idx)

        def write(kind, k, labels):
            name = f"aaf_{size}_{idx}_GRD_{kind}_{k}.lp"
            with open(os.path.join(G.POOL_DIR, name), "w", encoding="utf-8") as fh:
                fh.write("\n".join(bare_lines) + "\n")
                fh.write("\n".join(f"{a}." for a in sorted(labels)) + "\n")

        write("POS", 1, g_lab)
        n_pos += 1

        negs = [m for m in comp if m != g_lab][:MAX_HARD_NEG]
        n_hard += len(negs)
        if not negs:
            for _ in range(2):
                c = corrupt(g_lab, arglist, rng)
                if c is not None and frozenset(c) not in [frozenset(x) for x in negs]:
                    negs.append(frozenset(c))
                    n_rand += 1
        for k, m in enumerate(negs, 1):
            write("NEG", k, m)

    print(f"pool at {G.POOL_DIR}: POS={n_pos} hardNEG={n_hard} randNEG={n_rand}")


if __name__ == "__main__":
    main()
