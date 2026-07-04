#!/bin/bash
# v2 campaign launcher: 5 semantics x p{1,.75,.5} x q{0,.1,.2} x totals{20..160} x 5 folds
# x 3 pos/neg proportions (50/60/40% positive) = 4050 rows, dual-surface eval.
# STOP: kill this script (or the python it runs) any time. RESUME: rerun this script —
# completed rows, pools, and AAFs are skipped automatically; partial rows are re-run.
set -u
cd "$(dirname "$0")"
export FABIO_ARTIFACTS_ROOT="${FABIO_ARTIFACTS_ROOT:-artifacts/final_synthetic_v2}"
for cfg in pos50 pos60 pos40; do
  echo "===== [$(date '+%F %T')] launching final_synthetic_v2_${cfg} ====="
  python3 run_experiment_grid.py --config "run_configs/final_synthetic_v2_${cfg}.json"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "===== final_synthetic_v2_${cfg} exited rc=$rc — rerun this script to resume ====="
    exit $rc
  fi
done
echo "===== [$(date '+%F %T')] ALL v2 CONFIGS DONE ====="
