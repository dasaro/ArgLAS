import os
import re
import csv
import time
import subprocess
import argparse
import clingo
import sys
import json
import random
import hashlib
from artifact_paths import resolve_artifact_path, resolve_repo_path
from ilasp_policy import load_ilasp_config, resolve_ilasp_args
from solver_runtime import build_semantics_runtime, solve_models
from solver_policy import (
    get_background_file,
    get_clingo_args,
    get_completion_rules_enabled,
    get_eval_on_bare_aaf,
    get_semantics_entry,
    get_show_predicates,
    load_semantics_config,
    semantics_wants_ilasp_heuristics,
)

DEFAULT_TRAIN_TIMEOUT_SECONDS = 1200
DEFAULT_TEST_PAR_TIMEOUT_SECONDS = 1200
DEFAULT_PAR2_FACTOR = 2.0
DEFAULT_RETRY_ON_EXIT_CODE_MINUS_11 = 1
DEFAULT_EVAL_MATCH_POLICY = "full_exact_model"
ILASP_UNSAT_EXIT_CODE = -2

RESULTS_HEADER = [
    "ILASP_TASK_FILENAME", "NFILES_POS", "NFILES_NEG", "NOISE", "NEGATIVE_POLICY", "NEGATIVE_FLIP_K", "P_PARTIAL",
    "TEST_SET_POLICY", "TEST_SET_TARGET_PER_CLASS", "TEST_SET_POS", "TEST_SET_NEG",
    "TEST_SET_SIZE", "EVAL_MATCH_POLICY",
    "RUNNING_TIME_ILASP_TRAIN_SECONDS",
    "TEST_LEARNED_TOTAL_SECONDS", "TEST_LEARNED_MEAN_SECONDS", "TEST_LEARNED_MAX_SECONDS",
    "TEST_ORACLE_TOTAL_SECONDS", "TEST_ORACLE_MEAN_SECONDS", "TEST_ORACLE_MAX_SECONDS",
    "ANY_TEST_TIMED_OUT", "ILASP_TRAIN_TIMED_OUT",
    "ILASP_TRAIN_SUCCEEDED", "ILASP_TRAIN_EXIT_CODE", "ILASP_TRAIN_RETRIES_USED",
    "TRAIN_TIMEOUT_SECONDS", "TEST_TIMEOUT_SECONDS",
    "LEARNED_MODEL_FILENAME",
    "LEARNED_HEURISTIC_RULES", "LEARNED_HAS_HEURISTIC",
    "SYNTH_NEG_TOTAL", "SYNTH_NEG_ORACLE_LEGAL", "SYNTH_NEG_ORACLE_LEGAL_RATE", "SYNTH_NEG_ORACLE_REJECT_RATE",
    "TP", "FP", "TN", "FN", "PRECISION", "RECALL", "F1", "MCC",
    "ACCURACY", "RUN_SEED", "ITERATION"
]

ILASP_EXAMPLE_RE = re.compile(
    r"^#(pos|neg)\(([^,]+),\s*\{(.*?)\},\s*\{\},\s*\{(.*?)\}\)\.$"
)
FACT_RE = re.compile(r"[^.]+\.")

def generate_ilasp_task(
    n_pos,
    n_neg,
    noise,
    input_dir,
    output_file,
    negative_policy="oracle_neg",
    negative_flip_k=1,
    semantics=None,
    semantics_config_path="semantics_config.json",
    allowed_examples_manifest=None,
    seed=None,
):
    print(f"Generating ILASP task for POS={n_pos}, NEG={n_neg}, NOISE={noise}, NEG_POLICY={negative_policy}, FLIP_K={negative_flip_k}...")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_ilasp_task.py")
    semantics_config_path = resolve_repo_path(semantics_config_path, "semantics_config.json")
    command = [
        sys.executable,
        script_path,
        input_dir,
        output_file,
        str(n_pos),
        str(noise),
        f"--n_neg={n_neg}",
        f"--negative_policy={negative_policy}",
        f"--flip_k={negative_flip_k}",
        f"--semantics_config={semantics_config_path}",
    ]
    if semantics:
        command.append(f"--semantics={semantics}")
    if allowed_examples_manifest:
        command.append(f"--allowed_examples_manifest={allowed_examples_manifest}")
    if seed is not None:
        command.append(f"--seed={int(seed)}")
    if noise != 0 or negative_policy != "oracle_neg":
        command.append("--noise_factor=100")
    subprocess.run(command, check=True)
    print(f"ILASP task saved to {output_file}")

def extract_train_files(task_file):
    train_files = set()
    pattern = r"#(?:pos|neg)\((aaf_\d+_\d+_[A-Z]+_[A-Z]+_\d+)(?:_SNEG_\d+)?[TF]"

    with open(task_file, 'r') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                train_files.add(match.group(1) + ".lp")

    return list(train_files)

def split_labelled_files_by_class(files):
    pos_files = sorted(f for f in files if "_POS_" in f and f.endswith(".lp"))
    neg_files = sorted(f for f in files if "_NEG_" in f and f.endswith(".lp"))
    return pos_files, neg_files

