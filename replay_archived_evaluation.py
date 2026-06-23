#!/usr/bin/env python3
import argparse
import csv
import os
import time
from pathlib import Path

from artifact_paths import resolve_artifact_path, resolve_repo_path
from train_test import (
    DEFAULT_EVAL_MATCH_POLICY,
    RESULTS_HEADER,
    append_result_row,
    construct_prefix,
    count_heuristic_directives,
    ensure_results_file,
    evaluate_model_sets,
    extract_train_files,
    format_noise_token,
    get_train_test_sets,
    load_completed_keys,
    par2_score_seconds,
    resolve_balanced_test_examples_per_class,
    run_ground_truth_with_api,
    run_learned_model_with_api,
)
from solver_policy import (
    get_background_file,
    get_clingo_args,
    get_completion_rules_enabled,
    get_semantics_entry,
    get_show_predicates,
    load_semantics_config,
)


def safe_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def safe_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except Exception:
        return default


def safe_div(num, den):
    return num / den if den else 0.0


def resolve_archive_path(archive_root, raw_path):
    raw = (raw_path or "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return archive_root / candidate


def iter_condition_dirs(archive_root, semantics, condition_glob):
    pattern = condition_glob or f"{semantics}_partial_*_ratio_*"
    yield from sorted((archive_root / "results").glob(pattern))


def load_condition_rows(condition_dir):
    rows = []
    for csv_path in sorted(condition_dir.glob("results_*.csv")):
        with open(csv_path, "r", newline="", encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f, delimiter=";"):
                row["_source_csv"] = csv_path.name
                rows.append(row)
    rows.sort(
        key=lambda row: (
            safe_int(row.get("ITERATION")),
            safe_int(row.get("NFILES_POS")),
            safe_int(row.get("NFILES_NEG", row.get("NFILES_POS"))),
            safe_float(row.get("NOISE")),
        )
    )
    return rows


def build_row(row_dict):
    return [row_dict.get(header, "") for header in RESULTS_HEADER]


def replay_condition(
    archive_root,
    repo_root,
    condition_dir,
    semantics,
    base_output_dir,
    output_root,
    semantics_config,
    test_set_policy,
    test_examples_per_class,
    test_sampling_seed,
    eval_match_policy,
    max_rows=None,
):
    rows = load_condition_rows(condition_dir)
    if not rows:
        return 0

    partial = safe_float(rows[0].get("P_PARTIAL"))
    prefix = construct_prefix(semantics, partial)
    input_dir = repo_root / base_output_dir / f"labelled_{prefix}"
    if not input_dir.exists():
        raise FileNotFoundError(f"Missing labelled input directory: {input_dir}")

    max_train_pos = max(safe_int(row.get("NFILES_POS")) for row in rows)
    max_train_neg = max(
        safe_int(row.get("NFILES_NEG", row.get("NFILES_POS"))) for row in rows
    )
    effective_test_examples_per_class = None
    fixed_holdout_files = None
    if test_set_policy in {"balanced_remaining", "fixed_balanced_holdout"}:
        effective_test_examples_per_class = resolve_balanced_test_examples_per_class(
            input_dir=str(input_dir),
            max_train_pos=max_train_pos,
            max_train_neg=max_train_neg,
            requested_per_class=test_examples_per_class,
        )
    if test_set_policy == "fixed_balanced_holdout":
        from train_test import build_fixed_balanced_holdout_files

        fixed_holdout_files = build_fixed_balanced_holdout_files(
            input_dir=str(input_dir),
            test_examples_per_class=effective_test_examples_per_class,
            test_sampling_seed=test_sampling_seed,
            semantics=semantics,
            partial=partial,
        )

    semantics_entry = get_semantics_entry(semantics_config, semantics)
    asp_file = repo_root / semantics_entry["file"]
    learned_background_cfg = get_background_file(
        semantics_config, stage="train_test_learned"
    )
    ground_truth_background_cfg = get_background_file(
        semantics_config, stage="train_test_ground_truth"
    )
    learned_background_file = (
        repo_root / learned_background_cfg if learned_background_cfg else None
    )
    ground_truth_background_file = (
        repo_root / ground_truth_background_cfg if ground_truth_background_cfg else None
    )
    learned_clingo_args = get_clingo_args(
        semantics_config, semantics, stage="train_test_learned"
    )
    ground_truth_clingo_args = get_clingo_args(
        semantics_config, semantics, stage="train_test_ground_truth"
    )
    learned_completion_rules = get_completion_rules_enabled(
        semantics_config, stage="train_test_learned"
    )
    ground_truth_completion_rules = get_completion_rules_enabled(
        semantics_config, stage="train_test_ground_truth"
    )
    learned_show_predicates = get_show_predicates(
        semantics_config, stage="train_test_learned"
    )
    ground_truth_show_predicates = get_show_predicates(
        semantics_config, stage="train_test_ground_truth"
    )

    written = 0
    out_dir = output_root / condition_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        if max_rows is not None and written >= max_rows:
            break
        iteration = safe_int(row.get("ITERATION"))
        n_pos = safe_int(row.get("NFILES_POS"))
        n_neg = safe_int(row.get("NFILES_NEG", row.get("NFILES_POS")))
        noise = safe_float(row.get("NOISE"))
        noise_key = format_noise_token(noise)

        results_file = out_dir / f"results_{iteration}.csv"
        ensure_results_file(str(results_file))
        completed_keys = load_completed_keys(str(results_file))
        combo_key = (n_pos, n_neg, noise_key)
        if combo_key in completed_keys:
            continue

        task_file = resolve_archive_path(archive_root, row.get("ILASP_TASK_FILENAME"))
        model_file = resolve_archive_path(archive_root, row.get("LEARNED_MODEL_FILENAME"))
        if task_file is None or not task_file.exists():
            raise FileNotFoundError(f"Missing archived task file: {task_file}")
        if model_file is None:
            raise FileNotFoundError(
                f"Missing learned model reference in archived row from {condition_dir}"
            )

        train_files = extract_train_files(str(task_file))
        _, test_files, test_set_meta = get_train_test_sets(
            input_dir=str(input_dir),
            train_files=train_files,
            test_set_policy=test_set_policy,
            test_examples_per_class=effective_test_examples_per_class,
            test_sampling_seed=test_sampling_seed,
            semantics=semantics,
            partial=partial,
            iteration=iteration,
            n_pos=n_pos,
            n_neg=n_neg,
            noise=noise,
            fixed_holdout_files=fixed_holdout_files,
        )

        total = len(test_files)
        par2_factor = safe_float(row.get("PAR2_FACTOR"), 2.0)
        test_timeout_seconds = safe_int(row.get("TEST_PAR_TIMEOUT_SECONDS"), 1200)
        train_succeeded = safe_int(row.get("ILASP_TRAIN_SUCCEEDED"), 1) == 1 and model_file.exists()

        tp = fp = tn = fn = 0
        correct = 0
        par2_ilasp_test_seconds = 0.0
        par2_aspartix_seconds = 0.0

        if train_succeeded:
            for tf in test_files:
                test_path = input_dir / tf

                start = time.perf_counter()
                ilasp_models = run_learned_model_with_api(
                    str(model_file),
                    str(test_path),
                    str(learned_background_file) if learned_background_file else None,
                    clingo_args=learned_clingo_args,
                    completion_rules=learned_completion_rules,
                    show_predicates=learned_show_predicates,
                )
                elapsed = time.perf_counter() - start
                par2_ilasp_test_seconds += par2_score_seconds(
                    elapsed, test_timeout_seconds, par2_factor
                )

                start = time.perf_counter()
                gt_models = run_ground_truth_with_api(
                    str(asp_file),
                    str(test_path),
                    str(ground_truth_background_file) if ground_truth_background_file else None,
                    clingo_args=ground_truth_clingo_args,
                    completion_rules=ground_truth_completion_rules,
                    show_predicates=ground_truth_show_predicates,
                )
                elapsed = time.perf_counter() - start
                par2_aspartix_seconds += par2_score_seconds(
                    elapsed, test_timeout_seconds, par2_factor
                )

                is_correct, add_tp, add_fp, add_tn, add_fn = evaluate_model_sets(
                    ilasp_models,
                    gt_models,
                    eval_match_policy,
                )
                if is_correct:
                    correct += 1
                tp += add_tp
                fp += add_fp
                tn += add_tn
                fn += add_fn
        else:
            penalty_per_test = par2_factor * test_timeout_seconds
            par2_ilasp_test_seconds = total * penalty_per_test
            for tf in test_files:
                test_path = input_dir / tf
                start = time.perf_counter()
                gt_models = run_ground_truth_with_api(
                    str(asp_file),
                    str(test_path),
                    str(ground_truth_background_file) if ground_truth_background_file else None,
                    clingo_args=ground_truth_clingo_args,
                    completion_rules=ground_truth_completion_rules,
                    show_predicates=ground_truth_show_predicates,
                )
                elapsed = time.perf_counter() - start
                par2_aspartix_seconds += par2_score_seconds(
                    elapsed, test_timeout_seconds, par2_factor
                )
                is_correct, add_tp, add_fp, add_tn, add_fn = evaluate_model_sets(
                    [],
                    gt_models,
                    eval_match_policy,
                )
                if is_correct:
                    correct += 1
                tp += add_tp
                fp += add_fp
                tn += add_tn
                fn += add_fn

        accuracy = correct / total if total else 0.0
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)

        learned_heuristic_rules = count_heuristic_directives(str(model_file))
        learned_has_heuristic = int(learned_heuristic_rules > 0)
        replay_row = {
            "ILASP_TASK_FILENAME": str(task_file.relative_to(repo_root)),
            "NFILES_POS": n_pos,
            "NFILES_NEG": n_neg,
            "NOISE": noise,
            "NEGATIVE_POLICY": row.get("NEGATIVE_POLICY", "oracle_neg"),
            "NEGATIVE_FLIP_K": row.get("NEGATIVE_FLIP_K", 1),
            "P_PARTIAL": partial,
            "TEST_SET_POLICY": test_set_meta["test_set_policy"],
            "TEST_SET_TARGET_PER_CLASS": test_set_meta["test_set_target_per_class"],
            "TEST_SET_POS": test_set_meta["test_set_pos"],
            "TEST_SET_NEG": test_set_meta["test_set_neg"],
            "TEST_SET_SIZE": total,
            "EVAL_MATCH_POLICY": eval_match_policy,
            "RUNNING_TIME_ILASP_TRAIN_SECONDS": row.get("RUNNING_TIME_ILASP_TRAIN_SECONDS", ""),
            "PAR2_SCORE_ILASP_TEST_SECONDS": par2_ilasp_test_seconds,
            "PAR2_SCORE_ASPARTIX_SECONDS": par2_aspartix_seconds,
            "ILASP_TRAIN_TIMED_OUT": row.get("ILASP_TRAIN_TIMED_OUT", ""),
            "ILASP_TRAIN_SUCCEEDED": int(train_succeeded),
            "ILASP_TRAIN_EXIT_CODE": row.get("ILASP_TRAIN_EXIT_CODE", ""),
            "ILASP_TRAIN_RETRIES_USED": row.get("ILASP_TRAIN_RETRIES_USED", ""),
            "TRAIN_TIMEOUT_SECONDS": row.get("TRAIN_TIMEOUT_SECONDS", ""),
            "TEST_PAR_TIMEOUT_SECONDS": test_timeout_seconds,
            "PAR2_FACTOR": par2_factor,
            "LEARNED_MODEL_FILENAME": str(model_file.relative_to(repo_root)),
            "LEARNED_HEURISTIC_RULES": learned_heuristic_rules,
            "LEARNED_HAS_HEURISTIC": learned_has_heuristic,
            "SYNTH_NEG_TOTAL": row.get("SYNTH_NEG_TOTAL", ""),
            "SYNTH_NEG_ORACLE_LEGAL": row.get("SYNTH_NEG_ORACLE_LEGAL", ""),
            "SYNTH_NEG_ORACLE_LEGAL_RATE": row.get("SYNTH_NEG_ORACLE_LEGAL_RATE", ""),
            "SYNTH_NEG_ORACLE_REJECT_RATE": row.get("SYNTH_NEG_ORACLE_REJECT_RATE", ""),
            "TP": tp,
            "FP": fp,
            "TN": tn,
            "FN": fn,
            "PRECISION": precision,
            "RECALL": recall,
            "F1": f1,
            "ACCURACY": accuracy,
            "ITERATION": iteration,
        }
        append_result_row(str(results_file), build_row(replay_row))
        written += 1
        print(
            f"[Replay] {condition_dir.name} iter={iteration} "
            f"pos={n_pos} neg={n_neg} noise={noise} -> {results_file.name}"
        )

    return written


