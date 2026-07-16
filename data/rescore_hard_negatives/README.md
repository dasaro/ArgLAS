# rescore_hard_negatives — adversarial Hamming-1 negative surface (evaluation-only)

Re-scores the **existing** learned models of the v2 synthetic campaign
(`data/exp1_v2/results/`, models under `artifacts/final_synthetic_v2/train_output/`,
addressed per-row via `LEARNED_MODEL_FILENAME`) on an adversarial negative test
surface, without any new ILASP training. Produced by
`analysis/hard_negative_rescore.py` (2026-07-16).

## Why

The campaign's committed negatives are *sampled* non-extensions; most violate
conflict-freeness outright, so a reviewer can ask whether near-ceiling MCC merely
reflects an easy negative class. This record answers that with the hardest
labelling-level negatives that exist: **Hamming-1 perturbations of true
extensions** — a single `in`/`out` label flipped on a held-out positive test
item, oracle-verified to no longer be an extension.

## Method (pinned to the campaign's own code paths and seeds)

- Test-split reconstruction: `build_grouped_folds` + `build_grouped_balanced_test`
  (`arglas/train_test.py`) with the campaign identity
  `test_sampling_seed=20260312`, `K=5`, `test_examples_per_class=100`, over the
  complete-information pools `artifacts/final_synthetic_v2/labelled/labelled_<SEM>_full`.
  The reconstruction is validated by recomputing committed rows' `TP_FULL/FP_FULL/
  TN_FULL/FN_FULL` from scratch and requiring bit-exact agreement (`--verify`;
  passed for all four semantics).
- Hard negatives: for each of the 100 held-out positive test labellings of a
  (semantics, fold), one `flip_one` mutation
  (`arglas/generate_ilasp_task.build_synthetic_negative`) kept only if the
  ground-truth stack (`run_ground_truth_with_api`: ASPARTIX reference encoding +
  injected labelling, the same adjudicator used on the campaign surface, and the
  eval-time equivalent of `generate_extensions.verify_extension`) has **no**
  model for it. Flips that remain legal labellings are counted in the manifests
  and skipped — the hard-negative class carries zero label noise. Deterministic
  RNG: `stable_seed_from_parts("hard_negative_rescore", 20260312, sem, fold)`.
  One hard negative per positive ⇒ balanced 100/100 surface per fold, shared by
  all rows of that (semantics, fold) for paired comparison across cells.
- Scoring: `run_learned_model_with_api` + `evaluate_model_sets`
  (`eval_match_policy=full_exact_model`), the campaign's learned-model stack.
  The positive side of the surface is identical to the committed
  complete-information surface, so `TP_FULL`/`FN_FULL` are carried over from the
  committed row (bit-exact reproducible, see above) and
  `MCC_HARD = mcc(TP_FULL, FP_HARD, TN_HARD, FN_FULL)`.
- Scope: STB/ADM/CMP/PRF, all 3,240 committed rows (3,120 scored; the 120
  training failures keep empty hard columns — failure taxonomy stays
  first-class). GRD is excluded (out of the paper's scope; scored on the bare
  AAF, so a labelled-negative surface does not apply).

## Layout

- `hard_neg_sets/<SEM>_fold<k>/` — the 100 verified Hamming-1 instances (`.lp`)
  plus `manifest.json` (source positive, flipped argument, flip direction,
  count of flips rejected as still-legal).
- `results/<config>/results_<k>.csv` — per-row rescore mirroring
  `data/exp1_v2/results/` (semicolon-separated). Key columns:
  `TP_FULL..MCC_FULL` copied from the committed row; `HARD_NEG_COUNT`,
  `FP_HARD`, `TN_HARD`, `MCC_HARD`, `ACCURACY_HARD`, `HARD_EVAL_SECONDS` new.
- `summary_by_cell.csv` — mean `MCC_FULL` vs `MCC_HARD` per grid cell
  (semantics × completeness × noise × ratio arm × f).
- `summary_surface_hard.csv` — Table-`tab:surface`-shaped aggregate
  (noise × semantics × f, balanced arm, pooled over completeness).

## Notable manifest fact

The still-legal-flip rejection counts measure how "sharp" each semantics'
extension set is at Hamming distance 1: STB and PRF reject nothing (no
Hamming-1 neighbour of a stable/preferred extension is ever an extension —
exactness resp. subset-maximality), while ADM discards ~44–55 and CMP ~12–29
legal single flips per 100 (removing one argument from an admissible set often
leaves it admissible).

## Reproduction

```
python analysis/hard_negative_rescore.py --verify
```

Stop/resume-safe (completed per-config CSVs and hard-negative sets are reused).
