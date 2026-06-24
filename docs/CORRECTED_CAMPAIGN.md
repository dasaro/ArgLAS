# Corrected synthetic campaign (Exp1) — runbook

This documents the corrected Exp1 pipeline after the 2026-06-23/24 health+trust audit
and the Phase-0 fixes. See the `fix/audit-corrections` branch commits for the changes.

## What was fixed (and why the old numbers can't be trusted)

| Defect | Fix | Commit |
|---|---|---|
| Eval `out/1` under-determination (CRITICAL, pessimistic) | `completion_rules.train_test_learned=true` (eval-only; learned answer sets become total in/out, comparable to ASPARTIX) | `bb92296` |
| Failed-training scored as TN → 0.5 accuracy floor (HIGH) | failed rows carry `tp=fp=tn=fn=0`, flagged by `ILASP_TRAIN_SUCCEEDED=0`, excluded from aggregation | `bb92296`,`e9e7df2` |
| AAF-level train/test leakage (CRITICAL, optimistic) | new `test_set_policy=grouped_kfold`: K group-disjoint CV folds over source-AAFs | `e9e7df2` |
| No generalization CIs (HIGH) | K folds give an honest interval: mean ± t_{K-1}/√K · s | `e9e7df2` |
| Path-dependent hold-out seed (reproducibility) | grouped fold/hold-out seeds use `(fold_seed, N)` / `(fold_seed, fold_index)`, not `abspath` | `e9e7df2` |
| Poison cell halts whole campaign (HIGH) | worker_loop record-and-continue (no fail-fast) | `4a88aec` |
| GRD never scheduled | `build_jobs` noise-ascending, semantics-interleaved | `4a88aec` |
| Absurd timeouts | train 1000s, test 20s (calibrated from the cost model) | `4a88aec` |
| Fabricated PAR2 penalty on failed rows + challenge-specific metric | dropped the 3 PAR2 columns → raw `TEST_LEARNED_/TEST_ORACLE_{TOTAL,MEAN,MAX}_SECONDS` + `ANY_TEST_TIMED_OUT`; added **MCC** (paper metric) and **RUN_SEED** (per-fold reproducibility); failed rows leave timing empty | `5b51d4a` |
| Thin fold could silently shrink the test set | `build_grouped_balanced_test` min-example guard: fail-fast if a fold can't supply `test_examples_per_class` | `5b51d4a` |
| Stale-schema CSV corruption | `append_result_row` refuses to append a 45-col row into an old 39-col file; plots aggregate quality over `ILASP_TRAIN_SUCCEEDED==1` rows only, surface MCC | `5b51d4a`,`9f10427` |

Eval fix validated: re-scoring ADM partial=1.0 noise=0 gives acc 0.96–1.00 vs the buggy
~0.58. Grouped split validated: folds are train∩test-disjoint and tile all 500 AAFs once.

**Launch-readiness verification (2026-06-24, 5-way parallel, 4 PASS / 1 WARN-no-bug):**
end-to-end smoke produces the 45-col schema with MCC/raw-timing/RUN_SEED correctly
populated (MCC recomputed exact); replay re-scores under the new schema; **every
(ADM/CMP/STB × partial {0.5,0.7,1.0} × fold) clears test/class=100** (global min balanced
test = 179, STB fold-5; min train pool/class = 771), so the guard never fires; config
constructs to 18 cells / 360 runs noise-ascending; adversarial diff review found the
45-col header↔row alignment, MCC formula+guard, and replay key-mapping all correct.

## Launch procedure (campaign is NOT auto-launched)

The corrected campaign uses a FRESH artifact root so it never mixes with the buggy run
`artifacts/final_synthetic_main_20260309_214128`.

