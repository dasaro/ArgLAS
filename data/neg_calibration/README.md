# Negative-policy calibration (bridge license B2)

Per-fold record behind the paper's Table `tab:negcal` (Section 6, B2):
recovery against a clean oracle when training positives carry injected
per-argument label-flip noise, comparing negative-generation policies at
Experiment 2's operating scale.

Generated 2026-07-16 by:

```
python3 experiments/synthetic_neg_robustness.py \
  --labelled_root artifacts/final_synthetic_v2/labelled \
  --out_csv neg_robustness_v1.csv \
  --semantics ADM,CMP,STB --q_values 0.0,0.1,0.2 \
  --policies oracle_neg,flip_one,reliable_negative \
  --K 3 --n_pos 30 --n_neg 30 --train_timeout 600
```

Fold seed 20260312 (baked into the harness); ILASP 4.4.1. The labelled pools
regenerate deterministically from the committed `data/exp1_v2/aafs` via
`arglas.generate_extensions` if `artifacts/` is absent. 81 rows =
3 semantics x 3 noise levels x 3 policies x 3 grouped folds; all 81 succeeded
(SUCC=1). Columns: SEM, Q, POLICY, FOLD, SUCC, ACC, F1, MCC, WRONG_NEG
(fraction of generated "negatives" that are in fact legal labellings under
the target semantics).
