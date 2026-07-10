"""End-to-end integration run: GRD (route G1) + PRF (route P1) through the REAL
train_test.run_experiment, exactly as the campaign would run it.

Everything is expressed through the real pipeline's own knobs (variant
semantics_config / ilasp_config copies, pool dirs) EXCEPT one thing that the
pipeline cannot express today and that is patched here as a documented shim:

  SHIM (GRD only): generate_ilasp_task.py line ~668 hardcodes
  background_knowledge.lp (WITH the 0{in(X)}1 / 0{out(X)}1 choice rules) into
  every ILASP task. Route G1 requires the task background WITHOUT the choice
  rules (the hypothesis must DERIVE in/out; with choice rules every labelling
  is an answer set and only constraint theories are learnable -> the historic
  GRD acc~0.14/UNSAT failure). The shim wraps train_test.generate_ilasp_task:
  it calls the ORIGINAL (unmodified subprocess to generate_ilasp_task.py) and
  then deletes the two choice-rule lines from the generated .las file. The
  matching repo patch is a per-semantics 'learn_background_file' option in
  generate_ilasp_task.py / semantics_config.json (documented in README).

  NOT a shim: GRD's ILASP --version=2i is injected via ilasp_config_grdprf.json
  GRD.ilasp_args (run_ilasp appends them after its hardcoded --version=4 and
  ILASP takes the LAST --version flag -- verified on the v4-spurious-UNSAT
  task). The clean repo patch makes the version first-class.

Run config (as instructed): grouped_kfold K=5 (one row per fold per f),
test_examples_per_class=50, f_values 10 20, p_partial=1.0, noise 0.0,
oracle_neg negatives, full_exact_model, ILASP timeout 600s.

Usage: python run_integration.py [GRD|PRF|both]
"""
import os
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
INTEG = os.path.join(REPO, "analysis/grd_prf_lab/integration")
sys.path.insert(0, REPO)
os.chdir(REPO)

from arglas import train_test as T  # noqa: E402

CHOICE_LINES = {"0{ in(X) }1 :- arg(X).", "0{ out(X) }1 :- arg(X)."}

_ORIG_GENERATE = T.generate_ilasp_task


def generate_task_nochoice(*args, **kwargs):
    """Call the real task generator, then strip the two choice rules from the
    task background (route G1). Everything else in the task is untouched."""
    _ORIG_GENERATE(*args, **kwargs)
    task_file = kwargs.get("output_file", args[4] if len(args) > 4 else None)
    with open(task_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    kept = [ln for ln in lines if ln.strip() not in CHOICE_LINES]
    removed = len(lines) - len(kept)
    if removed != 2:
        raise RuntimeError(
            f"GRD shim expected to remove exactly 2 choice rules from "
            f"{task_file}, removed {removed}."
        )
    with open(task_file, "w", encoding="utf-8") as f:
        f.writelines(kept)
    print(f"[G1 shim] stripped {removed} choice rules from {task_file}")


COMMON = dict(
    partial=1.0,
    f_values=[10, 20],
    f_neg_values=None,
    n_values=[0.0],
    iterations=5,  # grouped_kfold: K=5 AAF-disjoint folds, one row per fold+f
    base_output_dir=os.path.join(INTEG, "pools"),
    train_dir=os.path.join(INTEG, "train"),
    train_output_dir=os.path.join(INTEG, "train_output"),
    results_dir=os.path.join(INTEG, "results"),
    no_prefix=False,
    dry_run=False,
    train_timeout_seconds=600,
    test_par_timeout_seconds=20,
    par2_factor=2.0,
    overwrite_existing_iterations=False,
    negative_policy="oracle_neg",
    negative_flip_k=1,
    test_set_policy="grouped_kfold",
    test_examples_per_class=50,
    test_sampling_seed=0,
    eval_match_policy="full_exact_model",
    ilasp_config_path=os.path.join(INTEG, "ilasp_config_grdprf.json"),
    task_sampling_seed_base=0,
)


def run_grd():
    T.generate_ilasp_task = generate_task_nochoice
    try:
        T.run_experiment(
            semantics="GRD",
            semantics_config_path=os.path.join(
                INTEG, "semantics_config_grdprf_GRD.json"),
            **COMMON,
        )
    finally:
        T.generate_ilasp_task = _ORIG_GENERATE


def run_prf():
    T.generate_ilasp_task = _ORIG_GENERATE
    T.run_experiment(
        semantics="PRF",
        semantics_config_path=os.path.join(
            INTEG, "semantics_config_grdprf_PRF.json"),
        **COMMON,
    )


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("GRD", "both"):
        run_grd()
    if which in ("PRF", "both"):
        run_prf()
    print("INTEGRATION RUN COMPLETE:", which)
