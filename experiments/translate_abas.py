"""Generate random flat ABA frameworks and translate them to AAF instance files.

Uses the CORRECTED per-root translation validated in
analysis/zlatina_theorems/check_aba_transform.py (the thesis/preprint step-1
program drops arguments whenever fact-derivable roots exist; see
docs/paper_revision_worklist.md item 1.1). Here we use the exhaustive reference
construction (ref_arguments/ref_attacks) directly — for the small ABAs generated
here it is exact and fast, and it equals the validated fixed_step1 output.

Output: <output_dir>/aaf_<n>_<i>.lp files (arg/att facts, one argument per
(root, minimal-support) pair) + a sidecar <output_dir>/aba_source_<n>_<i>.txt
recording the source ABA, so learned-theory audits can trace back to it.
Standalone pre-step for Experiment F2 (docs/gap_experiments_spec.md).
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "zlatina_theorems"))
from check_aba_transform import ref_arguments, ref_attacks  # noqa: E402


def rand_flat_aba(rng, min_atoms=4, max_atoms=7, max_rules=8):
    atoms = [f"s{i}" for i in range(rng.randint(min_atoms, max_atoms))]
    assumptions = set(rng.sample(atoms, rng.randint(2, min(4, len(atoms) - 1))))
    non_assum = [a for a in atoms if a not in assumptions]
    rules = []
    for _ in range(rng.randint(1, max_rules)):
        if not non_assum:
            break
        head = rng.choice(non_assum)  # flat: assumptions never appear in heads
        body = rng.sample(atoms, rng.randint(0, 2))
        rules.append((head, body))
    contraries = {p: rng.choice(atoms) for p in assumptions}
    return atoms, rules, assumptions, contraries


def translate(atoms, rules, assumptions, contraries):
    args_list = sorted(ref_arguments(atoms, rules, assumptions))
    attacks = ref_attacks(args_list, contraries)
    return args_list, attacks


def main(argv=None):
    parser = argparse.ArgumentParser(description="Random flat ABAs -> translated AAF pool.")
    parser.add_argument("M", type=int, help="Number of translated AAFs to produce.")
    parser.add_argument("--output_dir", default="aba_outputs")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--min-args", type=int, default=3, help="Keep AAFs with at least this many arguments.")
    parser.add_argument("--max-args", type=int, default=12, help="Keep AAFs with at most this many arguments.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)
    rng = random.Random(args.seed)
    kept, attempts, seen = 0, 0, set()
    per_n_counter = {}
    while kept < args.M and attempts < args.M * 200:
        attempts += 1
        atoms, rules, assumptions, contraries = rand_flat_aba(rng)
        args_list, attacks = translate(atoms, rules, assumptions, contraries)
        n = len(args_list)
        if not (args.min_args <= n <= args.max_args):
            continue
        signature = (tuple(args_list), tuple(sorted(attacks)))
        if signature in seen:
            continue
        seen.add(signature)
        per_n_counter[n] = per_n_counter.get(n, 0) + 1
        idx = per_n_counter[n]
        aaf_path = os.path.join(args.output_dir, f"aaf_{n}_{idx}.lp")
        with open(aaf_path, "w", encoding="utf-8") as f:
            for i in range(1, n + 1):
                f.write(f"arg({i}).\n")
            for x, y in sorted(attacks):
                f.write(f"att({x},{y}).\n")
        with open(os.path.join(args.output_dir, f"aba_source_{n}_{idx}.txt"), "w", encoding="utf-8") as f:
            f.write(f"atoms: {atoms}\nassumptions: {sorted(assumptions)}\n")
            f.write("rules:\n" + "".join(f"  {h} <- {', '.join(b) if b else 'TRUE'}\n" for h, b in rules))
            f.write(f"contraries: {contraries}\n")
            f.write("arguments (id: root <- minimal support):\n")
            f.write("".join(f"  {i+1}: {r} <- {sorted(s)}\n" for i, (r, s) in enumerate(args_list)))
        kept += 1
        if not args.quiet:
            print(f"[{kept}/{args.M}] |args|={n} |att|={len(attacks)} -> {aaf_path}")
    if kept < args.M:
        raise SystemExit(f"Only produced {kept}/{args.M} AAFs in {attempts} attempts; widen size bounds.")
    if not args.quiet:
        print(f"ABA translation completed ({attempts} sampled).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
