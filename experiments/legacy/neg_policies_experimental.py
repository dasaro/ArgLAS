"""Experimental negative-generation policies retired from the arglas core.

Moved here (2026-07-16) from arglas/generate_ilasp_task.py: the `nce_sample`
and `rn_hardmix` policies. Neither is used by any committed artifact — no
experiments/run_configs/ config, no data/ result, and not the AIJ paper (the
studied synthetic policies are flip_one / flip_k / full_relabel /
reliable_negative, plus oracle_neg). The Exp2 real-world pipeline has its own
independent implementations in Real_World_Examples/scripts/ and does not
import these.

Kept verbatim for provenance. To experiment with them, import these helpers
and wire them into a task builder (see arglas/generate_ilasp_task.py `run()`
for the surrounding sampling/rendering machinery they used to plug into).
"""
import random

from arglas.generate_ilasp_task import (
    build_synthetic_negative,
    count_flippable,
    labels_signature,
)


def nce_sample_negative(labels, p_in=0.5):
    """Noise-contrastive (word2vec-style) synthetic negative: relabel each
    argument INDEPENDENTLY from the global accept marginal p_in, deliberately
    breaking the joint structure of real extensions so the result is unlikely
    to be a valid labelling. Oracle-free.

    In the original CLI, p_in was estimated as the global P(in) over the
    sampled positives' labelled in/out arguments.
    """
    if not labels:
        return None
    mutated = dict(labels)
    for arg in mutated:
        mutated[arg] = "in" if random.random() < p_in else "out"
    return mutated


def estimate_p_in_marginal(parsed_positives):
    """Global accept marginal P(in) over labelled in/out arguments of the
    sampled positive examples — the noise distribution for nce_sample.
    `parsed_positives` is an iterable of label dicts ({arg: status})."""
    num = den = 0
    for labels in parsed_positives:
        for status in labels.values():
            if status in ("in", "out"):
                den += 1
                num += 1 if status == "in" else 0
    return (num / den) if den else 0.5


def rn_hardmix_negatives(
    get_parsed,
    eligible_pos,
    source_pool,
    n_neg,
    flip_k=1,
    rn_reliable_fraction=0.7,
    rn_candidates_per_source=3,
):
    """rn_hardmix: mine flip-mutation candidates from positive examples, take a
    reliable subset (many flips => far from the positive manifold) and fill the
    remaining slots with harder near-positive (single-flip) negatives.

    - get_parsed(filename) -> (af_facts, labels): the caller's parsed-example
      loader (cached, as in generate_ilasp_task.run).
    - eligible_pos: positive filenames with >= 1 flippable label.
    - source_pool: filenames to mine candidates from (the original CLI used
      choose_synthetic_sources(eligible_pos, selected_pos, max(n_neg, n_neg*3))).

    Returns a list of up to n_neg records
    {"src_file", "af_facts", "mutated_labels"} or raises RuntimeError when the
    budget cannot be met (mirroring the original CLI errors).
    """
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
                flip_k=k_value,
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
        raise RuntimeError("rn_hardmix could not generate any candidate negatives.")

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
        raise RuntimeError(
            f"rn_hardmix could only generate {len(selected_candidates)}/{n_neg} negatives."
        )
    return selected_candidates[:n_neg]
