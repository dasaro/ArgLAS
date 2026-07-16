"""Fold and hold-out builders for the train/test harness.

Moved verbatim from arglas.train_test (which re-exports every name here, so
`from arglas.train_test import build_grouped_folds` etc. keep working).
"""
import hashlib
import os
import random
import re


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
