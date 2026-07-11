"""Route P1, variant B+: complete-core pool, ILASP task background ALSO carries
the completion rules (training convention == eval convention), plus:
  - empty-extension positives for 7 of the 14 incoherent AAFs, encoded as
    #pos(id, {}, {in(a) for every arg a}, {AAF}) -- expressible only because the
    task background is total (completion);
  - the (rare) non-total preferred-labelling positives force completeness over
    the stable shortcut at training time.
Extra metrics: bare-AAF exact preferred recovery on the 7 HELD-OUT incoherent
AAFs and on the 2 non-total POS instances (when not in the fold's train side).

Usage: python run_lab2.py <f:int> <fold_indices comma-sep>
"""
import json
import os
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention")
sys.path.insert(0, REPO)

from arglas import train_test as T  # noqa: E402
from arglas.generate_ilasp_task import parse_lp_instance, render_label_facts  # noqa: E402

PREFERRED_LP = os.path.join(REPO, "config", "ASPARTIX", "preferred.lp")
BG = os.path.join(REPO, "config/background_knowledge.lp")
MODES = os.path.join(REPO, "config/mode_declarations.las")
BG_CONV = os.path.join(LAB, "bg_learned_prf.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]
K_FOLDS = 5
TEST_PER_CLASS = 30
FOLD_SEED = 0
ILASP_TIMEOUT = 600
COMPLETION = "in(X) :- arg(X), not out(X).\nout(X) :- arg(X), not in(X).\n"
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")

INCOH = ["aaf_5_16.lp", "aaf_5_35.lp", "aaf_5_42.lp", "aaf_6_14.lp",
         "aaf_6_91.lp", "aaf_7_10.lp", "aaf_7_15.lp", "aaf_7_52.lp",
         "aaf_7_59.lp", "aaf_7_67.lp", "aaf_7_75.lp", "aaf_8_42.lp",
         "aaf_8_78.lp", "aaf_8_90.lp"]
INCOH_TRAIN, INCOH_HELD = INCOH[:7], INCOH[7:]
NONTOTAL_POS = ["aaf_8_82_PRF_POS_1.lp", "aaf_8_87_PRF_POS_1.lp"]


def empty_pos_directive(aaf_file):
    facts = [ln.strip() for ln in open(os.path.join(AAF_DIR, aaf_file))
             if ln.strip().startswith(("arg(", "att("))]
    args = [f[4:-2] for f in facts if f.startswith("arg(")]
    excl = ", ".join(f"in({a})" for a in args)
    ex_id = aaf_file.replace(".lp", "") + "_EMPTYPOS_T"
    return f"#pos({ex_id}, {{}}, {{{excl}}}, {{{' '.join(facts)}}})."


def build_task(pool_dir, train_aafs, f, seed_parts, task_file):
    train_set = set(train_aafs)
    pos = sorted(x for x in os.listdir(pool_dir)
                 if "_POS_" in x and T.aaf_group_id(x) in train_set)
    neg = sorted(x for x in os.listdir(pool_dir)
                 if "_NEG_" in x and T.aaf_group_id(x) in train_set)
    sel_pos = T.stable_sample(pos, f, seed_parts + ["POS"])
    sel_neg = T.stable_sample(neg, f, seed_parts + ["NEG"])
    # force-include non-total positives when their AAF is on the train side
    forced = [x for x in NONTOTAL_POS
              if T.aaf_group_id(x) in train_set and x not in sel_pos]
    lines = []
    for kind, files in [("#pos", sel_pos + forced), ("#neg", sel_neg)]:
        for fname in files:
            af_facts, labels = parse_lp_instance(os.path.join(pool_dir, fname))
            label_str = ", ".join(render_label_facts(labels))
            af_str = " ".join(af_facts)
            ex_id = fname.replace(".lp", "") + "T"
            lines.append(f"{kind}({ex_id}, {{{label_str}}}, {{}}, {{{af_str}}}).")
    for aaf_file in INCOH_TRAIN:
        lines.append(empty_pos_directive(aaf_file))
    with open(task_file, "w") as fh:
        fh.write("\n".join(lines) + "\n")
        fh.write(open(BG).read() + "\n")
        fh.write(COMPLETION + "\n")
        fh.write(open(MODES).read() + "\n")
    return forced


def solve_pair(model_file, path):
    pred = T.run_learned_model_with_api(
        model_file, path, BG_CONV, clingo_args=DOMREC,
        completion_rules=True, show_predicates=["in/1"])
    gt = T.run_ground_truth_with_api(
        PREFERRED_LP, path, None, clingo_args=DOMREC,
        completion_rules=False, show_predicates=["in/1"])
    return pred, gt


def main():
    f, fold_idxs = int(sys.argv[1]), [int(x) for x in sys.argv[2].split(",")]
    pool_dir = os.path.join(LAB, "pool_cmp", "labelled_PRF_full")
    outdir = os.path.join(LAB, "runs")
    folds = T.build_grouped_folds(pool_dir, K_FOLDS, fold_seed=FOLD_SEED)

    for j in fold_idxs:
        train_aafs, test_aafs = folds[j]
        tag = f"cmpc_f{f}_fold{j}"
        task_file = os.path.join(outdir, f"task_{tag}.las")
        model_file = os.path.join(outdir, f"model_{tag}.lp")
        forced = build_task(pool_dir, train_aafs, f,
                            ["p1_prf", "cmpc", f, j], task_file)
        elapsed, timed_out, exit_code, succeeded, retries = T.run_ilasp(
            task_file, model_file, [], timeout_seconds=ILASP_TIMEOUT,
            retry_on_exit_code_minus_11=1)
        row = {"tag": tag, "train_seconds": round(elapsed, 2),
               "timed_out": timed_out, "exit_code": exit_code,
               "succeeded": succeeded, "forced_nontotal_pos": forced}
        if succeeded:
            row["theory"] = open(model_file).read().strip().splitlines()
            test_files = T.build_grouped_balanced_test(
                pool_dir, test_aafs, TEST_PER_CLASS, FOLD_SEED, j)
            tp = fp = tn = fn = 0
            mism = []
            for tfile in test_files:
                pred, gt = solve_pair(model_file, os.path.join(pool_dir, tfile))
                ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
                tp += a; fp += b; tn += c; fn += d
                if not ok:
                    mism.append(tfile)
            row.update(tp=tp, fp=fp, tn=tn, fn=fn,
                       mcc=round(T.matthews_corrcoef(tp, fp, tn, fn), 4),
                       mismatches=mism[:8])
            # bare-AAF preferred recovery on held-out fold AAFs
            exact = tot = 0
            for (n, i) in sorted(test_aafs)[:25]:
                pred, gt = solve_pair(
                    model_file, os.path.join(AAF_DIR, f"aaf_{n}_{i}.lp"))
                tot += 1
                exact += int(T.canonical_model_set(pred) ==
                             T.canonical_model_set(gt))
            row["bare_aaf_exact_preferred_recovery"] = f"{exact}/{tot}"
            # held-out INCOHERENT AAFs (never trained on)
            exact = 0
            for aaf_file in INCOH_HELD:
                pred, gt = solve_pair(model_file, os.path.join(AAF_DIR, aaf_file))
                exact += int(T.canonical_model_set(pred) ==
                             T.canonical_model_set(gt))
            row["incoherent_heldout_exact"] = f"{exact}/{len(INCOH_HELD)}"
            # non-total POS instances, only when on the fold's TEST side
            nt = []
            for x in NONTOTAL_POS:
                if T.aaf_group_id(x) in set(test_aafs):
                    pred, gt = solve_pair(model_file, os.path.join(pool_dir, x))
                    ok, *_ = T.evaluate_model_sets(pred, gt, "full_exact_model")
                    nt.append((x, bool(ok)))
            row["nontotal_pos_test"] = nt
        print(json.dumps(row))
        with open(os.path.join(outdir, f"results_cmpc_f{f}.json"), "a") as fh:
            fh.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
