import argparse
import os
import random
import re
from collections import defaultdict
from arglas.artifact_paths import ensure_parent_dir, resolve_artifact_path, resolve_repo_path
from arglas.solver_runtime import build_semantics_runtime, solve_models
from arglas.solver_policy import (
    load_semantics_config,
)

STATUSES = ("in", "out", "undec")
LABEL_RE = re.compile(r"^(in|out|undec)\(([^)]+)\)\.$")


def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Generate an ILASP learning task from argumentation extensions.",
        add_help=add_help,
    )
    parser.add_argument(
        "input_dir",
        default="aaf_extensions",
        type=str,
        help="Directory containing labelled AAF examples.",
    )
    parser.add_argument(
        "output_file",
        default="ilasp_task.las",
        type=str,
        help="Path to save the ILASP learning task.",
    )
    parser.add_argument("n_pos", type=int, default=50, help="Number of positive examples to sample.")
    parser.add_argument(
        "p",
        type=float,
        default=0.0,
        help="Probability of inverting example polarity (p=0 is deterministic).",
    )
    parser.add_argument(
        "--n_neg",
        type=int,
        help="Number of negative examples to sample/generate (default: same as n_pos).",
    )
    parser.add_argument("--noise_factor", default=100, type=int, help="Penalty for noisy examples.")
    parser.add_argument(
        "--negative_policy",
        choices=(
            "oracle_neg", "flip_one", "flip_k", "full_relabel", "rn_hardmix",
            "nce_sample", "reliable_negative",
        ),
        default="oracle_neg",
        help=(
            "Negative generation strategy: "
            "oracle_neg samples existing *_NEG_* files; "
            "flip_one flips one in/out label from sampled positives; "
            "flip_k flips k in/out labels from sampled positives; "
            "full_relabel relabels all observed labels from sampled positives; "
            "rn_hardmix mines candidate synthetic negatives, taking a reliable subset "
            "and filling with harder near-positive negatives; "
            "nce_sample relabels each arg independently from the global accept "
            "marginal (noise-contrastive); "
            "reliable_negative keeps the relabelling farthest from the source positive "
            "(PU density-based)."
        ),
    )
    parser.add_argument(
        "--flip_k",
        type=int,
        default=1,
        help="Number of in/out labels to flip when --negative_policy=flip_k.",
    )
    parser.add_argument(
        "--rn_reliable_fraction",
        type=float,
        default=0.7,
        help=(
            "Fraction of negatives selected from the most reliable rn_hardmix candidates "
            "(remaining slots are filled with hard negatives)."
        ),
    )
    parser.add_argument(
        "--rn_candidates_per_source",
        type=int,
        default=3,
        help="How many rn_hardmix mutation candidates to generate per source positive example.",
    )
    parser.add_argument(
        "--allow_overwrite",
        action="store_true",
        help="Allow overwriting output_file if it already exists (default: disabled).",
    )
    parser.add_argument(
        "--semantics",
        help=(
            "Semantics name (e.g., ADM/CMP/STB/GRD/PRF). "
            "If omitted, inferred from input_dir or example filenames."
        ),
    )
    parser.add_argument(
        "--semantics_config",
        default="semantics_config.json",
        help="Path to semantics config JSON (default: semantics_config.json).",
    )
    parser.add_argument(
        "--allowed_examples_manifest",
        default=None,
        help=(
            "Optional text file listing the example filenames that task generation is allowed "
            "to sample from. One filename per line."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic RNG seed for example sampling and task construction.",
    )
    parser.add_argument(
        "--learn_background",
        default=None,
        help=(
            "Optional background file to embed in the LEARNING task instead of "
            "background_knowledge.lp. Needed for GRD, whose task must NOT contain the "
            "0{in}1/0{out}1 choice rules (with them the grounded task is unsatisfiable: "
            "every labelling is an answer set and minimality is not first-order expressible)."
        ),
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def parse_lp_instance(path):
    af_facts = []
    labels = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            fact = raw.strip()
            if not fact:
                continue
            match = LABEL_RE.match(fact)
            if match:
                labels[match.group(2)] = match.group(1)
            else:
                af_facts.append(fact)
    return af_facts, labels


def render_label_facts(labels):
    status_order = {status: idx for idx, status in enumerate(STATUSES)}
    ordered = sorted(labels.items(), key=lambda item: (status_order.get(item[1], 99), item[0]))
    return [f"{status}({arg})" for arg, status in ordered]


def build_synthetic_negative(labels, policy, flip_k=1, p_in=0.5, n_candidates=8):
    mutated = dict(labels)
    if policy in {"flip_one", "flip_k"}:
        required_k = 1 if policy == "flip_one" else int(flip_k)
        if required_k <= 0:
            return None
        flippable = [arg for arg, status in mutated.items() if status in {"in", "out"}]
        if len(flippable) < required_k:
            return None
        chosen_args = random.sample(flippable, required_k)
        for chosen in chosen_args:
            mutated[chosen] = "out" if mutated[chosen] == "in" else "in"
        return mutated

    if policy == "full_relabel":
        if not mutated:
            return None
        for arg, current in list(mutated.items()):
            alternatives = [status for status in STATUSES if status != current]
            mutated[arg] = random.choice(alternatives)
        return mutated

    if policy == "nce_sample":
        # Noise-contrastive (word2vec-style): relabel each argument INDEPENDENTLY
        # from the global accept marginal p_in, deliberately breaking the joint
        # structure of real extensions so the result is unlikely to be a valid
        # labelling. Oracle-free.
        if not mutated:
            return None
        for arg in mutated:
            mutated[arg] = "in" if random.random() < p_in else "out"
        return mutated

    if policy == "reliable_negative":
        # PU reliable-negative (density-based): among several random relabellings,
        # keep the one FARTHEST (Hamming) from the source positive -> a low-density,
        # high-confidence negative. Oracle-free. (Far-from-source is a per-example
        # proxy for far-from-all-positives.)
        if not mutated:
            return None
        best, best_dist = None, -1
        for _ in range(max(1, int(n_candidates))):
            cand = {arg: ("in" if random.random() < 0.5 else "out") for arg in mutated}
            dist = sum(1 for arg in mutated if cand[arg] != labels.get(arg))
            if dist > best_dist:
                best_dist, best = dist, cand
        return best

    raise ValueError(f"Unsupported policy: {policy}")


def count_flippable(labels):
    return sum(1 for status in labels.values() if status in {"in", "out"})


def labels_signature(labels):
    return tuple(sorted(labels.items()))


def choose_synthetic_sources(pos_examples, selected_pos, n_neg):
    preferred = [x for x in pos_examples if x not in selected_pos]
    chosen = []

    if len(preferred) >= n_neg:
        return random.sample(preferred, n_neg)

    chosen.extend(preferred)
    remaining = n_neg - len(chosen)

    remaining_pool = [x for x in pos_examples if x not in chosen]
    if remaining_pool:
        if remaining <= len(remaining_pool):
            chosen.extend(random.sample(remaining_pool, remaining))
            return chosen
        chosen.extend(remaining_pool)
        remaining = n_neg - len(chosen)

    if not pos_examples:
        return chosen

    chosen.extend(random.choice(pos_examples) for _ in range(remaining))
    return chosen


def infer_semantics_name(explicit_semantics, input_dir, pos_examples, neg_examples):
    if explicit_semantics:
        return explicit_semantics

    base_dir = os.path.basename(os.path.normpath(input_dir))
    match = re.match(r"^labelled_([A-Za-z0-9]+)_(?:full|partial_.*)$", base_dir)
    if match:
        return match.group(1)

    sample_names = []
    if pos_examples:
        sample_names.append(pos_examples[0])
    if neg_examples:
        sample_names.append(neg_examples[0])

    for name in sample_names:
        match = re.search(r"_([A-Za-z0-9]+)_(?:POS|NEG)_", name)
        if match:
            return match.group(1)

    raise ValueError(
        "Could not infer semantics from input directory/files. "
        "Pass --semantics explicitly."
    )


def make_oracle_consistency_checker(
    semantics,
    semantics_config_path,
    parsed_example_loader,
):
    semantics_config = load_semantics_config(
        resolve_repo_path(semantics_config_path, "semantics_config.json")
    )
    runtime = build_semantics_runtime(
        semantics_config,
        semantics,
        stage="train_test_ground_truth",
    )
    af_models_cache = {}

    def get_models_for_af(af_facts):
        signature = tuple(sorted(af_facts))
        if signature in af_models_cache:
            return af_models_cache[signature]
        models = solve_models(
            files_to_load=[runtime.background_file, runtime.semantics_file],
            clingo_args=list(runtime.clingo_args),
            completion_rules=runtime.completion_rules,
            additional_program="\n".join(af_facts) if af_facts else None,
            show_predicates=list(runtime.show_predicates),
        )
        af_models_cache[signature] = models
        return models

    def interpretation_is_legal(example_filename):
        af_facts, labels = parsed_example_loader(example_filename)
        label_atoms = set(render_label_facts(labels))
        models = get_models_for_af(af_facts)
        for model_atoms in models:
            if label_atoms.issubset(model_atoms):
                return True
        return False

    return interpretation_is_legal


def build_ilasp_directive(example_id, label_facts, af_facts, is_positive, p, deterministic, noise_factor):
    noisy = False
    if random.random() >= p:
        example_type = "#pos" if is_positive else "#neg"
    else:
        example_type = "#neg" if is_positive else "#pos"
        noisy = True

    noisy_flag = "F" if noisy else "T"
    labels_str = ", ".join(label_facts)
    af_str = " ".join(af_facts)

    if deterministic:
        text = f"{example_type}({example_id}{noisy_flag}, {{{labels_str}}}, {{}}, {{{af_str}}})."
    else:
        text = f"{example_type}({example_id}{noisy_flag}@{noise_factor}, {{{labels_str}}}, {{}}, {{{af_str}}})."
    return text, noisy


def main(argv=None):
    args = parse_args(argv)
    if args.seed is not None:
        random.seed(args.seed)

    input_dir = resolve_artifact_path(args.input_dir)
    output_file = ensure_parent_dir(resolve_artifact_path(args.output_file))
    n_pos = args.n_pos
    n_neg = args.n_neg if args.n_neg is not None else args.n_pos
    p = args.p
    negative_policy = args.negative_policy
    flip_k = args.flip_k
    rn_reliable_fraction = args.rn_reliable_fraction
    rn_candidates_per_source = args.rn_candidates_per_source
    noise_factor = args.noise_factor

    if not (0.0 <= p <= 1.0):
        print(f"Error: p must be in [0,1], got {p}.")
        raise SystemExit(1)
    if flip_k <= 0:
        print(f"Error: flip_k must be > 0, got {flip_k}.")
        raise SystemExit(1)
    if not (0.0 <= rn_reliable_fraction <= 1.0):
        print(f"Error: rn_reliable_fraction must be in [0,1], got {rn_reliable_fraction}.")
        raise SystemExit(1)
    if rn_candidates_per_source <= 0:
        print(f"Error: rn_candidates_per_source must be > 0, got {rn_candidates_per_source}.")
        raise SystemExit(1)

    # Keep oracle_neg deterministic at p=0, but force weighted noisy format for
    # synthetic-negative policies so @noise_factor is always present.
    deterministic = (p == 0 and negative_policy == "oracle_neg")
    noisy_count = 0

    if not os.path.exists(input_dir):
        print(f"Error: Directory {input_dir} does not exist.")
        raise SystemExit(1)

    if os.path.exists(output_file) and not args.allow_overwrite:
        print(
            f"Error: Output file already exists: {output_file}. "
            "Refusing to overwrite. Pick a new output path or pass --allow_overwrite."
        )
        raise SystemExit(1)

    allowed_examples = None
    if args.allowed_examples_manifest:
        manifest_path = resolve_repo_path(args.allowed_examples_manifest)
        if not os.path.exists(manifest_path):
            print(f"Error: allowed_examples_manifest does not exist: {manifest_path}")
            raise SystemExit(1)
        with open(manifest_path, "r", encoding="utf-8") as f:
            allowed_examples = {
                os.path.basename(line.strip())
                for line in f
                if line.strip()
            }
        if not allowed_examples:
            print(f"Error: allowed_examples_manifest is empty: {manifest_path}")
            raise SystemExit(1)

    pos_examples = [f for f in os.listdir(input_dir) if "_POS_" in f and f.endswith(".lp")]
    neg_examples = [f for f in os.listdir(input_dir) if "_NEG_" in f and f.endswith(".lp")]
    if allowed_examples is not None:
        pos_examples = [f for f in pos_examples if f in allowed_examples]
        neg_examples = [f for f in neg_examples if f in allowed_examples]

    if len(pos_examples) < n_pos:
        print(f"Error: Not enough positive examples in {input_dir}. Found {len(pos_examples)}.")
        raise SystemExit(1)

    if negative_policy == "oracle_neg" and len(neg_examples) < n_neg:
        print(f"Error: Not enough negative examples in {input_dir}. Found {len(neg_examples)}.")
        raise SystemExit(1)

    selected_pos = random.sample(pos_examples, n_pos)
    parsed_cache = {}

    def get_parsed(example_filename):
        key = os.path.join(input_dir, example_filename)
        if key not in parsed_cache:
            parsed_cache[key] = parse_lp_instance(key)
        return parsed_cache[key]

    # Global accept marginal P(in) over the sampled positives' labelled in/out
    # arguments -- the noise distribution used by the nce_sample policy.
    _pin_num = _pin_den = 0
    for _pf in selected_pos:
        _, _lbls = get_parsed(_pf)
        for _st in _lbls.values():
            if _st in ("in", "out"):
                _pin_den += 1
                _pin_num += 1 if _st == "in" else 0
    p_in_marginal = (_pin_num / _pin_den) if _pin_den else 0.5

    oracle_interpretation_is_legal = None
    oracle_neg_validity_cache = {}
    oracle_neg_rejected = 0
    if negative_policy == "oracle_neg":
        semantics_name = infer_semantics_name(
            args.semantics, input_dir, pos_examples, neg_examples
        )
        oracle_interpretation_is_legal = make_oracle_consistency_checker(
            semantics=semantics_name,
            semantics_config_path=args.semantics_config,
            parsed_example_loader=get_parsed,
        )

    ilasp_examples = []

    # Positives: always sampled from oracle positive files.
    for pos_file in selected_pos:
        filename_id = os.path.basename(pos_file).replace(".lp", "")
        af_facts, labels = get_parsed(pos_file)
        label_facts = render_label_facts(labels)
        directive, noisy = build_ilasp_directive(
            example_id=filename_id,
            label_facts=label_facts,
            af_facts=af_facts,
            is_positive=True,
            p=p,
            deterministic=deterministic,
            noise_factor=noise_factor,
        )
        if noisy:
            print(f"Example {filename_id} gets inverted.")
            noisy_count += 1
        ilasp_examples.append(directive)

    # Negatives: from oracle files or generated from positive files.
    if n_neg > 0:
        if negative_policy == "oracle_neg":
            shuffled_neg = list(neg_examples)
            random.shuffle(shuffled_neg)
            selected_neg = []

            for neg_file in shuffled_neg:
                cached_validity = oracle_neg_validity_cache.get(neg_file)
                if cached_validity is None:
                    # Oracle negatives must remain negative in the same stack used
                    # during training/evaluation: background + target semantics.
                    cached_validity = not oracle_interpretation_is_legal(neg_file)
                    oracle_neg_validity_cache[neg_file] = cached_validity
                if not cached_validity:
                    oracle_neg_rejected += 1
                    continue
                selected_neg.append(neg_file)
                if len(selected_neg) >= n_neg:
                    break

            if len(selected_neg) < n_neg:
                valid_available = sum(1 for ok in oracle_neg_validity_cache.values() if ok)
                print(
                    "Error: Not enough oracle negatives consistent with training stack. "
                    f"Requested {n_neg}, found {len(selected_neg)} (validated {valid_available})."
                )
                raise SystemExit(1)

            for neg_file in selected_neg:
                filename_id = os.path.basename(neg_file).replace(".lp", "")
                af_facts, labels = get_parsed(neg_file)
                label_facts = render_label_facts(labels)
                directive, noisy = build_ilasp_directive(
                    example_id=filename_id,
                    label_facts=label_facts,
                    af_facts=af_facts,
                    is_positive=False,
                    p=p,
                    deterministic=deterministic,
                    noise_factor=noise_factor,
                )
                if noisy:
                    print(f"Example {filename_id} gets inverted.")
                    noisy_count += 1
                ilasp_examples.append(directive)
        else:
            eligible_pos = pos_examples
            if negative_policy in {"flip_one", "flip_k", "rn_hardmix"}:
                required_k = 1 if negative_policy == "flip_one" else flip_k
                if negative_policy == "rn_hardmix":
                    required_k = 1
                eligible_pos = []
                for fname in pos_examples:
                    _, labels = get_parsed(fname)
                    flippable_count = count_flippable(labels)
                    if flippable_count >= required_k:
                        eligible_pos.append(fname)
                if not eligible_pos:
                    print(
                        f"Error: {negative_policy} requested with k={required_k}, "
                        "but no sufficiently flippable positive examples were found."
                    )
                    raise SystemExit(1)

            source_counts = defaultdict(int)
            generated_count = 0

            if negative_policy == "rn_hardmix":
                source_budget = max(n_neg, n_neg * 3)
                source_pool = choose_synthetic_sources(eligible_pos, selected_pos, source_budget)
                candidate_records = []

                for src_file in source_pool:
                    af_facts, labels = get_parsed(src_file)
                    flippable = count_flippable(labels)
                    if flippable == 0:
                        continue

                    max_k = max(1, min(flippable, max(2, flip_k)))
                    for _ in range(rn_candidates_per_source):
                        k_value = 1 if max_k == 1 else random.randint(1, max_k)
                        mutated_labels = build_synthetic_negative(
                            labels,
                            "flip_k" if k_value > 1 else "flip_one",
                            flip_k=k_value
                        )
                        if mutated_labels is None:
                            continue
                        changed = sum(
                            1 for arg, status in labels.items()
                            if mutated_labels.get(arg) != status
                        )
                        reliability = changed / flippable if flippable else 0.0
                        candidate_records.append(
                            {
                                "src_file": src_file,
                                "af_facts": af_facts,
                                "mutated_labels": mutated_labels,
                                "reliability": reliability,
                                "hardness": 1.0 - reliability,
                                "sig": labels_signature(mutated_labels),
                            }
                        )

                if not candidate_records:
                    print("Error: rn_hardmix could not generate any candidate negatives.")
                    raise SystemExit(1)

                selected_candidates = []
                seen = set()
                n_reliable = min(n_neg, int(round(n_neg * rn_reliable_fraction)))

                for rec in sorted(candidate_records, key=lambda x: (-x["reliability"], -x["hardness"])):
                    key = (rec["src_file"], rec["sig"])
                    if key in seen:
                        continue
                    seen.add(key)
                    selected_candidates.append(rec)
                    if len(selected_candidates) >= n_reliable:
                        break

                for rec in sorted(candidate_records, key=lambda x: (-x["hardness"], -x["reliability"])):
                    if len(selected_candidates) >= n_neg:
                        break
                    key = (rec["src_file"], rec["sig"])
                    if key in seen:
                        continue
                    seen.add(key)
                    selected_candidates.append(rec)

                # Fallback if still short: plain flip_one from eligible sources.
                fallback_attempts = 0
                fallback_limit = max(10, n_neg * 5)
                while len(selected_candidates) < n_neg and fallback_attempts < fallback_limit:
                    fallback_attempts += 1
                    src_file = random.choice(eligible_pos)
                    af_facts, labels = get_parsed(src_file)
                    mutated_labels = build_synthetic_negative(labels, "flip_one", flip_k=1)
                    if mutated_labels is None:
                        continue
                    key = (src_file, labels_signature(mutated_labels))
                    if key in seen:
                        continue
                    seen.add(key)
                    selected_candidates.append(
                        {
                            "src_file": src_file,
                            "af_facts": af_facts,
                            "mutated_labels": mutated_labels,
                        }
                    )

                if len(selected_candidates) < n_neg:
                    print(
                        f"Error: rn_hardmix could only generate {len(selected_candidates)}/{n_neg} negatives."
                    )
                    raise SystemExit(1)

                for rec in selected_candidates[:n_neg]:
                    src_file = rec["src_file"]
                    source_counts[src_file] += 1
                    occurrence = source_counts[src_file]
                    base_id = os.path.basename(src_file).replace(".lp", "")
                    example_id = f"{base_id}_SNEG_{occurrence}"
                    label_facts = render_label_facts(rec["mutated_labels"])
                    directive, noisy = build_ilasp_directive(
                        example_id=example_id,
                        label_facts=label_facts,
                        af_facts=rec["af_facts"],
                        is_positive=False,
                        p=p,
                        deterministic=deterministic,
                        noise_factor=noise_factor,
                    )
                    if noisy:
                        print(f"Example {example_id} gets inverted.")
                        noisy_count += 1
                    ilasp_examples.append(directive)
                    generated_count += 1
            else:
                selected_sources = choose_synthetic_sources(eligible_pos, selected_pos, n_neg)
                for src_file in selected_sources:
                    source_counts[src_file] += 1
                    occurrence = source_counts[src_file]

                    af_facts, labels = get_parsed(src_file)
                    mutated_labels = build_synthetic_negative(
                        labels, negative_policy, flip_k=flip_k,
                        p_in=p_in_marginal, n_candidates=max(8, rn_candidates_per_source),
                    )
                    if mutated_labels is None:
                        continue

                    base_id = os.path.basename(src_file).replace(".lp", "")
                    example_id = f"{base_id}_SNEG_{occurrence}"
                    label_facts = render_label_facts(mutated_labels)
                    directive, noisy = build_ilasp_directive(
                        example_id=example_id,
                        label_facts=label_facts,
                        af_facts=af_facts,
                        is_positive=False,
                        p=p,
                        deterministic=deterministic,
                        noise_factor=noise_factor,
                    )
                    if noisy:
                        print(f"Example {example_id} gets inverted.")
                        noisy_count += 1
                    ilasp_examples.append(directive)
                    generated_count += 1

            if generated_count < n_neg:
                print(
                    f"Error: Could only generate {generated_count}/{n_neg} synthetic negatives "
                    f"for policy '{negative_policy}'."
                )
                raise SystemExit(1)

    random.shuffle(ilasp_examples)

    learn_bg_path = args.learn_background or "background_knowledge.lp"
    with open(resolve_repo_path(learn_bg_path), "r", encoding="utf-8") as bg_file:
        background_knowledge = bg_file.read()

    with open(resolve_repo_path("mode_declarations.las"), "r", encoding="utf-8") as mode_file:
        mode_declarations = mode_file.read()

    ilasp_constraints = background_knowledge + "\n" + mode_declarations

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(ilasp_examples) + "\n")
        f.write(ilasp_constraints + "\n")

    total_examples = n_pos + n_neg
    noise_ratio = (noisy_count / total_examples) if total_examples > 0 else 0.0
    print(
        f"✅ ILASP learning task generated and saved to {output_file} "
        f"with {total_examples} examples (pos={n_pos}, neg={n_neg}). "
        f"Noisy examples={noisy_count} ({noise_ratio:.2%}). "
        f"Negative policy={negative_policy}"
        + (f"(k={flip_k})" if negative_policy == "flip_k" else "")
        + (
            f"(reliable_frac={rn_reliable_fraction}, candidates_per_source={rn_candidates_per_source})"
            if negative_policy == "rn_hardmix"
            else ""
        )
        + "."
    )
    if negative_policy == "oracle_neg":
        print(
            f"[oracle_neg filter] Rejected {oracle_neg_rejected} oracle negatives "
            "that became satisfiable under training stack."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
