import argparse
import os
import random

import clingo

from arglas.artifact_paths import resolve_artifact_path

def generate_random_aafs(n, M, output_dir, prefix="", seed=None, quiet=False,
                         density_preset="v2", allow_self_attacks=False):
    # Backward-compatible defaults (density_preset="v2", allow_self_attacks=False)
    # reproduce the original generator byte-for-byte: same rng call sequence, same
    # max_att and attack template. See docs/gap_experiments_spec.md §4.1.
    neq = "" if allow_self_attacks else ", X != Y"
    max_att = n * n if allow_self_attacks else n * (n - 1)
    unique_models = set()
    rng = random.Random(seed)

    for i in range(1, M + 1):
        while True:
            selected_model = None
            if density_preset == "sparse":
                s = rng.randint(n, min(2 * n, max_att))
            else:  # "v2" — unchanged default
                s = rng.randint(n, max_att)

            def on_model(model):
                nonlocal selected_model
                atoms = sorted(str(atom) + "." for atom in model.symbols(shown=True))
                selected_model = "\n".join(atoms)

            rand_seed = rng.randint(1, 1_000_000) if seed is None else seed + i

            ctl = clingo.Control([
                "--models=1",
                "--rand-freq=1.0",
                "--heuristic=Vsids,92",
                "--shuffle=1,100",
                "--sign-def=rnd",
                f"--seed={rand_seed}"
            ])

            program = f"arg(1..{n}).\n{{ att(X,Y) : arg(X), arg(Y){neq} }} = {s}.\n"
            ctl.add("base", [], program)
            ctl.ground([("base", [])])
            ctl.solve(on_model=on_model)

            if selected_model and selected_model not in unique_models:
                unique_models.add(selected_model)
                break

        filename = os.path.join(output_dir, f"{prefix}aaf_{n}_{i}.lp")
        with open(filename, "w") as f:
            f.write(selected_model + "\n")
        if not quiet:
            print(f"Saved: {filename}")
            print(f"N={n}, S={s}: Generated AAF {i}/{M}.")

def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Generate random AAFs with Clingo.",
        add_help=add_help,
    )
    parser.add_argument("Nmin", type=int, help="Minimum number of arguments.")
    parser.add_argument("Nmax", type=int, help="Maximum number of arguments.")
    parser.add_argument("M", type=int, help="Number of AAFs per N.")
    parser.add_argument("--output_dir", default="aaf_outputs",
                        help="Directory to save AAFs (relative paths resolve under FABIO_ARTIFACTS_ROOT).")
    parser.add_argument("--prefix", default="", help="Prefix for output files.")
    parser.add_argument("--seed", type=int, help="Random seed (optional).")
    parser.add_argument("--quiet", action="store_true", help="Suppress output.")
    parser.add_argument("--density-preset", choices=["v2", "sparse"], default="v2",
                        help="Attack-count regime: 'v2' s~U[n,max]; 'sparse' s~U[n,2n].")
    parser.add_argument("--allow_self_attacks", "--allow-self-attacks",
                        action="store_true", dest="allow_self_attacks",
                        help="Permit att(X,X); widens max attacks to n*n.")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    output_dir = resolve_artifact_path(args.output_dir, "aaf_outputs")
    os.makedirs(output_dir, exist_ok=True)

    for n in range(args.Nmin, args.Nmax + 1):
        generate_random_aafs(
            n=n,
            M=args.M,
            output_dir=output_dir,
            prefix=args.prefix,
            seed=None if args.seed is None else args.seed + (n - args.Nmin) * 100000,
            quiet=args.quiet,
            density_preset=args.density_preset,
            allow_self_attacks=args.allow_self_attacks,
        )

    if not args.quiet:
        print("✅ AAF generation completed!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
