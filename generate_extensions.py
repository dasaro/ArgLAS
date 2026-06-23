import argparse
import os
import random
import re

import clingo
from artifact_paths import resolve_artifact_path, resolve_repo_path
from solver_runtime import build_semantics_runtime, solve_semantics_instance
from solver_policy import (
    get_semantics_entry,
    get_semantics_names,
    load_semantics_config,
)

def extract_arguments_attacks(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    arguments = [line.strip() for line in lines if line.startswith("arg(")]
    attacks = [line.strip() for line in lines if line.startswith("att(")]
    return arguments, attacks

def run_clingo(input_file, runtime):
    models = solve_semantics_instance(runtime, input_file)
    return [
        [clingo.parse_term(atom) for atom in sorted(model)]
        for model in models
    ]

def normalize_extension_atoms(extension_atoms):
    normalized = set()
    for atom in extension_atoms:
        fact = atom.strip()
        if not fact:
            continue
        if not fact.endswith("."):
            fact = f"{fact}."
        normalized.add(fact)
    return normalized

def model_to_fact_set(model_symbols):
    facts = set()
    for atom in model_symbols:
        if atom.name in {"in", "out", "undec"}:
            facts.add(f"{atom}.")
    return facts

def verify_extension(
    input_file,
    runtime,
    extension_atoms,
    precomputed_models=None,
):
    target_facts = normalize_extension_atoms(extension_atoms)
    models = (
        precomputed_models
        if precomputed_models is not None
        else run_clingo(
            input_file,
            runtime,
        )
    )
    for model in models:
        model_facts = model_to_fact_set(model)
        if target_facts.issubset(model_facts):
            return True
    return False

def generate_negative_examples(
    input_file,
    runtime,
    arguments,
    p_partial,
    attempts=5,
    precomputed_models=None,
):
    invalid = []
    arg_list = [arg.split("(")[1].rstrip(").") for arg in arguments]

    for _ in range(attempts):
        chosen = random.sample(arg_list, random.randint(1, len(arg_list)))
        ext = [f"in({arg})." for arg in chosen if random.random() < p_partial] + \
              [f"out({arg})." for arg in arg_list if arg not in chosen and random.random() < p_partial]

        if not verify_extension(
            input_file,
            runtime,
            ext,
            precomputed_models=precomputed_models,
        ):
            invalid.append(ext)
    return invalid

def generate_labelled_aafs(
    input_dir,
    output_dir,
    semantics,
    runtime,
    p_partial,
    generate_empty_extensions,
):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if not filename.endswith(".lp"):
            continue

        match = re.match(r"aaf_(\d+)_(\d+)\.lp", filename)
        if not match:
            continue

        size, id_ = match.groups()
        input_path = os.path.join(input_dir, filename)
        args, atts = extract_arguments_attacks(input_path)

        models = run_clingo(
            input_path,
            runtime,
        )
        pos_count = 0

        for model in models:
            if not model and not generate_empty_extensions:
                continue

            ext_atoms = [f"{atom}." for atom in model if random.random() < p_partial]
            if verify_extension(
                input_path,
                runtime,
                ext_atoms,
                precomputed_models=models,
            ):
                output_file = f"aaf_{size}_{id_}_{semantics}_POS_{pos_count + 1}.lp"
                with open(os.path.join(output_dir, output_file), "w") as f:
                    f.write("\n".join(args + atts + ext_atoms) + "\n")
                print(f"[POS] {output_file}")
                pos_count += 1

        neg_extensions = generate_negative_examples(
            input_path,
            runtime,
            args,
            p_partial,
            precomputed_models=models,
        )
        for i, neg in enumerate(neg_extensions):
            output_file = f"aaf_{size}_{id_}_{semantics}_NEG_{i + 1}.lp"
            with open(os.path.join(output_dir, output_file), "w") as f:
                f.write("\n".join(args + atts + neg) + "\n")
            print(f"[NEG] {output_file}")

def construct_output_dir(base_dir, semantics, p_partial):
    if p_partial < 1.0:
        suffix = f"partial_{p_partial}"
    else:
        suffix = "full"
    return os.path.join(base_dir, f"labelled_{semantics}_{suffix}")

def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Label AAFs with positive/negative extensions.",
        add_help=add_help,
    )
    parser.add_argument("--input_dir", default="aafs/", help="Directory with raw AAFs.")
    parser.add_argument("--base_output_dir", default="labelled/", help="Base output directory.")
    parser.add_argument("--semantics", default="ADM", help="AAF semantics.")
    parser.add_argument(
        "--semantics_config",
        default="semantics_config.json",
        help="Path to semantics config JSON.",
    )
    parser.add_argument("--p_partial", type=float, default=0.3, help="Probability to include atoms in partial ext.")
    parser.add_argument("--allow_empty", action="store_true", help="Include empty extensions.")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic RNG seed for partial sampling and synthetic negative generation.",
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.seed is not None:
        random.seed(args.seed)

    semantics_config_path = resolve_repo_path(args.semantics_config, "semantics_config.json")
    semantics_config = load_semantics_config(semantics_config_path)
    semantics_names = get_semantics_names(semantics_config)
    if args.semantics not in semantics_names:
        raise ValueError(
            f"Unknown semantics: {args.semantics}. Available: {', '.join(semantics_names)}"
        )

    input_dir = resolve_artifact_path(args.input_dir, "aafs")
    output_dir = construct_output_dir(
        resolve_artifact_path(args.base_output_dir, "labelled"),
        args.semantics,
        args.p_partial,
    )

    get_semantics_entry(semantics_config, args.semantics)
    runtime = build_semantics_runtime(
        semantics_config,
        args.semantics,
        stage="label_generation",
    )
    generate_labelled_aafs(
        input_dir=input_dir,
        output_dir=output_dir,
        semantics=args.semantics,
        runtime=runtime,
        p_partial=args.p_partial,
        generate_empty_extensions=args.allow_empty,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
