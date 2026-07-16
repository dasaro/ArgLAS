# GRD appendix run: grounded through the standard pipeline

Closes the paper's grounded-semantics loop: with the **definite learning
background** (`config/bg_nochoice_grd.lp`, wired in as the standard
`GRD.learn_background_file` in `config/semantics_config.json`), grounded is
exactly recoverable through the **identical** grouped-CV harness used by the
main campaign — no shim, no variant configs — on both the committed sparse
pool and the committed dense Experiment-1 pool.

## Protocol

- Driver: `experiments/run_grd_appendix.py` (run 2026-07-16, ILASP 4.4.1,
  clingo 5.8.0).
- Pools: `sparse/` = `data/v3_sparse/aafs` (500 AAFs, attacks ~ U[n,2n]);
  `dense/` = `data/exp1_v2/aafs` (500 AAFs, attacks ~ U[n, n(n-1)]).
- Labelling: oracle grounded labellings (`ASPARTIX/grounded.lp`), p_partial=1.0
  (complete labellings, clean labels), `--allow_empty` (all-undec grounded
  labellings kept as positives), label seed 20260310.
  Empty grounded in-set rate: dense 341/500 (68.2%), sparse 132/500 (26.4%).
- Learning/eval: `arglas.train_test.run_experiment`, `test_set_policy=grouped_kfold`
  K=5 (AAF-disjoint folds, fold seed 0), f in {10, 20, 40} (balanced pos=neg),
  noise 0.0, `negative_policy=oracle_neg`, `eval_match_policy=full_exact_model`,
  `test_examples_per_class=50`, ILASP train timeout 600 s,
  `task_sampling_seed_base=0`. Standard `config/ilasp_config.json`
  (GRD: `--version=2i`) and `config/semantics_config.json`.
- GRD evaluation is on the **bare AAF** (`eval_on_bare_aaf`): each of the 100
  test items per fold checks whether the learned program's unique answer set
  equals the oracle grounded labelling exactly, so `ACCURACY` (= `ACCURACY_FULL`)
  IS per-framework exact recovery; the `MCC` columns are degenerate (0.0, no
  negative class) and must not be read as scores.

## Results (exact recovery, mean over 5 folds)

| pool   | f=10  | f=20  | f=40  |
|--------|-------|-------|-------|
| sparse | 0.918 | 1.000 | 1.000 |
| dense  | 1.000 | 1.000 | 1.000 |

All 30 ILASP runs succeeded (no timeout, no UNSAT, no error); training time
1.1–2.0 s per fold. 29/30 tasks learned the exact two-rule grounded program

    out(V1) :- defeated(V1).
    in(V1) :- supported(V1).

(vocabulary from `bg_nochoice_grd.lp`: `defeated` = attacked by an in argument,
`supported` = all attackers out). The single non-perfect fold (sparse, f=10,
fold 1: 0.59) learned the over-general `out(V1) :- not_defended(V1)` — an
alternative consistent with its 10 training examples that the other folds'
samples rule out.

## Files

- `sparse/results_{1..5}.csv`, `dense/results_{1..5}.csv` — one file per fold,
  one row per f value; semicolon-delimited, standard campaign schema (see
  `data/README.md`).

## Reproduce

    python3 experiments/run_grd_appendix.py both

Outputs (labelled pools, ILASP tasks, learned programs, results) land under
`artifacts/grd_appendix_run/{sparse,dense}/` via `FABIO_ARTIFACTS_ROOT`; the
per-fold results CSVs here are verbatim copies of
`artifacts/grd_appendix_run/<pool>/results/GRD_full/results_*.csv`.
