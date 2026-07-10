"""Route G1: GRD definite-core learning experiment.

Variants:
  Va  no-choice background for LEARNING and for EVAL (bg_nochoice.lp:
      derived preds + ':- arg,in,out' but WITHOUT the 0{in}1/0{out}1 choice
      rules). The learned theory must DERIVE in/out.
  Vb  choice background (repo background_knowledge.lp) for LEARNING, but the
      same no-choice background at EVAL (the BG_PREDICT split).

Splits: train_test.build_grouped_folds over the campaign labelled_GRD_full
pool (source-AAF-disjoint), train examples sampled from fold-train files with
train_test.stable_sample, test = train_test.build_grouped_balanced_test
(50 POS + 50 NEG per fold).

Eval conventions (both faithful reuses of train_test functions):
  E1 "bare"  pipeline GRD convention (eval_on_bare_aaf): strip labels, learned
     side = eval_bg + learned rules + bare AAF, plain clingo, completion OFF,
     show in/1,out/1; gt side = ASPARTIX/grounded.lp on the same bare AAF;
     full_exact_model via train_test.evaluate_model_sets. gt is never empty
     here so only TP/FN are populated (MCC degenerate by construction).
  E2 "disc"  labelled-instance discrimination: learned side = eval_bg +
     learned rules + LABELLED test file (labels injected as facts; the bg
     constraint rejects clashes); gt side = grd_check_oracle.lp (accepts iff
     labels are a subset of the grounded labelling, then emits the full
     grounded labelling; UNSAT otherwise). full_exact_model. POS/NEG both
     meaningful -> real confusion matrix and MCC.
"""
import json
import os
import subprocess
import sys
import time

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
sys.path.insert(0, REPO)
os.chdir(REPO)

from arglas import train_test as T  # noqa: E402
from arglas.generate_ilasp_task import parse_lp_instance, render_label_facts  # noqa: E402

LAB = os.path.join(REPO, "analysis/grd_prf_lab/g1_definite_core")
POOL = os.path.join(
    REPO, "artifacts/final_synthetic_corrected_20260625/labelled/labelled_GRD_full"
)
GROUNDED_LP = os.path.join(REPO, "config/ASPARTIX/grounded.lp")
BG_CHOICE = os.path.join(REPO, "config/background_knowledge.lp")
BG_NOCHOICE = os.path.join(LAB, "bg_nochoice.lp")
GRD_CHECK = os.path.join(LAB, "grd_check_oracle.lp")
MODES = os.path.join(REPO, "config/mode_declarations.las")
SHOW = ["in/1", "out/1"]
ILASP_TIMEOUT = 600
ILASP_VERSION = os.environ.get("G1_ILASP_VERSION", "4")


def build_task(task_path, train_files, learn_bg_path):
    """Pipeline-faithful example encoding: #pos(<id>T, {labels}, {}, {af})."""
    lines = []
    for kind, fname in train_files:
        af_facts, labels = parse_lp_instance(os.path.join(POOL, fname))
        label_facts = render_label_facts(labels)
        ex_id = fname.replace(".lp", "") + "T"
        directive = "#pos" if kind == "pos" else "#neg"
        lines.append(
            f"{directive}({ex_id}, {{{', '.join(label_facts)}}}, {{}}, "
            f"{{{' '.join(af_facts)}}})."
        )
    with open(learn_bg_path) as f:
        bg = f.read()
    with open(MODES) as f:
        modes = f.read()
    with open(task_path, "w") as f:
        f.write("\n".join(lines) + "\n" + bg + "\n" + modes + "\n")


def run_ilasp(task_path, log_path):
    cmd = ["ILASP", f"--version={ILASP_VERSION}", "-d", task_path]
    start = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=ILASP_TIMEOUT
        )
        out = proc.stdout + proc.stderr
        rc = proc.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        rc, timed_out = None, True
    elapsed = time.perf_counter() - start
    with open(log_path, "w") as f:
        f.write(out)
    unsat = T._final_verdict_unsat(out)
    rules = [] if (timed_out or unsat) else T.extract_hypothesis_rules(out)
    return rules, elapsed, timed_out, unsat, rc


def write_model(model_path, rules):
    with open(model_path, "w") as f:
        if rules:
            f.write("\n".join(rules) + "\n")
        else:
            f.write("% empty hypothesis\n")


def bare_path_for(test_file):
    src = os.path.join(POOL, test_file)
    dst = os.path.join(LAB, "_bare_eval_instance.lp")
    bare = [
        ln.strip() for ln in open(src) if ln.strip().startswith(("arg(", "att("))
    ]
    with open(dst, "w") as f:
        f.write("\n".join(bare) + "\n")
    return dst


