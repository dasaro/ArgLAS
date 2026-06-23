import argparse
import os
import random

import clingo

asp_program_template = """
arg(1..{n}).
{{ att(X,Y) : arg(X), arg(Y), X != Y }} = {s}.
"""

def generate_random_aafs(n, M, output_dir, prefix="", seed=None, quiet=False):
    max_att = n * (n - 1)
    unique_models = set()
    rng = random.Random(seed)

    for i in range(1, M + 1):
        while True:
            selected_model = None
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

            ctl.add("base", [], asp_program_template.format(n=n, s=s))
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
    parser.add_argument("--output_dir", default="aaf_outputs", help="Directory to save AAFs.")
    parser.add_argument("--prefix", default="", help="Prefix for output files.")
    parser.add_argument("--seed", type=int, help="Random seed (optional).")
    parser.add_argument("--quiet", action="store_true", help="Suppress output.")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)

    for n in range(args.Nmin, args.Nmax + 1):
        generate_random_aafs(
            n=n,
            M=args.M,
            output_dir=args.output_dir,
            prefix=args.prefix,
            seed=None if args.seed is None else args.seed + (n - args.Nmin) * 100000,
            quiet=args.quiet
        )

    if not args.quiet:
        print("✅ AAF generation completed!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