def stable_sample(files, k, seed_parts):
    seed_blob = "||".join(str(part) for part in seed_parts)
    seed_value = int(hashlib.sha256(seed_blob.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_value)
    return sorted(rng.sample(sorted(files), k))


def stable_seed_from_parts(*seed_parts):
    seed_blob = "||".join(str(part) for part in seed_parts)
    return int(hashlib.sha256(seed_blob.encode("utf-8")).hexdigest()[:16], 16)

def resolve_balanced_test_examples_per_class(input_dir, max_train_pos, max_train_neg, requested_per_class=None):
    all_files = set(f for f in os.listdir(input_dir) if f.endswith(".lp"))
    all_pos, all_neg = split_labelled_files_by_class(all_files)
    available_pos = len(all_pos) - max_train_pos
    available_neg = len(all_neg) - max_train_neg
    auto_per_class = min(available_pos, available_neg)

    if auto_per_class <= 0:
        raise ValueError(
            f"Balanced test set is infeasible for '{input_dir}': "
            f"POS={len(all_pos)}, NEG={len(all_neg)}, "
            f"max_train_pos={max_train_pos}, max_train_neg={max_train_neg}."
        )

    if requested_per_class is None:
        return auto_per_class

    if requested_per_class > auto_per_class:
        raise ValueError(
            f"Requested --test_examples_per_class={requested_per_class} exceeds feasible "
            f"balanced test size per class ({auto_per_class}) for '{input_dir}'."
        )
    return requested_per_class


def build_fixed_balanced_holdout_files(
    input_dir,
    test_examples_per_class,
    test_sampling_seed=0,
    semantics=None,
    partial=None,
):
    if test_examples_per_class is None or test_examples_per_class <= 0:
        raise ValueError(
            "Fixed balanced hold-out requires test_examples_per_class to be a positive integer."
        )

    all_files = set(f for f in os.listdir(input_dir) if f.endswith(".lp"))
    all_pos, all_neg = split_labelled_files_by_class(all_files)
    if len(all_pos) < test_examples_per_class or len(all_neg) < test_examples_per_class:
        raise ValueError(
            f"Insufficient files for fixed balanced hold-out in '{input_dir}': "
            f"need {test_examples_per_class} per class, found "
            f"POS={len(all_pos)}, NEG={len(all_neg)}."
        )

    seed_parts = [
        "fixed_balanced_holdout",
        test_sampling_seed,
        os.path.abspath(input_dir),
        semantics,
        partial,
    ]
    selected_pos = stable_sample(all_pos, test_examples_per_class, seed_parts + ["POS"])
    selected_neg = stable_sample(all_neg, test_examples_per_class, seed_parts + ["NEG"])
    return sorted(selected_pos + selected_neg)


def aaf_group_id(filename):
    """Source-AAF identity (N, i) from aaf_<N>_<i>_<SEM>_<POS|NEG>_<k>.lp."""
    m = re.match(r"aaf_(\d+)_(\d+)_", filename)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def build_grouped_folds(input_dir, k, fold_seed=0):
    """Partition the source-AAFs in input_dir into k GROUP-DISJOINT CV folds,
    stratified by AAF size N. Returns a list of k (train_aafs, test_aafs) pairs
    of (N, i) tuples: fold j's test AAFs tile the population exactly once and
    train = population - test, so a given source-AAF is NEVER in both the train
    and test side of the same fold (this is the fix for AAF-level leakage,
    audit defect #2). The per-size shuffle seed depends ONLY on (fold_seed, N)
    -- not on os.path.abspath(input_dir) and not on the semantics -- so folds
    are reproducible across checkouts (fixing the path-dependent-seed wart) and
    identical across semantics for paired cross-semantics comparison."""
    if k < 2:
        raise ValueError("grouped_kfold requires k >= 2 folds.")
    ids_by_size = {}
    for f in os.listdir(input_dir):
        if not f.endswith(".lp"):
            continue
        gid = aaf_group_id(f)
        if gid is None:
            continue
        ids_by_size.setdefault(gid[0], set()).add(gid[1])
    if not ids_by_size:
        raise ValueError(f"No parseable source-AAFs found in '{input_dir}'.")
    test_aafs = [set() for _ in range(k)]
    all_aafs = set()
    for size in sorted(ids_by_size):
        ids = sorted(ids_by_size[size])
        for i in ids:
            all_aafs.add((size, i))
        rng = random.Random(stable_seed_from_parts("grouped_folds", fold_seed, size))
        rng.shuffle(ids)
        n = len(ids)
        for j in range(k):
            lo = (j * n) // k
            hi = ((j + 1) * n) // k
            for i in ids[lo:hi]:
                test_aafs[j].add((size, i))
    return [(all_aafs - test_aafs[j], test_aafs[j]) for j in range(k)]


def build_grouped_balanced_test(input_dir, test_aafs, test_per_class, fold_seed, fold_index):
    """Balanced (equal POS/NEG) hold-out drawn ONLY from the given test AAFs.
    Caps at the smaller class so the result stays balanced; seed is
    path-independent (fold_seed, fold_index)."""
    test_set = set(test_aafs)
    pos = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".lp") and "_POS_" in f and aaf_group_id(f) in test_set
    )
    neg = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".lp") and "_NEG_" in f and aaf_group_id(f) in test_set
    )
    # Min-example guard: fail fast if this fold cannot supply a full balanced test
    # set, instead of silently shrinking to an under-powered/unbalanced one.
    if min(len(pos), len(neg)) < test_per_class:
        raise ValueError(
            f"Grouped fold {fold_index} cannot reach test_examples_per_class="
            f"{test_per_class} in '{input_dir}': only POS={len(pos)}, NEG={len(neg)} "
            f"available among the fold's test AAFs. Lower test_examples_per_class, "
            f"raise the AAF count, or reduce K."
        )
    per_class = test_per_class
    seed_parts = ["grouped_balanced_test", fold_seed, fold_index]
    selected_pos = stable_sample(pos, per_class, seed_parts + ["POS"])
    selected_neg = stable_sample(neg, per_class, seed_parts + ["NEG"])
    return sorted(selected_pos + selected_neg)


def build_grouped_train_manifest(input_dir, train_aafs):
    """All labelled files whose source-AAF is in the fold's training AAF set."""
    train_set = set(train_aafs)
    return sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".lp") and aaf_group_id(f) in train_set
    )


def get_train_test_sets(
    input_dir,
    train_files,
    test_set_policy="fixed_balanced_holdout",
    test_examples_per_class=None,
    test_sampling_seed=0,
    semantics=None,
    partial=None,
    iteration=None,
    n_pos=None,
    n_neg=None,
    noise=None,
    fixed_holdout_files=None,
):
    all_files = set(f for f in os.listdir(input_dir) if f.endswith(".lp"))
    train_files_set = set(train_files)
    remaining_files = sorted(all_files - train_files_set)

    if test_set_policy == "all_remaining":
        pos_files, neg_files = split_labelled_files_by_class(remaining_files)
        metadata = {
            "test_set_policy": test_set_policy,
            "test_set_target_per_class": "",
            "test_set_pos": len(pos_files),
            "test_set_neg": len(neg_files),
        }
        return train_files, remaining_files, metadata

    if test_set_policy == "fixed_balanced_holdout":
        holdout_files = (
            sorted(fixed_holdout_files)
            if fixed_holdout_files is not None
            else build_fixed_balanced_holdout_files(
                input_dir=input_dir,
                test_examples_per_class=test_examples_per_class,
                test_sampling_seed=test_sampling_seed,
                semantics=semantics,
                partial=partial,
            )
        )
        holdout_set = set(holdout_files)
        overlap = sorted(train_files_set & holdout_set)
        if overlap:
            preview = ", ".join(overlap[:5])
            if len(overlap) > 5:
                preview += ", ..."
            raise ValueError(
                "Fixed balanced hold-out leaked into training examples. "
                f"Overlap count={len(overlap)} in '{input_dir}'. "
                f"Examples: {preview}"
            )
        holdout_pos, holdout_neg = split_labelled_files_by_class(holdout_files)
        metadata = {
            "test_set_policy": test_set_policy,
            "test_set_target_per_class": test_examples_per_class,
            "test_set_pos": len(holdout_pos),
            "test_set_neg": len(holdout_neg),
        }
        return train_files, holdout_files, metadata

    if test_set_policy != "balanced_remaining":
        raise ValueError(f"Unsupported test_set_policy: {test_set_policy}")

    if test_examples_per_class is None or test_examples_per_class <= 0:
        raise ValueError(
            "Balanced test policy requires test_examples_per_class to be a positive integer."
        )

    pos_files, neg_files = split_labelled_files_by_class(remaining_files)
    if len(pos_files) < test_examples_per_class or len(neg_files) < test_examples_per_class:
        raise ValueError(
            f"Insufficient remaining files for balanced test set in '{input_dir}': "
            f"need {test_examples_per_class} per class, found "
            f"POS={len(pos_files)}, NEG={len(neg_files)}."
        )

    seed_parts = [
        "balanced_test_subset",
        test_sampling_seed,
        os.path.abspath(input_dir),
        semantics,
        partial,
        iteration,
        n_pos,
        n_neg,
        noise,
    ]
    selected_pos = stable_sample(pos_files, test_examples_per_class, seed_parts + ["POS"])
    selected_neg = stable_sample(neg_files, test_examples_per_class, seed_parts + ["NEG"])
    test_files = sorted(selected_pos + selected_neg)
    metadata = {
        "test_set_policy": test_set_policy,
        "test_set_target_per_class": test_examples_per_class,
        "test_set_pos": len(selected_pos),
        "test_set_neg": len(selected_neg),
    }
    return train_files, test_files, metadata

