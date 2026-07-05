"""Generate random BAFs: random AAFs (via generate_aafs) + random support facts.

Support pairs are sampled among ordered pairs (X, Y), X != Y, that are NOT attack
pairs (att and support kept disjoint, as in Cayrol & Lagasquie-Schiex-style BAFs).
Support cycles are allowed; the closure rule in the BAF encodings handles them.
Output files keep the pipeline naming convention aaf_<n>_<i>.lp so that the
experiment grid (count_aafs, labelling, k-fold grouping) works unchanged; each
file simply carries support/2 facts in addition to arg/1 and att/2.

Standalone pre-step for Experiment F1 (docs/gap_experiments_spec.md): populate
<artifact_root>/aafs/ before launching a run config with no aaf_generation block.
"""

import argparse
import os
import random
import re

import generate_aafs

ATT_RE = re.compile(r"att\((\d+),(\d+)\)\.")
ARG_RE = re.compile(r"arg\((\d+)\)\.")


def add_support_facts(aaf_path, rng, support_max_factor):
    with open(aaf_path, "r", encoding="utf-8") as f:
        text = f.read()
    args = [int(m) for m in ARG_RE.findall(text)]
    atts = {(int(a), int(b)) for a, b in ATT_RE.findall(text)}
    candidates = [
        (x, y)
        for x in args
        for y in args
        if x != y and (x, y) not in atts
    ]
    n_support = rng.randint(0, min(len(candidates), int(support_max_factor * len(args))))
    chosen = sorted(rng.sample(candidates, n_support))
    with open(aaf_path, "a", encoding="utf-8") as f:
        for x, y in chosen:
            f.write(f"support({x},{y}).\n")
    return n_support


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate random BAFs (AAF + support facts).")
    parser.add_argument("Nmin", type=int)
    parser.add_argument("Nmax", type=int)
    parser.add_argument("M", type=int, help="Number of BAFs per N.")
    parser.add_argument("--output_dir", default="baf_outputs")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--support-max-factor",
        type=float,
        default=1.0,
        help="Support count per BAF is sampled uniformly in [0, factor*n].",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)
    for n in range(args.Nmin, args.Nmax + 1):
        size_seed = args.seed + (n - args.Nmin) * 100000
        generate_aafs.generate_random_aafs(
            n=n,
            M=args.M,
            output_dir=args.output_dir,
            seed=size_seed,
            quiet=True,
        )
        rng = random.Random(size_seed + 7)
        for i in range(1, args.M + 1):
            path = os.path.join(args.output_dir, f"aaf_{n}_{i}.lp")
            n_sup = add_support_facts(path, rng, args.support_max_factor)
            if not args.quiet:
                print(f"BAF n={n} #{i}: +{n_sup} support facts -> {path}")
    if not args.quiet:
        print("BAF generation completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
