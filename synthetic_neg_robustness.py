#!/usr/bin/env python3
"""Noise-augmented negative-strategy calibration. Injects PER-ARGUMENT positive
noise q (flip each in/out label w.p. q) into the TRAINING positives only -- modelling
noisy human judgements -- generates negatives from those noisy positives, learns, and
scores RECOVERY against the CLEAN known-semantics oracle on a CLEAN held-out fold.
Answers: which negative-generation strategy degrades least as positive-noise rises.
ADM/CMP/STB, noise-0 synthetic training (the q is the only noise), grouped K folds."""
import argparse, os, glob, random, csv, math

from artifact_paths import resolve_repo_path
from generate_ilasp_task import build_synthetic_negative, render_label_facts, parse_lp_instance
from synthetic_self_training import write_task, in_set, model_insets, model_insets_oracle
from train_test import (
    build_grouped_folds, build_grouped_balanced_test, aaf_group_id,
    run_ilasp, run_learned_model_with_api, run_ground_truth_with_api,
    evaluate_model_sets, safe_div, stable_seed_from_parts,
)
from solver_policy import (
    load_semantics_config, get_clingo_args, get_background_file,
    get_completion_rules_enabled, get_show_predicates,
)
from ilasp_policy import resolve_ilasp_args

SEM_ASP = {"ADM": "ASPARTIX/admissible.lp", "CMP": "ASPARTIX/complete.lp", "STB": "ASPARTIX/stable.lp"}
POLICIES = ["oracle_neg", "flip_one", "flip_k", "reliable_negative", "self_training"]


def corrupt(labels, q, rng):
    out = dict(labels)
    for a, s in list(out.items()):
        if s in ("in", "out") and rng.random() < q:
            out[a] = "out" if s == "in" else "in"
    return out


def mcc(tp, fp, tn, fn):
    d = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / d if d else 0.0


def run_cell(sem, q, policy, cfg, ctx, n_pos=30, n_neg=30, K=3, rounds=2, fold_seed=20260312, train_timeout=120, flip_k=2):
    input_dir, asp, bg, lcomp, gcomp, lshow, gshow, largs, gargs, ilasp_args = ctx
    folds = build_grouped_folds(input_dir, K, fold_seed=fold_seed)
    allf = [f for f in os.listdir(input_dir) if f.endswith(".lp")]
    out_rows = []
    for fi, (train_aafs, test_aafs) in enumerate(folds, 1):
        rng = random.Random(stable_seed_from_parts("robust", fold_seed, sem, q, policy, fi))
        random.seed(stable_seed_from_parts("robust_glob", fold_seed, sem, q, policy, fi))  # build_synthetic_negative uses global random
        train_pos = sorted(f for f in allf if "_POS_" in f and aaf_group_id(f) in train_aafs)
        train_neg = sorted(f for f in allf if "_NEG_" in f and aaf_group_id(f) in train_aafs)
        if len(train_pos) < n_pos:
            continue
        sampled_pos = rng.sample(train_pos, n_pos)
        parsed = {f: parse_lp_instance(os.path.join(input_dir, f)) for f in set(train_pos)}
        # corrupt the (training) positives once each
        noisy = {f: corrupt(parsed[f][1], q, rng) for f in sampled_pos}
        pos_ex = [(f.replace(".lp", ""), render_label_facts(noisy[f]), parsed[f][0], True) for f in sampled_pos]

        neg_recs = []  # (af_facts, labels)
        if policy == "oracle_neg":
            for nf in rng.sample(train_neg, min(n_neg, len(train_neg))):
                af, lab = parse_lp_instance(os.path.join(input_dir, nf))
                neg_recs.append((af, lab))
        elif policy in ("flip_one", "flip_k", "reliable_negative"):
            srcs = rng.sample(sampled_pos, min(n_neg, len(sampled_pos)))
            for sf in srcs:
                mut = build_synthetic_negative(noisy[sf], policy, flip_k=flip_k, p_in=0.5, n_candidates=8)
                if mut:
                    neg_recs.append((parsed[sf][0], mut))
        elif policy == "self_training":
            seed = []
            for sf in rng.sample(sampled_pos, min(n_neg, len(sampled_pos))):
                mut = build_synthetic_negative(noisy[sf], "reliable_negative", p_in=0.5, n_candidates=8)
                if mut:
                    seed.append((parsed[sf][0], mut))
            cur = seed
            model_path = None
            for r in range(rounds):
                neg_ex = [(f"n{i}_SNEG_1", render_label_facts(m), af, False) for i, (af, m) in enumerate(cur)]
                task = f"/tmp/robust_{sem}_{q}_st_f{fi}_r{r}.las"; model_path = task.replace(".las", ".lp")
                write_task(task, pos_ex + neg_ex, deterministic=False)
                res = run_ilasp(task, model_path, ilasp_args, timeout_seconds=train_timeout, retry_on_exit_code_minus_11=1)
                if not res[3] or r == rounds - 1:
                    break
                kept = []
                for sf in rng.sample(sampled_pos, len(sampled_pos)):
                    m = build_synthetic_negative(noisy[sf], "reliable_negative", p_in=0.5, n_candidates=8)
                    if not m:
                        continue
                    ins = model_insets(model_path, parsed[sf][0], bg, lcomp, lshow)
                    if in_set(m) not in ins:
                        kept.append((parsed[sf][0], m))
                    if len(kept) >= n_neg:
                        break
                cur = (seed + kept)[: 2 * n_neg] if kept else seed
            neg_recs = cur
            succeeded = bool(res[3])
            _eval_and_record(out_rows, sem, q, policy, fi, model_path, succeeded, neg_recs, test_aafs, ctx, fold_seed)
            continue

        # non-self_training: build + learn once
        neg_ex = [(f"n{i}_SNEG_1", render_label_facts(lab), af, False) for i, (af, lab) in enumerate(neg_recs)]
        task = f"/tmp/robust_{sem}_{q}_{policy}_f{fi}.las"; model_path = task.replace(".las", ".lp")
        write_task(task, pos_ex + neg_ex, deterministic=False)
        res = run_ilasp(task, model_path, ilasp_args, timeout_seconds=train_timeout, retry_on_exit_code_minus_11=1)
        _eval_and_record(out_rows, sem, q, policy, fi, model_path, bool(res[3]), neg_recs, test_aafs, ctx, fold_seed)
    return out_rows