def par2_score_seconds(elapsed_seconds, timeout_seconds, par2_factor):
    if elapsed_seconds >= timeout_seconds:
        return par2_factor * timeout_seconds
    return elapsed_seconds

def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0

def matthews_corrcoef(tp, fp, tn, fn):
    # MCC = (TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN)); 0.0 when any
    # marginal is 0 (degenerate single-class fold) to avoid div-by-zero/NaN.
    import math
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return ((tp * tn) - (fp * fn)) / denom if denom else 0.0

def canonical_model_set(models):
    return set(map(frozenset, models))

def evaluate_model_sets(pred_models, gt_models, eval_match_policy):
    pred_set = canonical_model_set(pred_models)
    gt_set = canonical_model_set(gt_models)
    gt_positive = len(gt_set) > 0

    if eval_match_policy == "full_exact_model":
        correct = pred_set == gt_set
        if gt_positive:
            return correct, int(correct), 0, 0, int(not correct)
        return correct, 0, int(len(pred_set) > 0), int(correct), 0

    if eval_match_policy == "existential_acceptance":
        pred_positive = len(pred_set) > 0
        correct = pred_set == gt_set
        if pred_positive and gt_positive:
            return correct, 1, 0, 0, 0
        if pred_positive and (not gt_positive):
            return correct, 0, 1, 0, 0
        if (not pred_positive) and (not gt_positive):
            return correct, 0, 0, 1, 0
        return correct, 0, 0, 0, 1

    raise ValueError(f"Unsupported eval_match_policy: {eval_match_policy}")

def format_noise_token(noise):
    token = f"{noise:.10g}" if isinstance(noise, float) else str(noise)
    return token.replace("-", "m").replace(".", "_")

def next_available_path(path):
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    suffix = 2
    while True:
        candidate = f"{base}_v{suffix}{ext}"
        if not os.path.exists(candidate):
            return candidate
        suffix += 1

def count_heuristic_directives(model_file):
    if not os.path.exists(model_file):
        return 0
    count = 0
    with open(model_file, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            stripped = raw.strip()
            if stripped.startswith("#heuristic") or stripped.startswith("# heuristic"):
                count += 1
    return count

def is_probable_asp_rule(line):
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("%") or stripped.startswith("["):
        return False
    # ILASP heuristic directives end with a bracketed tuple, not a trailing dot.
    if stripped.startswith("#heuristic"):
        return stripped.endswith("]") and "[" in stripped
    if not stripped.endswith("."):
        return False
    return (
        stripped.startswith(":-")
        or stripped.startswith(":~")
        or stripped.startswith("#")
        or stripped.startswith("{")
        or stripped[0].isalpha()
    )

def extract_hypothesis_rules(ilasp_output):
    lines = ilasp_output.splitlines()

    # Primary path: read the section after "Final Hypothesis".
    rules_after_final = []
    in_final_hypothesis = False
    for line in lines:
        stripped = line.strip()
        if "Final Hypothesis" in stripped:
            in_final_hypothesis = True
            continue
        if not in_final_hypothesis:
            continue
        if is_probable_asp_rule(stripped):
            rules_after_final.append(stripped)

    if rules_after_final:
        return rules_after_final

    # Fallback path: ILASP output without debug banners.
    return [line.strip() for line in lines if is_probable_asp_rule(line)]

def ensure_text_output(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)

def _final_verdict_unsat(output_text):
    """ILASP signals genuine unsatisfiability by printing 'UNSATISFIABLE' as its
    FINAL solver verdict. Treat the task as UNSAT only when the last meaningful
    (non-comment, non-blank) line is exactly UNSATISFIABLE -- so an intermediate
    'UNSATISFIABLE' emitted during ILASP's iterative counterexample search,
    followed by further output or a learned hypothesis, is NOT misread as failure.
    Noisy/penalised tasks always have the empty-hypothesis fallback and so should
    never end UNSATISFIABLE; this avoids the prior bare-substring false positives."""
    meaningful = [
        ln.strip() for ln in output_text.splitlines()
        if ln.strip() and not ln.strip().startswith("%")
    ]
    return bool(meaningful) and meaningful[-1] == "UNSATISFIABLE"


def run_ilasp(task_file, output_file, extra_args, timeout_seconds, retry_on_exit_code_minus_11):
    start = time.perf_counter()
    command = ["ILASP", "--version=4"] + extra_args + ["-d", task_file]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    max_attempts = 1 + max(0, int(retry_on_exit_code_minus_11))
    attempts = []
    last_returncode = None
    last_timed_out = False
    last_unsat = False
    final_output_text = ""

    for attempt_id in range(1, max_attempts + 1):
        timed_out = False
        unsat = False
        output_text = ""
        status_messages = []

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )

        try:
            output_text, _ = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as e:
            timed_out = True
            partial_output = ensure_text_output(
                getattr(e, "stdout", None) if hasattr(e, "stdout") else None
            )
            if not partial_output:
                partial_output = ensure_text_output(getattr(e, "output", None))
            process.kill()
            try:
                remaining_output, _ = process.communicate()
            except Exception:
                remaining_output = ""
            output_text = partial_output + ensure_text_output(remaining_output)

        output_text = ensure_text_output(output_text)
        unsat = (not timed_out) and _final_verdict_unsat(output_text)

        if output_text:
            sys.stdout.write(output_text)
            sys.stdout.flush()

        if timed_out:
            timeout_msg = (
                f"\n[Timeout] ILASP training exceeded {timeout_seconds}s. "
                "Training process terminated.\n"
            )
            status_messages.append(timeout_msg)
            sys.stdout.write(timeout_msg)
            sys.stdout.flush()
        elif unsat:
            unsat_msg = (
                f"\n[Warning] ILASP reported UNSATISFIABLE task "
                f"for {task_file} (attempt {attempt_id}/{max_attempts}).\n"
            )
            status_messages.append(unsat_msg)
            sys.stdout.write(unsat_msg)
            sys.stdout.flush()
        elif process.returncode != 0:
            warn_msg = (
                f"\n[Warning] ILASP exited with code {process.returncode} "
                f"for task {task_file} (attempt {attempt_id}/{max_attempts}).\n"
            )
            status_messages.append(warn_msg)
            sys.stdout.write(warn_msg)
            sys.stdout.flush()

        attempt_log_file = f"{output_file}.attempt_{attempt_id}.log"
        with open(attempt_log_file, "w") as log:
            if output_text:
                log.write(output_text)
                if not output_text.endswith("\n"):
                    log.write("\n")
            for msg in status_messages:
                log.write(msg)

        attempts.append(
            {
                "attempt_id": attempt_id,
                "timed_out": timed_out,
                "unsat": unsat,
                "returncode": process.returncode,
                "output_text": output_text,
                "status_messages": status_messages,
                "log_file": attempt_log_file,
            }
        )

        last_returncode = process.returncode
        last_timed_out = timed_out
        last_unsat = unsat
        final_output_text = output_text

        should_retry = (
            (not timed_out)
            and (not unsat)
            and process.returncode == -11
            and attempt_id < max_attempts
        )
        if should_retry:
            retry_msg = (
                f"[Retry] Retrying ILASP after exit code -11 "
                f"(next attempt {attempt_id + 1}/{max_attempts})...\n"
            )
            sys.stdout.write(retry_msg)
            sys.stdout.flush()
            continue

        break

    with open(output_file + ".log", "w") as combined_log:
        for attempt in attempts:
            combined_log.write(
                f"===== ILASP attempt {attempt['attempt_id']} "
                f"(returncode={attempt['returncode']}, timed_out={int(attempt['timed_out'])}, "
                f"unsat={int(attempt.get('unsat', False))}) =====\n"
            )
            if attempt["output_text"]:
                combined_log.write(attempt["output_text"])
                if not attempt["output_text"].endswith("\n"):
                    combined_log.write("\n")
            for msg in attempt["status_messages"]:
                combined_log.write(msg)
            combined_log.write("\n")

    effective_returncode = last_returncode
    if (not last_timed_out) and last_unsat and (last_returncode == 0):
        effective_returncode = ILASP_UNSAT_EXIT_CODE

    succeeded = (not last_timed_out) and (not last_unsat) and (last_returncode == 0)
    with open(output_file, "w") as model_file:
        if succeeded:
            hypothesis_rules = extract_hypothesis_rules(final_output_text)
            if hypothesis_rules:
                model_file.write("\n".join(hypothesis_rules) + "\n")
            else:
                # Empty hypothesis is still a valid model artifact.
                model_file.write("% ILASP completed but produced an empty hypothesis.\n")
        else:
            # Keep learned model syntactically valid ASP even on failures.
            model_file.write(
                f"% ILASP training failed for task {task_file}\n"
                f"% timed_out={int(last_timed_out)} unsat={int(last_unsat)} returncode={effective_returncode}\n"
            )

    elapsed_seconds = time.perf_counter() - start
    if last_timed_out:
        # Keep runtime metric bounded by timeout on forced termination.
        elapsed_seconds = min(elapsed_seconds, float(timeout_seconds))
    retries_used = max(0, len(attempts) - 1)
    return elapsed_seconds, last_timed_out, effective_returncode, succeeded, retries_used