```bash
cd /Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude
export FABIO_ARTIFACTS_ROOT="$PWD/artifacts/final_synthetic_corrected_20260624"
mkdir -p "$FABIO_ARTIFACTS_ROOT"

# Reuse the verified-sound AAFs + ADM/CMP/STB labelling from the old run. SAFE to symlink:
# ensure_aafs sees 500 (seed 20260309) and ensure_labelled sees POS/NEG >> 50, so both
# SKIP regeneration and never write into the source. (cp -R also works if you prefer copies.)
ln -s "$PWD/artifacts/final_synthetic_main_20260309_214128/aafs"     "$FABIO_ARTIFACTS_ROOT/aafs"
ln -s "$PWD/artifacts/final_synthetic_main_20260309_214128/labelled" "$FABIO_ARTIFACTS_ROOT/labelled"

# The corrected 3-semantics grid (ADM/CMP/STB): partials {0.5,0.7,1.0}, noise {0,0.1},
# f {10,20,30,40}, K=5, test/class=100, oracle_neg. 18 cells / 360 ILASP runs.
# GRD is EXCLUDED (grounded needs minimality-forcing negatives — not yet implemented).
python3 -m arglas benchmark run   --config run_configs/final_synthetic_corrected.json   # launcher
python3 -m arglas benchmark watch --config run_configs/final_synthetic_corrected.json   # watchdog (separate term)

# OPTIONAL, separately: PRF cost probe (PRF is the cost wildcard: subset-maximal +
# --heuristic=Domain --enum=domRec + --learn-heuristics). Run before adding "PRF":
# python3 -m arglas benchmark run --config run_configs/prf_probe.json
```

## Budget (M4 Pro, 12 cores / 24 GB; ~2.8 GB peak RSS per ILASP → 7 workers)

- Corrected 3-sem grid (ADM/CMP/STB): **18 cells × (K=5 folds × 4 f-sizes) = 360 ILASP runs**.
  Split 180 noise-0 (≈8–15 s/run) + 180 noise-0.1 (soft optimisation, ≈100–400 s/run).
  ≈ **5–21 CPU-hours → ~1–4.4 wall-hours** at 7 workers; noise-0.1 is ≥95% of the cost and
  runs last (noise-ascending schedule). `train_timeout=1000s` gives ~2.5× headroom over the
  observed noisy-soft max (~400 s). Re-check after the first 2–3 noise-0.1 cells report.
- + PRF: measure with the probe first; estimated +0.5–1 wall-day.
- + GRD: excluded pending minimality-forcing negatives + a higher GRD train timeout.
- Widening noise (add 0.2) or partials roughly scales the noise-fraction cost linearly.

## Output schema (45 columns, per fold-iteration row)

Quality: `MCC` (primary, paper metric), `ACCURACY`, `PRECISION`/`RECALL`/`F1`, `TP/FP/TN/FN`.
Aggregate over `ILASP_TRAIN_SUCCEEDED==1` rows only; the K=5 folds per (sem,partial,noise)
give the CI: mean ± t_{K-1}/√K · s. Timing: `RUNNING_TIME_ILASP_TRAIN_SECONDS` (train),
`TEST_{LEARNED,ORACLE}_{TOTAL,MEAN,MAX}_SECONDS` (raw eval solve times), `ANY_TEST_TIMED_OUT`
(post-hoc "exceeded budget", not a kill). Reproducibility: `RUN_SEED` (per-row task seed).
Failure: `ILASP_TRAIN_SUCCEEDED`, `ILASP_TRAIN_TIMED_OUT`, `ILASP_TRAIN_EXIT_CODE`. The old
PAR2 columns are gone; `plot_benchmark_progress.py` writes `summary.csv` with the same
quality/MCC means + `train_success_rate`/`timeout_rate`.

## GRD (grounded) — known-not-ready

GRD is configured for the correct approach (`learn_heuristics` + `--heuristic=Domain --enum=domRec` + per-semantics `completion_rules.train_test_learned=false` + `eval_on_bare_aaf=true`) and CAN recover grounded perfectly when ILASP learns the right rule+heuristic (`in(V1):-arg(V1),not not_defended(V1).` + `#heuristic in(V1).[1@1,false]` → 30/30). But it is **not reliable**: the random-relabel negatives don't pin grounded's defense/minimality, so ILASP often learns a wrong theory (acc 0.0), and `--learn-heuristics` is slow. Fix path: minimality-forcing negatives (complete-but-not-grounded labellings as hard negatives) + a much higher GRD train timeout. Grounded is PTIME-computable directly, so a small paper-style demonstration may be preferable to the full grid.

## Caveats

- Phase-1 re-score numbers (`artifacts/rescore_eval_fixed_20260624/`) remove the eval bias
  but still carry AAF-leakage (they re-use the old leaky models); only this corrected
  campaign (grouped split + retrain) gives leakage-free, CI-backed results.
- `cell_retry_budget` is not yet wired (worker_loop currently records-and-continues without
  retrying transient SIGSEGV); add if needed.