def _eval_and_record(out_rows, sem, q, policy, fi, model_path, succeeded, neg_recs, test_aafs, ctx, fold_seed):
    input_dir, asp, bg, lcomp, gcomp, lshow, gshow, largs, gargs, ilasp_args = ctx
    # wrong-negative rate (oracle-measured) of the generated negatives
    legal = 0
    for (af, lab) in neg_recs:
        if in_set(lab) in model_insets_oracle(asp, af, gargs, gcomp, gshow):
            legal += 1
    wnr = legal / len(neg_recs) if neg_recs else 0.0
    if succeeded and model_path and os.path.exists(model_path):
        holdout = build_grouped_balanced_test(input_dir, test_aafs, 50, fold_seed, fi)
        tp = fp = tn = fn = correct = 0
        for tf in holdout:
            tpath = os.path.join(input_dir, tf)
            lm = run_learned_model_with_api(model_path, tpath, bg, clingo_args=largs, completion_rules=lcomp, show_predicates=lshow)
            gm = run_ground_truth_with_api(asp, tpath, None, clingo_args=gargs, completion_rules=gcomp, show_predicates=gshow)
            ok, a, b, c, d = evaluate_model_sets(lm, gm, "full_exact_model")
            correct += ok; tp += a; fp += b; tn += c; fn += d
        n = len(holdout); acc = correct / n if n else 0.0
        prec = safe_div(tp, tp + fp); rec = safe_div(tp, tp + fn); f1 = safe_div(2 * prec * rec, prec + rec)
        out_rows.append(dict(SEM=sem, Q=q, POLICY=policy, FOLD=fi, SUCC=1, ACC=acc, F1=f1, MCC=mcc(tp, fp, tn, fn), WRONG_NEG=wnr))
    else:
        out_rows.append(dict(SEM=sem, Q=q, POLICY=policy, FOLD=fi, SUCC=0, ACC=0.0, F1=0.0, MCC=0.0, WRONG_NEG=wnr))
    r = out_rows[-1]
    print(f"[robust] {sem} q={q} {policy} fold{fi}: succ={r['SUCC']} acc={r['ACC']:.3f} F1={r['F1']:.3f} wrongNeg={wnr:.3f}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labelled_root", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--q_values", default="0.0,0.1,0.2")
    ap.add_argument("--K", type=int, default=3)
    ap.add_argument("--train_timeout", type=int, default=120)
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--n_pos", type=int, default=30)
    ap.add_argument("--n_neg", type=int, default=30)
    ap.add_argument("--semantics", default="ADM,CMP,STB")
    args = ap.parse_args()
    pols = [p.strip() for p in args.policies.split(",") if p.strip()]
    sems = [s.strip() for s in args.semantics.split(",") if s.strip()]
    cfg = load_semantics_config(resolve_repo_path("semantics_config.json"))
    qs = [float(x) for x in args.q_values.split(",")]
    rows = []
    for sem in sems:
        asp = resolve_repo_path(SEM_ASP[sem])
        bg = resolve_repo_path(get_background_file(cfg, stage="train_test_learned"))
        ctx = (
            os.path.join(args.labelled_root, f"labelled_{sem}_full"), asp, bg,
            get_completion_rules_enabled(cfg, "train_test_learned", semantics=sem),
            get_completion_rules_enabled(cfg, "train_test_ground_truth", semantics=sem),
            get_show_predicates(cfg, "train_test_learned"), get_show_predicates(cfg, "train_test_ground_truth"),
            get_clingo_args(cfg, sem, "train_test_learned"), get_clingo_args(cfg, sem, "train_test_ground_truth"),
            resolve_ilasp_args(semantics=sem),
        )
        for q in qs:
            for policy in pols:
                rows += run_cell(sem, q, policy, cfg, ctx, n_pos=args.n_pos, n_neg=args.n_neg, K=args.K, train_timeout=args.train_timeout)
    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["SEM", "Q", "POLICY", "FOLD", "SUCC", "ACC", "F1", "MCC", "WRONG_NEG"])
        w.writeheader(); w.writerows(rows)
    print(f"[robust] wrote {len(rows)} rows to {args.out_csv}")


if __name__ == "__main__":
    main()
