"""Route P1 lab: learn the ADM/CMP core with ILASP, evaluate PRF with the fixed
subset-maximal convention, grouped AAF-disjoint folds, balanced test.

Usage: python run_lab.py <variant:adm|cmp> <f:int> <fold_indices comma-sep>
"""
import json
import os
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention")
sys.path.insert(0, REPO)

import train_test as T  # noqa: E402
from generate_ilasp_task import parse_lp_instance, render_label_facts  # noqa: E402

PREFERRED_LP = os.path.join(REPO, "ASPARTIX", "preferred.lp")
BG = os.path.join(REPO, "background_knowledge.lp")
MODES = os.path.join(REPO, "mode_declarations.las")
BG_CONV = os.path.join(LAB, "bg_learned_prf.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]
K_FOLDS = 5
TEST_PER_CLASS = 30
FOLD_SEED = 0
ILASP_TIMEOUT = 600
BARE_RECOVERY_AAFS = 25


def build_task(pool_dir, train_aafs, f, seed_parts, task_file):
    train_set = set(train_aafs)
    pos = sorted(x for x in os.listdir(pool_dir)
                 if "_POS_" in x and T.aaf_group_id(x) in train_set)
    neg = sorted(x for x in os.listdir(pool_dir)
                 if "_NEG_" in x and T.aaf_group_id(x) in train_set)
    sel_pos = T.stable_sample(pos, f, seed_parts + ["POS"])
    sel_neg = T.stable_sample(neg, f, seed_parts + ["NEG"])
    lines = []
    for kind, files in [("#pos", sel_pos), ("#neg", sel_neg)]:
        for fname in files:
            af_facts, labels = parse_lp_instance(os.path.join(pool_dir, fname))
            label_str = ", ".join(render_label_facts(labels))
            af_str = " ".join(af_facts)
            ex_id = fname.replace(".lp", "") + "T"
            lines.append(f"{kind}({ex_id}, {{{label_str}}}, {{}}, {{{af_str}}}).")
    with open(task_file, "w") as fh:
        fh.write("\n".join(lines) + "\n")
        fh.write(open(BG).read() + "\n")
        fh.write(open(MODES).read() + "\n")
    return sel_pos, sel_neg


def eval_fold(model_file, pool_dir, test_files):
    tp = fp = tn = fn = 0
    mism = []
    for tfile in test_files:
        path = os.path.join(pool_dir, tfile)
        pred = T.run_learned_model_with_api(
            model_file, path, BG_CONV, clingo_args=DOMREC,
            completion_rules=True, show_predicates=["in/1"])
        gt = T.run_ground_truth_with_api(
            PREFERRED_LP, path, None, clingo_args=DOMREC,
            completion_rules=False, show_predicates=["in/1"])
        ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp += a; fp += b; tn += c; fn += d
        if not ok:
            mism.append(tfile)
    return tp, fp, tn, fn, mism


def bare_recovery(model_file, pool_dir, test_aafs, workdir):
    """On held-out BARE AAFs: does [learned + convention] enumerate EXACTLY the
    preferred in-sets? The strong (secondary) validation of maximality."""
    aaf_dir = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")
    chosen = sorted(test_aafs)[:BARE_RECOVERY_AAFS]
    exact = 0
    for (n, i) in chosen:
        path = os.path.join(aaf_dir, f"aaf_{n}_{i}.lp")
        pred = T.run_learned_model_with_api(
            model_file, path, BG_CONV, clingo_args=DOMREC,
            completion_rules=True, show_predicates=["in/1"])
        gt = T.run_ground_truth_with_api(
            PREFERRED_LP, path, None, clingo_args=DOMREC,
            completion_rules=False, show_predicates=["in/1"])
        if T.canonical_model_set(pred) == T.canonical_model_set(gt):
            exact += 1
    return exact, len(chosen)


def main():
    variant, f, fold_idxs = sys.argv[1], int(sys.argv[2]), [
        int(x) for x in sys.argv[3].split(",")]
    pool_dir = os.path.join(LAB, f"pool_{variant}", "labelled_PRF_full")
    outdir = os.path.join(LAB, "runs")
    os.makedirs(outdir, exist_ok=True)
    folds = T.build_grouped_folds(pool_dir, K_FOLDS, fold_seed=FOLD_SEED)

    results = []
    for j in fold_idxs:
        train_aafs, test_aafs = folds[j]
        tag = f"{variant}_f{f}_fold{j}"
        task_file = os.path.join(outdir, f"task_{tag}.las")
        model_file = os.path.join(outdir, f"model_{tag}.lp")
        build_task(pool_dir, train_aafs, f,
                   ["p1_prf", variant, f, j], task_file)
        elapsed, timed_out, exit_code, succeeded, retries = T.run_ilasp(
            task_file, model_file, [], timeout_seconds=ILASP_TIMEOUT,
            retry_on_exit_code_minus_11=1)
        row = {"tag": tag, "train_seconds": round(elapsed, 2),
               "timed_out": timed_out, "exit_code": exit_code,
               "succeeded": succeeded}
        if succeeded:
            row["theory"] = open(model_file).read().strip().splitlines()
            test_files = T.build_grouped_balanced_test(
                pool_dir, test_aafs, TEST_PER_CLASS, FOLD_SEED, j)
            tp, fp, tn, fn, mism = eval_fold(model_file, pool_dir, test_files)
            row.update(tp=tp, fp=fp, tn=tn, fn=fn,
                       mcc=round(T.matthews_corrcoef(tp, fp, tn, fn), 4),
                       acc=round((tp + tn) / max(1, tp + fp + tn + fn), 4),
                       mismatches=mism[:8])
            ex, tot = bare_recovery(model_file, pool_dir, test_aafs, outdir)
            row["bare_aaf_exact_preferred_recovery"] = f"{ex}/{tot}"
        results.append(row)
        print(json.dumps(row))

    with open(os.path.join(outdir, f"results_{variant}_f{f}.json"), "a") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
