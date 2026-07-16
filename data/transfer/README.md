# Tier-1 cross-pool transfer (evaluation-only)

Committed record of the generator-breadth transfer experiment: every anchor-slice
learned program (STB/ADM/CMP/PRF x p in {1.0, 0.5} x q in {0.0, 0.1} x f in
{20, 60} x 5 grouped-CV folds, from the v2 dense campaign and the v3
sparse/self/large breadth campaigns) re-scored — with NO retraining — on fixed
complete-information test surfaces built from OTHER pools' committed AAFs.

Produced by `experiments/transfer_score.py` (deterministic; surface seed base
20260715). Its `--validate` mode reproduces the stored campaign `*_FULL`
confusion counts exactly (16/16 rows, one per pool x semantics) before any
transfer scoring is trusted.

## Directions

- `dense -> {sparse, self, large}` and `{sparse, self, large} -> dense`
  (cross-pool transfer; train and test AAFs come from disjoint pools).
- `X -> X` same-pool controls: calibration of the surface machinery only. The
  control surface is drawn from the WHOLE pool, so it can overlap a model's
  training AAFs; the honest within-pool reference is the fold-disjoint
  `STORED_MCC_FULL` column (copied from the committed campaign CSVs).

## Files

- `transfer_scores.csv` (`;`-separated): one row per (source model x target
  surface). Train-failure rows are kept with `ILASP_TRAIN_SUCCEEDED=0` and empty
  metric columns (failure taxonomy stays first-class; never fold them into
  scores).
- `transfer_summary.csv`: mean/min transfer MCC per
  (source, target, semantics, p, q, f) over folds, next to the mean stored
  within-pool complete-information MCC (`MEAN_STORED_MCC_FULL`) and the delta.
- `surfaces/<pool>/<SEM>/`: the labelled test items — 80 POS + 80 NEG per
  (pool x semantics), complete-information (p=1.0), oracle-labelled with the
  campaign `label_generation` runtime (ASPARTIX encodings; PRF via
  domain-heuristic domRec enumeration), at most one POS and one NEG per source
  AAF. `surfaces/manifest.json` records seeds and file lists.

## Scoring protocol

Exact campaign scorer, reused from `arglas.train_test`:
`run_learned_model_with_api` / `run_ground_truth_with_api` /
`evaluate_model_sets` with `full_exact_model`, config-driven per-semantics
backgrounds and clingo args from `config/semantics_config.json` (PRF gets the
eval-time subset-maximal in-selection symmetrically on both sides, as in the
campaign). clingo-only; no ILASP involved.