def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Replay archived learned models through the current evaluator without retraining.",
        add_help=add_help,
    )
    parser.add_argument("--archive_root", required=True, help="Archived benchmark root containing results/train/train_output.")
    parser.add_argument("--semantics", required=True, help="Semantics to replay, e.g. PRF.")
    parser.add_argument("--base_output_dir", default="labelled", help="Base labelled-data directory in the current repo.")
    parser.add_argument("--output_root", required=True, help="Directory where replayed results CSVs will be written.")
    parser.add_argument("--condition_glob", default=None, help="Optional glob under archive_root/results to restrict replay scope.")
    parser.add_argument(
        "--test_set_policy",
        choices=("fixed_balanced_holdout", "balanced_remaining", "all_remaining"),
        default="fixed_balanced_holdout",
    )
    parser.add_argument("--test_examples_per_class", type=int, default=None)
    parser.add_argument("--test_sampling_seed", type=int, default=0)
    parser.add_argument(
        "--eval_match_policy",
        choices=("full_exact_model", "existential_acceptance"),
        default=DEFAULT_EVAL_MATCH_POLICY,
    )
    parser.add_argument("--semantics_config", default="semantics_config.json")
    parser.add_argument("--max_rows_per_condition", type=int, default=None)
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    repo_root = Path(resolve_repo_path(".", "."))
    archive_root = Path(args.archive_root).resolve()
    output_root = Path(resolve_artifact_path(args.output_root)).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    semantics_config = load_semantics_config(
        resolve_repo_path(args.semantics_config, "semantics_config.json")
    )
    total_written = 0
    for condition_dir in iter_condition_dirs(archive_root, args.semantics, args.condition_glob):
        total_written += replay_condition(
            archive_root=archive_root,
            repo_root=repo_root,
            condition_dir=condition_dir,
            semantics=args.semantics,
            base_output_dir=resolve_artifact_path(args.base_output_dir, "labelled"),
            output_root=output_root,
            semantics_config=semantics_config,
            test_set_policy=args.test_set_policy,
            test_examples_per_class=args.test_examples_per_class,
            test_sampling_seed=args.test_sampling_seed,
            eval_match_policy=args.eval_match_policy,
            max_rows=args.max_rows_per_condition,
        )

    print(f"[Done] wrote {total_written} replayed result rows to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
