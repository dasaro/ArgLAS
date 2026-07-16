#!/usr/bin/env python3
"""GRD appendix run: grounded semantics through the STANDARD pipeline.

Closes the loop on the paper's GRD exclusion footnote: with the definite
learning background (config/semantics_config.json GRD.learn_background_file =
bg_nochoice_grd.lp, standard since the grd_prf_lab patch set), grounded is
exactly recoverable through the identical grouped-CV harness used by the main
campaign -- on BOTH the committed sparse pool (data/v3_sparse/aafs) and the
committed dense Exp1 pool (data/exp1_v2/aafs).

Unlike analysis/grd_prf_lab/integration/run_integration.py, this needs NO
shim and NO variant configs: everything comes from config/semantics_config.json
and config/ilasp_config.json (GRD ilasp_args --version=2i rides along; ILASP
takes the last --version flag).

Protocol (mirrors the lab integration run, extended to f=40 and two pools):
  grouped_kfold K=5 (AAF-disjoint folds), p_partial=1.0 (clean, complete
  labellings), noise=0.0, f in {10,20,40} (balanced pos=neg), oracle_neg
  negatives, full_exact_model evaluation on the bare AAF (exact recovery of
  the unique grounded labelling), test_examples_per_class=50, ILASP timeout
  600s. Labelling seed 20260310 (the campaign label_seed_base); fold seed 0.

Outputs under FABIO_ARTIFACTS_ROOT (set per pool by this script):
  artifacts/grd_appendix_run/<pool>/{labelled,train,train_output,results}
Final per-fold CSVs are then copied to data/grd_appendix/ by the caller.

Usage: python3 experiments/run_grd_appendix.py [sparse|dense|both]
"""
import os as _os
import sys as _sys

REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
_sys.path.insert(0, REPO)

POOLS = {
    "sparse": _os.path.join(REPO, "data", "v3_sparse", "aafs"),
    "dense": _os.path.join(REPO, "data", "exp1_v2", "aafs"),
}
ARTIFACTS_BASE = _os.path.join(REPO, "artifacts", "grd_appendix_run")
LABEL_SEED = 20260310  # campaign label_seed_base (experiments/run_configs/*)


def run_pool(pool_name):
    aafs_dir = POOLS[pool_name]
    root = _os.path.join(ARTIFACTS_BASE, pool_name)
    _os.makedirs(root, exist_ok=True)
    _os.environ["FABIO_ARTIFACTS_ROOT"] = root

    # Import after setting the env is not required (artifacts_root() reads the
    # env at call time), but keep imports here so each pool run is explicit.
    from arglas import generate_extensions as GE
    from arglas import train_test as T

    labelled_dir = _os.path.join(root, "labelled", "labelled_GRD_full")
    n_labelled = (
        len([f for f in _os.listdir(labelled_dir) if f.endswith(".lp")])
        if _os.path.isdir(labelled_dir)
        else 0
    )
    if n_labelled == 0:
        print(f"[{pool_name}] labelling pool {aafs_dir} -> {labelled_dir}")
        GE.main([
            "--input_dir", aafs_dir,
            "--base_output_dir", _os.path.join(root, "labelled"),
            "--semantics", "GRD",
            "--p_partial", "1.0",
            "--allow_empty",  # grounded labellings can be all-undec (esp. dense)
            "--seed", str(LABEL_SEED),
        ])
    else:
        print(f"[{pool_name}] reusing labelled pool ({n_labelled} files) at {labelled_dir}")

    T.run_experiment(
        semantics="GRD",
        partial=1.0,
        f_values=[10, 20, 40],
        f_neg_values=None,          # balanced: neg = pos
        n_values=[0.0],             # clean labels
        iterations=5,               # grouped_kfold: K=5 AAF-disjoint folds
        base_output_dir=_os.path.join(root, "labelled"),
        train_dir=_os.path.join(root, "train"),
        train_output_dir=_os.path.join(root, "train_output"),
        results_dir=_os.path.join(root, "results"),
        no_prefix=False,
        dry_run=False,
        train_timeout_seconds=600,
        test_par_timeout_seconds=20,
        overwrite_existing_iterations=False,
        negative_policy="oracle_neg",
        negative_flip_k=1,
        test_set_policy="grouped_kfold",
        test_examples_per_class=50,
        test_sampling_seed=0,
        eval_match_policy="full_exact_model",
        # STANDARD configs -- the whole point of this run:
        ilasp_config_path="ilasp_config.json",
        semantics_config_path="semantics_config.json",
        task_sampling_seed_base=0,
    )
    print(f"[{pool_name}] DONE -> {_os.path.join(root, 'results', 'GRD_full')}")


if __name__ == "__main__":
    which = _sys.argv[1] if len(_sys.argv) > 1 else "both"
    if which not in ("sparse", "dense", "both"):
        raise SystemExit(f"usage: {_sys.argv[0]} [sparse|dense|both]")
    for name in ("sparse", "dense"):
        if which in (name, "both"):
            run_pool(name)
    print("GRD APPENDIX RUN COMPLETE:", which)