def run_learned_model_with_api(
    model_file,
    test_file,
    background_file,
    clingo_args=None,
    completion_rules=True,
    show_predicates=None,
):
    return solve_models(
        files_to_load=[background_file, model_file, test_file],
        clingo_args=clingo_args,
        completion_rules=completion_rules,
        show_predicates=show_predicates,
    )

def run_ground_truth_with_api(
    semantics_file,
    test_file,
    background_file,
    clingo_args=None,
    completion_rules=True,
    show_predicates=None,
):
    # Keep ground-truth and learned-model evaluation symmetric:
    # both are solved with the same background and completion rules.
    return solve_models(
        files_to_load=[background_file, semantics_file, test_file],
        clingo_args=clingo_args,
        completion_rules=completion_rules,
        show_predicates=show_predicates,
    )

def parse_task_examples(task_file):
    examples = []
    with open(task_file, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or not line.startswith("#"):
                continue
            match = ILASP_EXAMPLE_RE.match(line)
            if not match:
                continue
            kind, raw_id, labels_blob, af_blob = match.groups()
            example_id = re.sub(r"(T|F)(@\d+)?$", "", raw_id.strip())
            label_atoms = []
            if labels_blob.strip():
                for atom in labels_blob.split(","):
                    atom = atom.strip()
                    if atom:
                        label_atoms.append(atom if atom.endswith(".") else f"{atom}.")
            af_facts = [m.group(0).strip() for m in FACT_RE.finditer(af_blob)]
            examples.append(
                {
                    "kind": kind,
                    "example_id": example_id,
                    "label_atoms": label_atoms,
                    "af_facts": af_facts,
                }
            )
    return examples

def count_oracle_legal_synthetic_negatives(
    task_file,
    semantics_file,
    background_file=None,
    clingo_args=None,
    completion_rules=False,
    show_predicates=None,
    cache=None,
):
    examples = parse_task_examples(task_file)
    if cache is None:
        cache = {}
    total = 0
    legal = 0

    for ex in examples:
        if "_SNEG_" not in ex["example_id"]:
            continue
        total += 1
        signature = (tuple(ex["label_atoms"]), tuple(ex["af_facts"]))
        if signature not in cache:
            inline_program = "\n".join(ex["label_atoms"] + ex["af_facts"])
            files_to_load = [semantics_file]
            if background_file:
                files_to_load = [background_file, semantics_file]
            models = solve_models(
                files_to_load=files_to_load,
                clingo_args=clingo_args,
                completion_rules=completion_rules,
                additional_program=inline_program,
                show_predicates=show_predicates,
            )
            cache[signature] = len(models) > 0
        if cache[signature]:
            legal += 1

    return legal, total

def construct_prefix(semantics, partial):
    return f"{semantics}_full" if partial >= 1.0 else f"{semantics}_partial_{partial}"

def build_sample_size_pairs(f_values, f_neg_values):
    if not f_neg_values:
        return [(f, f) for f in f_values]

    if len(f_values) != len(f_neg_values):
        raise ValueError(
            "When provided, --f_neg_values must have the same length as --f_values "
            "(pairwise mapping by position)."
        )

    return list(zip(f_values, f_neg_values))

def count_data_rows(csv_path):
    if not os.path.exists(csv_path):
        return 0
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        try:
            next(reader)  # header
        except StopIteration:
            return 0
        return sum(1 for row in reader if row)

def ensure_results_file(results_file):
    if os.path.exists(results_file) and os.path.getsize(results_file) > 0:
        return
    with open(results_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(RESULTS_HEADER)

def load_completed_keys(results_file):
    completed = set()
    if not os.path.exists(results_file) or os.path.getsize(results_file) == 0:
        return completed

    with open(results_file, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                n_pos = int(row["NFILES_POS"])
                n_neg = int(row.get("NFILES_NEG", row["NFILES_POS"]))
                noise_key = format_noise_token(float(row["NOISE"]))
                completed.add((n_pos, n_neg, noise_key))
            except Exception:
                # Ignore malformed rows and keep best-effort resume.
                continue
    return completed

def append_result_row(results_file, row):
    header_len = len(RESULTS_HEADER)
    if os.path.exists(results_file) and os.path.getsize(results_file) > 0:
        with open(results_file, "r", newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            header = next(reader, None)
            if header:
                header_len = len(header)
    if len(row) > header_len:
        row = row[:header_len]
    elif len(row) < header_len:
        row = row + [""] * (header_len - len(row))
    with open(results_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(row)

def run_experiment(semantics, partial, f_values, f_neg_values, n_values, iterations,
                   base_output_dir, train_dir, train_output_dir, results_dir,
                   no_prefix=False, dry_run=False,
                   train_timeout_seconds=None, test_par_timeout_seconds=None, par2_factor=None,
                   overwrite_existing_iterations=False, negative_policy="oracle_neg", negative_flip_k=1,
                   test_set_policy="fixed_balanced_holdout", test_examples_per_class=None, test_sampling_seed=0,
                   eval_match_policy=DEFAULT_EVAL_MATCH_POLICY, ilasp_config_path="ilasp_config.json",
                   semantics_config_path="semantics_config.json", task_sampling_seed_base=0):

    base_output_dir = resolve_artifact_path(base_output_dir, "labelled")
    train_dir = resolve_artifact_path(train_dir, "train")
    train_output_dir = resolve_artifact_path(train_output_dir, "train_output")
    results_dir = resolve_artifact_path(results_dir, "results")
    ilasp_config_path = resolve_repo_path(ilasp_config_path, "ilasp_config.json")
    semantics_config_path = resolve_repo_path(semantics_config_path, "semantics_config.json")

    prefix = construct_prefix(semantics, partial)
    input_dir = os.path.join(base_output_dir, f"labelled_{prefix}")

    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory '{input_dir}' does not exist. Run generate_extensions.py first.")

    train_dir = os.path.join(train_dir, prefix)
    train_output_dir = os.path.join(train_output_dir, prefix)

    # ✅ Do NOT append prefix to results_dir if --no_prefix is passed
    if not no_prefix:
        results_dir = os.path.join(results_dir, prefix)

    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(train_output_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    semantics_config = load_semantics_config(semantics_config_path)
    semantics_entry = get_semantics_entry(semantics_config, semantics)
    asp_file = resolve_repo_path(semantics_entry["file"])
    learned_clingo_args = get_clingo_args(
        semantics_config, semantics, stage="train_test_learned"
    )
    ground_truth_clingo_args = get_clingo_args(
        semantics_config, semantics, stage="train_test_ground_truth"
    )
    learned_background_file_cfg = get_background_file(
        semantics_config, stage="train_test_learned"
    )
    ground_truth_background_file_cfg = get_background_file(
        semantics_config, stage="train_test_ground_truth"
    )
    learned_background_file = (
        resolve_repo_path(learned_background_file_cfg)
        if learned_background_file_cfg
        else None
    )
    ground_truth_background_file = (
        resolve_repo_path(ground_truth_background_file_cfg)
        if ground_truth_background_file_cfg
        else None
    )
    learned_completion_rules = get_completion_rules_enabled(
        semantics_config, stage="train_test_learned", semantics=semantics
    )
    ground_truth_completion_rules = get_completion_rules_enabled(
        semantics_config, stage="train_test_ground_truth", semantics=semantics
    )
    eval_on_bare_aaf = get_eval_on_bare_aaf(semantics_config, semantics)
    learned_show_predicates = get_show_predicates(
        semantics_config, stage="train_test_learned"
    )
    ground_truth_show_predicates = get_show_predicates(
        semantics_config, stage="train_test_ground_truth"
    )
    ground_truth_runtime = build_semantics_runtime(
        semantics_config,
        semantics,
        stage="train_test_ground_truth",
    )
    ilasp_config = load_ilasp_config(ilasp_config_path)
    ilasp_args = resolve_ilasp_args(
        semantics=semantics,
        ilasp_config_path=ilasp_config_path,
        semantics_config_path=semantics_config_path,
    )
    learn_heuristics = semantics_wants_ilasp_heuristics(semantics_config, semantics)
    if learn_heuristics:
        print(f"[Config] {semantics}: ILASP heuristic learning enabled.")
    else:
        print(f"[Config] {semantics}: ILASP heuristic learning disabled.")
    global_ilasp_cfg = ilasp_config.get("global", {})
    effective_train_timeout_seconds = int(
        train_timeout_seconds
        if train_timeout_seconds is not None
        else global_ilasp_cfg.get("train_timeout_seconds", DEFAULT_TRAIN_TIMEOUT_SECONDS)
    )
    effective_test_par_timeout_seconds = int(
        test_par_timeout_seconds
        if test_par_timeout_seconds is not None
        else global_ilasp_cfg.get("test_par_timeout_seconds", DEFAULT_TEST_PAR_TIMEOUT_SECONDS)
    )
    effective_par2_factor = float(
        par2_factor
        if par2_factor is not None
        else global_ilasp_cfg.get("par2_factor", DEFAULT_PAR2_FACTOR)
    )
    effective_retry_on_exit_code_minus_11 = int(
        global_ilasp_cfg.get(
            "retry_on_exit_code_minus_11",
            DEFAULT_RETRY_ON_EXIT_CODE_MINUS_11
        )
    )
    if effective_train_timeout_seconds <= 0:
        raise ValueError("train_timeout_seconds must be > 0")
    if effective_test_par_timeout_seconds <= 0:
        raise ValueError("test_par_timeout_seconds must be > 0")
    if effective_par2_factor <= 0:
        raise ValueError("par2_factor must be > 0")
    if effective_retry_on_exit_code_minus_11 < 0:
        raise ValueError("retry_on_exit_code_minus_11 must be >= 0")
    if negative_flip_k <= 0:
        raise ValueError("negative_flip_k must be > 0")

    print(
        f"[Config] ILASP train timeout: {effective_train_timeout_seconds}s | "
        f"PAR-{effective_par2_factor:g} test threshold: {effective_test_par_timeout_seconds}s | "
        f"retry_on_exit_code_-11: {effective_retry_on_exit_code_minus_11}"
    )
    print(
        f"[Config] label_oracle_stage=train_test_ground_truth | "
        f"learned_background={learned_background_file or '(none)'} | "
        f"ground_truth_background={ground_truth_background_file or '(none)'} | "
        f"label_oracle_args={' '.join(ground_truth_runtime.clingo_args) if ground_truth_runtime.clingo_args else '(none)'} | "
        f"learned_args={' '.join(learned_clingo_args) if learned_clingo_args else '(none)'} | "
        f"gt_args={' '.join(ground_truth_clingo_args) if ground_truth_clingo_args else '(none)'}"
    )

    sample_pairs = build_sample_size_pairs(f_values, f_neg_values)
    expected_rows_per_iteration = len(sample_pairs) * len(n_values)
    oracle_legal_cache = {}
    max_train_pos = max(n_pos for n_pos, _ in sample_pairs)
    max_train_neg = max(n_neg for _, n_neg in sample_pairs)
    effective_test_examples_per_class = None
    fixed_holdout_files = None
    allowed_training_examples_manifest = None
    if test_set_policy in {"balanced_remaining", "fixed_balanced_holdout"}:
        effective_test_examples_per_class = resolve_balanced_test_examples_per_class(
            input_dir=input_dir,
            max_train_pos=max_train_pos,
            max_train_neg=max_train_neg,
            requested_per_class=test_examples_per_class,
        )
    if test_set_policy == "fixed_balanced_holdout":
        fixed_holdout_files = build_fixed_balanced_holdout_files(
            input_dir=input_dir,
            test_examples_per_class=effective_test_examples_per_class,
            test_sampling_seed=test_sampling_seed,
            semantics=semantics,
            partial=partial,
        )
        allowed_training_examples = sorted(
            set(f for f in os.listdir(input_dir) if f.endswith(".lp")) - set(fixed_holdout_files)
        )
        if not allowed_training_examples:
            raise ValueError(
                f"Training pool is empty after reserving fixed hold-out for '{input_dir}'."
            )
        allowed_training_examples_manifest = os.path.join(
            train_dir,
            f"allowed_training_examples_{prefix}.txt",
        )
        with open(allowed_training_examples_manifest, "w", encoding="utf-8") as f:
            for name in allowed_training_examples:
                f.write(name + "\n")

    grouped_kfold = test_set_policy == "grouped_kfold"
    grouped_folds = None
    if grouped_kfold:
        if effective_test_examples_per_class is None:
            effective_test_examples_per_class = (
                test_examples_per_class if test_examples_per_class is not None else 50
            )
        grouped_folds = build_grouped_folds(input_dir, iterations, fold_seed=test_sampling_seed)
        fold_counts = [(len(tr), len(te)) for tr, te in grouped_folds]
        print(
            f"[Config] grouped_kfold: K={iterations} group-disjoint folds over source-AAFs "
            f"(train/test AAF counts per fold: {fold_counts}); "
            f"test_per_class={effective_test_examples_per_class}"
        )
    print(
        f"[Config] test_set_policy={test_set_policy} | "
        f"test_examples_per_class="
        f"{effective_test_examples_per_class if effective_test_examples_per_class is not None else '(all remaining)'} | "
        f"test_sampling_seed={test_sampling_seed} | "
        f"task_sampling_seed_base={task_sampling_seed_base} | "
        f"eval_match_policy={eval_match_policy}"
    )

    for iteration in range(1, iterations + 1):
        results_file = os.path.join(results_dir, f"results_{iteration}.csv")
        if overwrite_existing_iterations and os.path.exists(results_file):
            os.remove(results_file)
        ensure_results_file(results_file)

        existing_rows = count_data_rows(results_file)
        if (not overwrite_existing_iterations) and existing_rows >= expected_rows_per_iteration:
            print(
                f"⏭️  Skipping iteration {iteration}: existing complete file "
                f"({existing_rows}/{expected_rows_per_iteration} rows) at {results_file}"
            )
            continue

        completed_keys = set()
        if not overwrite_existing_iterations:
            completed_keys = load_completed_keys(results_file)
            if existing_rows > 0 and existing_rows < expected_rows_per_iteration:
                print(
                    f"♻️  Resuming iteration {iteration}: existing file has "
                    f"{existing_rows}/{expected_rows_per_iteration} rows."
                )

        # Per-fold (grouped_kfold) hold-out + training manifest. The fold index IS
        # the `iteration` counter, so the per-iteration results files and resume
        # logic carry over unchanged (the ITERATION column now records the fold).
        # For non-grouped policies, reuse the global hold-out/manifest.
        if grouped_kfold:
            fold_train_aafs, fold_test_aafs = grouped_folds[iteration - 1]
            iter_holdout_files = build_grouped_balanced_test(
                input_dir,
                fold_test_aafs,
                effective_test_examples_per_class,
                fold_seed=test_sampling_seed,
                fold_index=iteration,
            )
            iter_manifest = os.path.join(
                train_dir, f"allowed_training_examples_{prefix}_fold{iteration}.txt"
            )
            with open(iter_manifest, "w", encoding="utf-8") as mf:
                for name in build_grouped_train_manifest(input_dir, fold_train_aafs):
                    mf.write(name + "\n")
        else:
            iter_holdout_files = fixed_holdout_files
            iter_manifest = allowed_training_examples_manifest

        for n_pos, n_neg in sample_pairs:
            for n in n_values:
                noise_key = format_noise_token(n)
                combo_key = (n_pos, n_neg, noise_key)
                if (not overwrite_existing_iterations) and combo_key in completed_keys:
                    print(
                        f"⏭️  Skipping completed task for iteration {iteration}: "
                        f"POS={n_pos}, NEG={n_neg}, NOISE={n}"
                    )
                    continue

                print(f"\n=== Iteration {iteration} | POS={n_pos}, NEG={n_neg}, N={n} ===")
                noise_token = noise_key
                task_stem = (
                    f"ilasp_task_iter_{iteration}_pos_{n_pos}_neg_{n_neg}_noise_{noise_token}"
                )
                base_task_file = os.path.join(train_dir, f"{task_stem}.las")
                task_file = next_available_path(base_task_file)

                model_stem = os.path.splitext(os.path.basename(task_file))[0]
                base_output_file = os.path.join(train_output_dir, f"{model_stem}.lp")
                output_file = next_available_path(base_output_file)

                if dry_run:
                    print(f"[DRY RUN] Would generate and run task: {task_file}")
                    continue

                run_seed = stable_seed_from_parts(
                    "task_sampling",
                    task_sampling_seed_base,
                    semantics,
                    partial,
                    iteration,
                    n_pos,
                    n_neg,
                    noise_key,
                )
                generate_ilasp_task(
                    n_pos,
                    n_neg,
                    n,
                    input_dir,
                    task_file,
                    negative_policy=negative_policy,
                    negative_flip_k=negative_flip_k,
                    semantics=semantics,
                    semantics_config_path=semantics_config_path,
                    allowed_examples_manifest=iter_manifest,
                    seed=run_seed,
                )
                train_files = extract_train_files(task_file)
                train_files, test_files, test_set_meta = get_train_test_sets(
                    input_dir=input_dir,
                    train_files=train_files,
                    # grouped_kfold reuses the fixed_balanced_holdout branch (which
                    # returns the supplied hold-out as the test set and enforces the
                    # train/test disjointness guard) but with the per-fold,
                    # AAF-disjoint hold-out built above.
                    test_set_policy=("fixed_balanced_holdout" if grouped_kfold else test_set_policy),
                    test_examples_per_class=effective_test_examples_per_class,
                    test_sampling_seed=test_sampling_seed,
                    semantics=semantics,
                    partial=partial,
                    iteration=iteration,
                    n_pos=n_pos,
                    n_neg=n_neg,
                    noise=n,
                    fixed_holdout_files=iter_holdout_files,
                )
                if grouped_kfold:
                    test_set_meta["test_set_policy"] = "grouped_kfold"
                synth_neg_legal = 0
                synth_neg_total = 0
                if negative_policy != "oracle_neg":
                    synth_neg_legal, synth_neg_total = count_oracle_legal_synthetic_negatives(
                        task_file=task_file,
                        semantics_file=ground_truth_runtime.semantics_file,
                        background_file=ground_truth_runtime.background_file,
                        clingo_args=list(ground_truth_runtime.clingo_args),
                        completion_rules=ground_truth_runtime.completion_rules,
                        show_predicates=list(ground_truth_runtime.show_predicates),
                        cache=oracle_legal_cache,
                    )
                    print(
                        f"[Synthetic-neg audit] oracle-legal={synth_neg_legal}/{synth_neg_total} "
                        f"for task {os.path.basename(task_file)}"
                    )

                (
                    train_runtime_seconds,
                    train_timed_out,
                    train_exit_code,
                    train_succeeded,
                    train_retries_used,
                ) = run_ilasp(
                    task_file,
                    output_file,
                    ilasp_args,
                    timeout_seconds=effective_train_timeout_seconds,
                    retry_on_exit_code_minus_11=effective_retry_on_exit_code_minus_11
                )
                learned_heuristic_rules = count_heuristic_directives(output_file)
                learned_has_heuristic = int(learned_heuristic_rules > 0)
                if learned_has_heuristic:
                    print(
                        f"[Heuristics] Learned {learned_heuristic_rules} heuristic directive(s) "
                        f"in {output_file}"
                    )

                correct = 0
                total = len(test_files)
                learned_test_times = []
                oracle_test_times = []
                any_test_timed_out = 0
                tp = 0
                fp = 0
                tn = 0
                fn = 0

                print(f"📄 Test set size: {total} files")

                if train_succeeded:
                    for tf in test_files:
                        test_path = os.path.join(input_dir, tf)
                        if eval_on_bare_aaf:
                            # Strip the test file's label atoms and compare on the
                            # BARE AAF. Required for grounded: grounded.lp is a
                            # definite program (no integrity constraints), so it can
                            # never reject an injected non-grounded labelling, which
                            # makes the labelled-instance comparison meaningless on
                            # negative instances. Comparing the computed unique
                            # extension on the bare AAF is the correct test.
                            bare_lines = [
                                ln.strip()
                                for ln in open(test_path, "r", encoding="utf-8")
                                if ln.strip().startswith(("arg(", "att("))
                            ]
                            test_path = os.path.join(train_dir, "_bare_eval_instance.lp")
                            with open(test_path, "w", encoding="utf-8") as bf:
                                bf.write("\n".join(bare_lines) + "\n")

                        start = time.perf_counter()
                        ilasp_models = run_learned_model_with_api(
                            output_file,
                            test_path,
                            learned_background_file,
                            clingo_args=learned_clingo_args,
                            completion_rules=learned_completion_rules,
                            show_predicates=learned_show_predicates,
                        )
                        ilasp_test_elapsed = time.perf_counter() - start
                        learned_test_times.append(ilasp_test_elapsed)
                        if ilasp_test_elapsed >= effective_test_par_timeout_seconds:
                            any_test_timed_out = 1

                        start = time.perf_counter()
                        gt_models = run_ground_truth_with_api(
                            asp_file,
                            test_path,
                            ground_truth_background_file,
                            clingo_args=ground_truth_clingo_args,
                            completion_rules=ground_truth_completion_rules,
                            show_predicates=ground_truth_show_predicates,
                        )
                        aspartix_elapsed = time.perf_counter() - start
                        oracle_test_times.append(aspartix_elapsed)
                        if aspartix_elapsed >= effective_test_par_timeout_seconds:
                            any_test_timed_out = 1

                        is_correct, add_tp, add_fp, add_tn, add_fn = evaluate_model_sets(
                            ilasp_models,
                            gt_models,
                            eval_match_policy,
                        )
                        if is_correct:
                            correct += 1
                        else:
                            print(f"[Mismatch] {tf}")
                        tp += add_tp
                        fp += add_fp
                        tn += add_tn
                        fn += add_fn
                else:
                    print(
                        f"[Warning] Skipping learned-model inference because ILASP failed "
                        f"(exit_code={train_exit_code}, timed_out={int(train_timed_out)})."
                    )
                    # Failed training => no learned model => NO generalization
                    # measurement. Do NOT score the NEG class as TN (audit defect
                    # #3, which pinned failed rows at a spurious 0.5 accuracy /
                    # 0.0 F1 floor). Leave tp=fp=tn=fn=correct=0; the row is flagged
                    # by ILASP_TRAIN_SUCCEEDED=0 and must be excluded from accuracy/
                    # F1 aggregation. Ground-truth solves are skipped (nothing to
                    # compare against), keeping failed cells cheap. No test solves ran,
                    # so test-timing columns stay empty (0) rather than a fabricated
                    # penalty; the failure is flagged by ILASP_TRAIN_SUCCEEDED=0 and
                    # ILASP_TRAIN_TIMED_OUT.
                    pass

                acc = correct / total if total > 0 else 0
                precision = safe_div(tp, tp + fp)
                recall = safe_div(tp, tp + fn)
                f1 = safe_div(2 * precision * recall, precision + recall)
                mcc = matthews_corrcoef(tp, fp, tn, fn)
                learned_total = sum(learned_test_times)
                learned_mean = safe_div(learned_total, len(learned_test_times))
                learned_max = max(learned_test_times) if learned_test_times else 0.0
                oracle_total = sum(oracle_test_times)
                oracle_mean = safe_div(oracle_total, len(oracle_test_times))
                oracle_max = max(oracle_test_times) if oracle_test_times else 0.0
                row = [
                    task_file,
                    n_pos,
                    n_neg,
                    n,
                    negative_policy,
                    negative_flip_k,
                    partial,
                    test_set_meta["test_set_policy"],
                    test_set_meta["test_set_target_per_class"],
                    test_set_meta["test_set_pos"],
                    test_set_meta["test_set_neg"],
                    total,
                    eval_match_policy,
                    train_runtime_seconds,
                    learned_total,
                    learned_mean,
                    learned_max,
                    oracle_total,
                    oracle_mean,
                    oracle_max,
                    any_test_timed_out,
                    int(train_timed_out),
                    int(train_succeeded),
                    train_exit_code if train_exit_code is not None else "",
                    train_retries_used,
                    effective_train_timeout_seconds,
                    effective_test_par_timeout_seconds,
                    output_file,
                    learned_heuristic_rules,
                    learned_has_heuristic,
                    synth_neg_total,
                    synth_neg_legal,
                    safe_div(synth_neg_legal, synth_neg_total),
                    safe_div(synth_neg_total - synth_neg_legal, synth_neg_total),
                    tp,
                    fp,
                    tn,
                    fn,
                    precision,
                    recall,
                    f1,
                    mcc,
                    acc,
                    run_seed,
                    iteration,
                ]
                append_result_row(results_file, row)
                completed_keys.add(combo_key)
                print(
                    f"✅ Appended result to {results_file} "
                    f"({len(completed_keys)}/{expected_rows_per_iteration} rows for iteration {iteration})"
                )

        final_rows = count_data_rows(results_file)
        print(
            f"✅ Iteration {iteration} done: {final_rows}/{expected_rows_per_iteration} rows in {results_file}"
        )

def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Run ILASP training/testing pipeline on labelled AAFs.",
        add_help=add_help,
    )
    parser.add_argument("--semantics", default="ADM", help="Semantics used (e.g. ADM, PRF)")
    parser.add_argument("--partial", type=float, default=0.3, help="Partial extension probability")
    parser.add_argument("--f_values", type=int, nargs="+", default=[5, 10], help="Positive example counts")
    parser.add_argument(
        "--f_neg_values",
        type=int,
        nargs="+",
        default=None,
        help="Negative example counts (optional; pairwise with --f_values). Default: same as --f_values."
    )
    parser.add_argument(
        "--negative_policy",
        choices=("oracle_neg", "flip_one", "flip_k", "full_relabel", "rn_hardmix", "nce_sample", "reliable_negative"),
        default="oracle_neg",
        help="Negative generation policy for ILASP task construction."
    )
    parser.add_argument(
        "--negative_flip_k",
        type=int,
        default=1,
        help="Number of label flips when --negative_policy=flip_k (ignored otherwise)."
    )
    parser.add_argument("--n_values", type=float, nargs="+", default=[0.0, 0.1], help="Noise levels")
    parser.add_argument("--iterations", type=int, default=3, help="How many times to repeat experiment")

    parser.add_argument("--base_output_dir", default="labelled", help="Top-level input dir for labelled AAFs")
    parser.add_argument("--train_dir", default="train", help="Directory to store ILASP task files")
    parser.add_argument("--train_output_dir", default="train_output", help="Directory for ILASP learned hypotheses")
    parser.add_argument("--results_dir", default="results", help="Top-level directory to store results")
    parser.add_argument("--no_prefix", action="store_true", help="Do not append semantic/partial prefix to results_dir")
    parser.add_argument(
        "--train_timeout_seconds",
        type=int,
        default=None,
        help="ILASP train timeout in seconds. Default: ilasp_config global value or 1200."
    )
    parser.add_argument(
        "--test_par_timeout_seconds",
        type=int,
        default=None,
        help="PAR-2 threshold (seconds) for test/inference metrics. Default: ilasp_config global value or 1200."
    )
    parser.add_argument(
        "--par2_factor",
        type=float,
        default=None,
        help="PAR-k penalty factor. Default: ilasp_config global value or 2."
    )
    parser.add_argument(
        "--overwrite_existing_iterations",
        action="store_true",
        help="Recompute iterations even if complete results_<iteration>.csv files already exist."
    )
    parser.add_argument(
        "--ilasp_config",
        default="ilasp_config.json",
        help="Path to ILASP config JSON (default: ilasp_config.json)."
    )
    parser.add_argument(
        "--semantics_config",
        default="semantics_config.json",
        help="Path to semantics config JSON (default: semantics_config.json)."
    )
    parser.add_argument(
        "--test_set_policy",
        choices=("grouped_kfold", "fixed_balanced_holdout", "balanced_remaining", "all_remaining"),
        default="fixed_balanced_holdout",
        help=(
            "Testing policy. 'grouped_kfold' (recommended) runs K group-disjoint CV folds over "
            "source-AAFs (K = --iterations): train and test never share a source-AAF, removing "
            "AAF-level leakage, and the K folds give honest generalization CIs. "
            "'fixed_balanced_holdout' reserves one deterministic, class-balanced hold-out pool per "
            "labelled dataset and samples training only from the complement (note: file-level "
            "disjoint but NOT AAF-disjoint -> leaks); 'balanced_remaining' preserves the earlier "
            "balanced-on-remainder behavior; 'all_remaining' preserves the legacy behavior."
        )
    )
    parser.add_argument(
        "--test_examples_per_class",
        type=int,
        default=None,
        help=(
            "Balanced test examples per class. Default: auto-compute the largest per-class size "
            "feasible after accounting for the largest requested training set in the current run."
        )
    )
    parser.add_argument(
        "--test_sampling_seed",
        type=int,
        default=0,
        help="Deterministic seed used to sample the balanced held-out test pool."
    )
    parser.add_argument(
        "--task_sampling_seed_base",
        type=int,
        default=0,
        help="Deterministic base seed used to derive per-task ILASP sampling seeds.",
    )
    parser.add_argument(
        "--eval_match_policy",
        choices=("full_exact_model", "existential_acceptance"),
        default=DEFAULT_EVAL_MATCH_POLICY,
        help=(
            "How correctness and TP/FP/TN/FN are defined. "
            "'full_exact_model' requires exact learned-vs-ground-truth model-set agreement; "
            "'existential_acceptance' preserves the legacy satisfiability-based confusion logic."
        )
    )
    parser.add_argument("--dry_run", action="store_true", help="Don't run training/testing, just print planned steps.")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    run_experiment(
        semantics=args.semantics,
        partial=args.partial,
        f_values=args.f_values,
        f_neg_values=args.f_neg_values,
        n_values=args.n_values,
        iterations=args.iterations,
        base_output_dir=args.base_output_dir,
        train_dir=args.train_dir,
        train_output_dir=args.train_output_dir,
        results_dir=args.results_dir,
        no_prefix=args.no_prefix,
        dry_run=args.dry_run,
        train_timeout_seconds=args.train_timeout_seconds,
        test_par_timeout_seconds=args.test_par_timeout_seconds,
        par2_factor=args.par2_factor,
        overwrite_existing_iterations=args.overwrite_existing_iterations,
        negative_policy=args.negative_policy,
        negative_flip_k=args.negative_flip_k,
        test_set_policy=args.test_set_policy,
        test_examples_per_class=args.test_examples_per_class,
        test_sampling_seed=args.test_sampling_seed,
        eval_match_policy=args.eval_match_policy,
        ilasp_config_path=args.ilasp_config,
        semantics_config_path=args.semantics_config,
        task_sampling_seed_base=args.task_sampling_seed_base,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
