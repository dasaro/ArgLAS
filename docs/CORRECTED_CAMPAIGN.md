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

Eval fix validated: re-scoring ADM partial=1.0 noise=0 gives acc 0.96–1.00 vs the buggy
~0.58. Grouped split validated: folds are train∩test-disjoint and tile all 500 AAFs once.

## Launch procedure (campaign is NOT auto-launched)

The corrected campaign uses a FRESH artifact root so it never mixes with the buggy run
`artifacts/final_synthetic_main_20260309_214128`.

```bash
cd /Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude
export FABIO_ARTIFACTS_ROOT="$PWD/artifacts/final_synthetic_corrected_20260624"
mkdir -p "$FABIO_ARTIFACTS_ROOT"

# (optional, faster) reuse the verified-sound AAFs + ADM/CMP/STB/GRD labelling from the
# old run instead of regenerating (identical by seed; just saves the relabel pass):
cp -R artifacts/final_synthetic_main_20260309_214128/aafs     "$FABIO_ARTIFACTS_ROOT/"
cp -R artifacts/final_synthetic_main_20260309_214128/labelled "$FABIO_ARTIFACTS_ROOT/"

# 1) PRF cost probe first (PRF was never run; it is the cost wildcard: subset-maximal +
#    --heuristic=Domain --enum=domRec + --learn-heuristics). Labels PRF, runs 12 cells.
python3 -m arglas benchmark run --config run_configs/prf_probe.json
#    -> inspect train times; if acceptable, add "PRF" to semantics in the corrected config.

# 2) The corrected 4-semantics grid (ADM/CMP/STB/GRD), reduced noise {0,0.1,0.2}:
python3 -m arglas benchmark run   --config run_configs/final_synthetic_corrected.json   # launcher
python3 -m arglas benchmark watch --config run_configs/final_synthetic_corrected.json   # watchdog (separate shell/term)
```

## Budget (M4 Pro, 12 cores / 24 GB; ~2.8 GB peak RSS per ILASP → 7 workers)

- Corrected 4-sem grid: 72 cells × (K=5 folds × 5 f-sizes) = 1,800 ILASP runs ≈ **~1.9 CPU-days → ~7–9 wall-hours** at 7 workers.
- + PRF: measure with the probe first; estimated +0.5–1 wall-day.
- Full noise {0..0.4} instead of {0,0.1,0.2}: roughly doubles wall-clock.

## Caveats

- Phase-1 re-score numbers (`artifacts/rescore_eval_fixed_20260624/`) remove the eval bias
  but still carry AAF-leakage (they re-use the old leaky models); only this corrected
  campaign (grouped split + retrain) gives leakage-free, CI-backed results.
- `cell_retry_budget` is not yet wired (worker_loop currently records-and-continues without
  retrying transient SIGSEGV); add if needed.