def evaluate(model_path, test_files, eval_bg_path):
    res = {}
    # ---- E1: pipeline bare-AAF convention -------------------------------
    tp = fp = tn = fn = 0
    correct = 0
    correct_nonempty = 0
    n_nonempty = 0
    for tf in test_files:
        bp = bare_path_for(tf)
        pred = T.run_learned_model_with_api(
            model_path, bp, eval_bg_path,
            clingo_args=[], completion_rules=False, show_predicates=SHOW,
        )
        gt = T.run_ground_truth_with_api(
            GROUNDED_LP, bp, None,
            clingo_args=[], completion_rules=False, show_predicates=SHOW,
        )
        ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp, fp, tn, fn = tp + a, fp + b, tn + c, fn + d
        correct += int(ok)
        if gt and any(gt[0]):
            n_nonempty += 1
            correct_nonempty += int(ok)
    res["E1_bare"] = {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "acc": correct / len(test_files),
        "acc_nonempty_grounded": (
            correct_nonempty / n_nonempty if n_nonempty else None
        ),
        "n_nonempty_grounded": n_nonempty,
        "mcc": T.matthews_corrcoef(tp, fp, tn, fn),
    }
    # ---- E2: labelled-instance discrimination ---------------------------
    tp = fp = tn = fn = 0
    for tf in test_files:
        lp = os.path.join(POOL, tf)
        pred = T.run_learned_model_with_api(
            model_path, lp, eval_bg_path,
            clingo_args=[], completion_rules=False, show_predicates=SHOW,
        )
        gt = T.run_ground_truth_with_api(
            GRD_CHECK, lp, None,
            clingo_args=[], completion_rules=False, show_predicates=SHOW,
        )
        ok, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp, fp, tn, fn = tp + a, fp + b, tn + c, fn + d
    res["E2_disc"] = {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "acc": (tp + tn) / len(test_files),
        "mcc": T.matthews_corrcoef(tp, fp, tn, fn),
    }
    return res


def main():
    folds = T.build_grouped_folds(POOL, 5, fold_seed=0)
    results = []
    plan = []
    for fold_idx in (1, 2, 3):
        for f in (10, 20):
            plan.append(("Va_nochoice", BG_NOCHOICE, fold_idx, f))
    plan.append(("Vb_choice_bgsplit", BG_CHOICE, 1, 20))
    plan.append(("Vb_choice_bgsplit", BG_CHOICE, 2, 20))

    for variant, learn_bg, fold_idx, f in plan:
        train_aafs, test_aafs = folds[fold_idx - 1]
        manifest = T.build_grouped_train_manifest(POOL, train_aafs)
        pos_files, neg_files = T.split_labelled_files_by_class(manifest)
        sel_pos = T.stable_sample(pos_files, f, ["g1", variant, fold_idx, f, "POS"])
        sel_neg = T.stable_sample(neg_files, f, ["g1", variant, fold_idx, f, "NEG"])
        train_files = [("pos", x) for x in sel_pos] + [("neg", x) for x in sel_neg]

        test_files = T.build_grouped_balanced_test(
            POOL, test_aafs, 50, fold_seed=0, fold_index=fold_idx
        )
        overlap = {g for g in map(T.aaf_group_id, [x for _, x in train_files])} & {
            g for g in map(T.aaf_group_id, test_files)
        }
        assert not overlap, f"AAF leakage: {overlap}"

        stem = f"{variant}_fold{fold_idx}_f{f}_v{ILASP_VERSION}"
        task = os.path.join(LAB, "tasks", stem + ".las")
        model = os.path.join(LAB, "models", stem + ".lp")
        log = os.path.join(LAB, "logs", stem + ".log")
        build_task(task, train_files, learn_bg)
        rules, elapsed, timed_out, unsat, rc = run_ilasp(task, log)
        write_model(model, rules)
        print(f"\n=== {stem}: ILASP {elapsed:.1f}s timed_out={timed_out} "
              f"unsat={unsat} rc={rc}")
        for r in rules:
            print("   ", r)
        entry = {
            "variant": variant, "fold": fold_idx, "f": f,
            "ilasp_seconds": round(elapsed, 2), "timed_out": timed_out,
            "unsat": unsat, "rc": rc, "rules": rules,
            "n_test": len(test_files),
        }
        if not timed_out and not unsat:
            entry["eval"] = evaluate(model, test_files, BG_NOCHOICE)
            for conv, ev in entry["eval"].items():
                print(f"    {conv}: {ev}")
        results.append(entry)
        with open(os.path.join(LAB, f"results_g1_v{ILASP_VERSION}.json"), "w") as f_:
            json.dump(results, f_, indent=2)

    print("\nDone. Results in results_g1.json")


if __name__ == "__main__":
    main()
