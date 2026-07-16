# Committed experimental data (Experiment 1 + breadth campaigns)

The complete quantitative record behind the paper's synthetic experiments, committed so
reviewers can reproduce every figure and table **without re-running any learning**.

| dir | campaign | rows | contents |
|---|---|---|---|
| `exp1_v2/` | Experiment 1 (four semantics × completeness × noise × size × proportion, grouped 5-fold CV) | 3,510 | `results/` per-cell CSVs, `aafs/` the 500-AAF generator pool |
| `v3_sparse/` | generator breadth: sparse (`s~U[n,2n]`) | 160 | results + 500-AAF pool |
| `v3_self/` | generator breadth: self-attacks allowed | 160 | results + 500-AAF pool |
| `v3_large/` | generator breadth: n ∈ {10,11,12} | 160 | results + 180-AAF pool |
| `v3_baf/` | framework breadth: bipolar AFs | 45 | results + 500-BAF pool (att + support facts) |
| `v3_aba/` | framework breadth: ABA via corrected translation | 30 | results + 300 translated AAFs (+ `aba_source_*.txt` sidecars tracing each AAF to its source ABA) |
| `rescore_eval_fixed/` | audit trail: re-scored CSVs from the evaluation-metric correction | — | evidence for the complete-information rescore |
| `neg_calibration/` | negative-policy calibration (bridge license B2, Table `tab:negcal`) | 81 | per-fold CSV; see its `README.md` |
| `grd_appendix/` | grounded through the standard pipeline (definite background), dense + sparse | 30 | appendix run; see its `README.md` |
| `rescore_hard_negatives/` | evaluation-only re-score of the v2 learned models on an adversarial Hamming-1 negative surface | — | summaries + per-cell results; see its `README.md` |
| `transfer/` | evaluation-only cross-pool transfer of learned models across breadth pools | — | scores + surfaces; see its `README.md` |

Result CSVs are semicolon-delimited; one row per (cell, fold) with training/test metrics,
timing, and the failure taxonomy (`ILASP_TRAIN_TIMED_OUT` / `_UNSAT` / `_ERROR` are
disjoint). `MCC_FULL` is the complete-information recovery metric used in the paper;
grounded rows (out of the paper's scope) are retained in `exp1_v2` for completeness and
excluded by all analysis scripts.

## Reproducing from this data (minutes)

- Paper figures: `python3 docs/aij_paper/make_figs.py`
- Exp1/Exp2 summary plots: `python3 analysis/make_plots.py` (writes `analysis/figs_regen/`)
- Non-LAS baseline (§7): `python3 analysis/tree_baseline/tree_baseline.py` (reads `exp1_v2/aafs`;
  writes `*_regen` twins of the committed outputs)
- Theorem exhaustive checks: `python3 analysis/zlatina_theorems/check_equivalence.py 4`
  (writes `level1_results_regen.json` — diff against the committed `level1_results.json`)

## Reproducing from scratch (days)

Every run behind the committed record is seeded: the v2 and v3 campaign configs
(`experiments/run_configs/final_synthetic_v2_*.json`, `v3_*.json`) carry the full seed
set (`master_seed`, `label_seed_base`, `task_sampling_seed_base`, `test_sampling_seed`,
generator `seed`); the `v3_baf`/`v3_aba` generator-pool seeds are pinned in
`experiments/run_v3_gap.sh`. (Pre-audit configs without seeds were retired to
`experiments/legacy/run_configs/`.) See the top-level README and
`docs/gap_experiments_spec.md`. Intermediate
pools (`labelled/`, `train/`, `train_output/`) are deterministic products of these seeds and
are deliberately not committed.
