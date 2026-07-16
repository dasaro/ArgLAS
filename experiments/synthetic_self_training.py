#!/usr/bin/env python3
"""Self-training (iterative PU) negative-generation strategy, benchmarked on
synthetic ground truth. Seeds with reliable_negative (far-from-positive) negatives,
learns a theory, then GROWS the negative set with fresh candidates the current
theory confidently rejects, and re-learns. Oracle-free during learning (the learner
is its own evolving filter); the known-semantics oracle is used ONLY to score
recovery + the wrong-negative rate. Reuses the corrected grouped-K-fold split + eval
so results are comparable to the other policies. ADM/CMP/STB only (no heuristics)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")))
import argparse, os, glob, random, tempfile, csv

from arglas.artifact_paths import resolve_repo_path, resolve_artifact_path
from arglas.generate_ilasp_task import build_synthetic_negative, build_ilasp_directive, render_label_facts
from arglas.train_test import (
    build_grouped_folds, build_grouped_balanced_test, build_grouped_train_manifest,
    aaf_group_id, run_ilasp, run_learned_model_with_api, run_ground_truth_with_api,
    evaluate_model_sets, canonical_model_set, safe_div,
    stable_seed_from_parts,
)
from arglas.generate_ilasp_task import parse_lp_instance
from arglas.solver_policy import (
    load_semantics_config, get_semantics_entry, get_clingo_args, get_background_file,
    get_completion_rules_enabled, get_show_predicates,
)
from arglas.ilasp_policy import resolve_ilasp_args

BG = resolve_repo_path("config/background_knowledge.lp")
MODES = resolve_repo_path("config/mode_declarations.las")


def write_task(path, examples, deterministic=True):
    lines = [build_ilasp_directive(eid, lf, af, isp, 0.0, deterministic, 100)[0] for (eid, lf, af, isp) in examples]
    body = open(BG).read() + "\n" + open(MODES).read()
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n" + body + "\n")


def in_set(labels):
    return frozenset(f"in({a})" for a, s in labels.items() if s == "in")


def model_insets(model_path, af_facts, bg, comp, show):
    tf = tempfile.NamedTemporaryFile("w", suffix=".lp", delete=False)
    tf.write("\n".join(af_facts) + "\n"); tf.close()
    try:
        models = run_learned_model_with_api(model_path, tf.name, bg, clingo_args=[], completion_rules=comp, show_predicates=show)
    finally:
        os.unlink(tf.name)
    return {frozenset(a for a in m if a.startswith("in(")) for m in models}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semantics", required=True)
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--asp_file", required=True)
    ap.add_argument("--results_csv", required=True)
    ap.add_argument("--n_pos", type=int, default=30)
    ap.add_argument("--n_neg", type=int, default=30)
    ap.add_argument("--K", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--fold_seed", type=int, default=20260312)
    ap.add_argument("--test_per_class", type=int, default=50)
    ap.add_argument("--train_timeout", type=int, default=120)
    args = ap.parse_args()

    cfg = load_semantics_config(resolve_repo_path("config/semantics_config.json"))
    asp = resolve_repo_path(args.asp_file)
    bg = resolve_repo_path(get_background_file(cfg, stage="train_test_learned"))
    lcomp = get_completion_rules_enabled(cfg, "train_test_learned", semantics=args.semantics)
    gcomp = get_completion_rules_enabled(cfg, "train_test_ground_truth", semantics=args.semantics)
    lshow = get_show_predicates(cfg, "train_test_learned"); gshow = get_show_predicates(cfg, "train_test_ground_truth")
    largs = get_clingo_args(cfg, args.semantics, "train_test_learned"); gargs = get_clingo_args(cfg, args.semantics, "train_test_ground_truth")
    ilasp_args = resolve_ilasp_args(semantics=args.semantics)

    folds = build_grouped_folds(args.input_dir, args.K, fold_seed=args.fold_seed)
    all_files = [f for f in os.listdir(args.input_dir) if f.endswith(".lp")]
    pos_by_aaf = {}
    for f in all_files:
        if "_POS_" in f:
            pos_by_aaf.setdefault(aaf_group_id(f), []).append(f)

    rows = []
    for fi, (train_aafs, test_aafs) in enumerate(folds, 1):
        rng = random.Random(stable_seed_from_parts("selftrain", args.fold_seed, args.semantics, fi))
        train_pos = sorted(f for f in all_files if "_POS_" in f and aaf_group_id(f) in train_aafs)
        if len(train_pos) < args.n_pos:
            continue
        sampled_pos = rng.sample(train_pos, args.n_pos)
        parsed = {f: parse_lp_instance(os.path.join(args.input_dir, f)) for f in train_pos}
        # global accept marginal for reliable_negative's internal randomness is 0.5; fine.
        pos_examples = []
        for pf in sampled_pos:
            af, labels = parsed[pf]
            pos_examples.append((pf.replace(".lp", ""), render_label_facts(labels), af, True))

        def make_reliable_negs(sources, k):
            negs = []
            for sf in sources:
                af, labels = parsed[sf]
                mut = build_synthetic_negative(labels, "reliable_negative", p_in=0.5, n_candidates=8)
                if mut:
                    negs.append((sf, af, mut))
                if len(negs) >= k:
                    break
            return negs

        # Round 0: seed reliable negatives
        seed_sources = rng.sample(train_pos, min(len(train_pos), args.n_neg * 3))
        seed = make_reliable_negs(seed_sources, args.n_neg)
        cur_negs = seed
        model_path = None
        for r in range(args.rounds):
            negs_examples = [(f"{sf.replace('.lp','')}_SNEG_{i+1}", render_label_facts(m), af, False)
                             for i, (sf, af, m) in enumerate(cur_negs)]
            task = f"/tmp/selftrain_{args.semantics}_f{fi}_r{r}.las"
            model_path = f"/tmp/selftrain_{args.semantics}_f{fi}_r{r}.lp"
            write_task(task, pos_examples + negs_examples)
            res = run_ilasp(task, model_path, ilasp_args, timeout_seconds=args.train_timeout, retry_on_exit_code_minus_11=1)
            succeeded = res[3]
            if not succeeded or r == args.rounds - 1:
                break
            # Self-training step: keep fresh candidates the current theory REJECTS (confident negs), grow the set
            cand_sources = rng.sample(train_pos, min(len(train_pos), args.n_neg * 4))
            fresh = make_reliable_negs(cand_sources, args.n_neg * 2)
            kept = []
            for (sf, af, m) in fresh:
                ins = model_insets(model_path, af, bg, lcomp, lshow)
                if in_set(m) not in ins:          # theory rejects it -> confident negative
                    kept.append((sf, af, m))
                if len(kept) >= args.n_neg:
                    break
            # accumulate seed + confident negatives (cap ~2x)
            cur_negs = (seed + kept)[: 2 * args.n_neg] if kept else seed

        # wrong-negative rate of the FINAL negative set (oracle-measured)
        legal = 0
        for (sf, af, m) in cur_negs:
            oins = model_insets_oracle(asp, af, gargs, gcomp, gshow)
            if in_set(m) in oins:
                legal += 1
        wrong_rate = legal / len(cur_negs) if cur_negs else 0.0

        # Evaluate final model vs oracle on the fold's balanced test set (pipeline-style)
        if model_path and os.path.exists(model_path) and succeeded:
            holdout = build_grouped_balanced_test(args.input_dir, test_aafs, args.test_per_class, args.fold_seed, fi)
            tp = fp = tn = fn = correct = 0
            for tf in holdout:
                tp_ = os.path.join(args.input_dir, tf)
                lm = run_learned_model_with_api(model_path, tp_, bg, clingo_args=largs, completion_rules=lcomp, show_predicates=lshow)
                gm = run_ground_truth_with_api(asp, tp_, None, clingo_args=gargs, completion_rules=gcomp, show_predicates=gshow)
                ok, a, b, c, d = evaluate_model_sets(lm, gm, "full_exact_model")
                correct += ok; tp += a; fp += b; tn += c; fn += d
            n = len(holdout)
            acc = correct / n if n else 0.0
            prec = safe_div(tp, tp + fp); rec = safe_div(tp, tp + fn); f1 = safe_div(2 * prec * rec, prec + rec)
            rows.append(dict(SEM=args.semantics, FOLD=fi, SUCC=int(succeeded), ACC=acc, F1=f1,
                             TP=tp, FP=fp, TN=tn, FN=fn, WRONG_NEG_RATE=wrong_rate))
        else:
            rows.append(dict(SEM=args.semantics, FOLD=fi, SUCC=0, ACC=0.0, F1=0.0, TP=0, FP=0, TN=0, FN=0, WRONG_NEG_RATE=wrong_rate))
        print(f"[selftrain] {args.semantics} fold {fi}: succ={rows[-1]['SUCC']} acc={rows[-1]['ACC']:.3f} F1={rows[-1]['F1']:.3f} wrong_neg={wrong_rate:.3f}")

    os.makedirs(os.path.dirname(args.results_csv), exist_ok=True)
    with open(args.results_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["SEM", "FOLD", "SUCC", "ACC", "F1", "TP", "FP", "TN", "FN", "WRONG_NEG_RATE"])
        w.writeheader(); w.writerows(rows)
    print(f"[selftrain] wrote {len(rows)} rows to {args.results_csv}")


def model_insets_oracle(asp, af_facts, gargs, gcomp, gshow):
    tf = tempfile.NamedTemporaryFile("w", suffix=".lp", delete=False)
    tf.write("\n".join(af_facts) + "\n"); tf.close()
    try:
        models = run_ground_truth_with_api(asp, tf.name, None, clingo_args=gargs, completion_rules=gcomp, show_predicates=gshow)
    finally:
        os.unlink(tf.name)
    return {frozenset(a for a in m if a.startswith("in(")) for m in models}


if __name__ == "__main__":
    main()
