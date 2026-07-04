#!/bin/bash
# v2 campaign launcher (rev b): ADM/CMP/STB/PRF full grid + GRD noise-free column.
# GRD x noise removed: the no-choice definite formulation is fragile under polarity
# noise (all ILASP versions time out or learn junk) — deferred to a designed follow-up.
# STOP: kill any time. RESUME: rerun this script; completed rows/pools/AAFs are skipped.
set -u
cd "$(dirname "$0")"
export FABIO_ARTIFACTS_ROOT="${FABIO_ARTIFACTS_ROOT:-artifacts/final_synthetic_v2}"
for cfg in pos50_grd pos50 pos60_grd pos60 pos40_grd pos40; do
  echo "===== [$(date '+%F %T')] launching final_synthetic_v2_${cfg} ====="
  python3 run_experiment_grid.py --config "run_configs/final_synthetic_v2_${cfg}.json"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "===== final_synthetic_v2_${cfg} exited rc=$rc — rerun this script to resume ====="
    exit $rc
  fi
done
echo "===== [$(date '+%F %T')] ALL v2 CONFIGS DONE ====="
