#!/bin/bash
# v3 gap-experiment launcher: generator breadth (Experiment G) + framework breadth
# (Experiment F1 BAF, F2 ABA). Full design + deferred patches: docs/gap_experiments_spec.md.
# STOP: kill any time. RESUME: rerun this script; completed rows/pools are skipped.
#
# Usage:  ./run_v3_gap.sh smoke   # after applying the deferred patches (spec §4)
#         nohup ./run_v3_gap.sh > v3_gap.out 2>&1 &
set -u
cd "$(dirname "$0")"

die() { echo "[v3] FATAL: $1" >&2; exit 1; }

# --- guard 1: never overlap with a running campaign (shares workers + pipeline files)
if pgrep -f "run_experiment_grid.py" >/dev/null 2>&1; then
  die "an experiment grid is still running — wait for v2 to finish (or kill it) first"
fi

# --- guard 2: refuse to start until the deferred patches (spec §4) are applied
grep -q "allow_self_attacks" generate_aafs.py \
  || die "generate_aafs.py patch not applied (spec §4.1: density preset + self-attacks)"
grep -q "density_preset" run_experiment_grid.py \
  || die "run_experiment_grid.py patch not applied (spec §4.2: ensure_aafs plumbing)"
grep -q 'support(' generate_extensions.py \
  || die "generate_extensions.py patch not applied (spec §4.3: support-fact prefix)"
python3 - <<'PY' || die "semantics_config.json BAF entries missing (spec §4.4)"
import json, sys
c = json.load(open("semantics_config.json"))
sys.exit(0 if all(k in c for k in ("BAF_STB", "BAF_ADM", "BAF_CMP")) else 1)
PY

MODE="${1:-full}"
if [ "$MODE" = "smoke" ]; then
  echo "[v3] smoke: sparse+self-attack generator flags, 1 STB cell, 2 folds"
  FABIO_ARTIFACTS_ROOT=artifacts/v3_smoke \
    python3 run_experiment_grid.py --config run_configs/v3_smoke_breadth.json \
    || die "smoke run failed"
  echo "[v3] SMOKE OK — launch the full run with: nohup ./run_v3_gap.sh > v3_gap.out 2>&1 &"
  exit 0
fi

# --- Experiment F pools (pre-populated; idempotent)
if [ -z "$(ls artifacts/final_synthetic_v3_baf/aafs/ 2>/dev/null)" ]; then
  echo "[v3] generating BAF pool (500 BAFs, n=4..8)"
  python3 generate_bafs.py 4 8 100 \
    --output_dir artifacts/final_synthetic_v3_baf/aafs --seed 20260804 --quiet \
    || die "BAF pool generation failed"
fi
if [ -z "$(ls artifacts/final_synthetic_v3_aba/aafs/ 2>/dev/null)" ]; then
  echo "[v3] generating ABA-translated pool (300 AAFs, corrected per-root translation)"
  python3 translate_abas.py 300 \
    --output_dir artifacts/final_synthetic_v3_aba/aafs --seed 20260805 --quiet \
    || die "ABA translation failed"
fi

run_cfg() { # $1 = artifact root, $2 = config stem
  echo "===== [$(date '+%F %T')] launching $2 (root: $1) ====="
  FABIO_ARTIFACTS_ROOT="$1" python3 run_experiment_grid.py --config "run_configs/$2.json"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "===== $2 exited rc=$rc — rerun this script to resume ====="
    exit $rc
  fi
}

# Fast cells first (F: hours), then the three G regimes (GRD column before main grid).
run_cfg artifacts/final_synthetic_v3_baf v3_baf
run_cfg artifacts/final_synthetic_v3_aba v3_aba
for regime in sparse self large; do
  run_cfg "artifacts/final_synthetic_v3_${regime}" "v3_breadth_${regime}_grd"
  run_cfg "artifacts/final_synthetic_v3_${regime}" "v3_breadth_${regime}"
done
echo "===== [$(date '+%F %T')] ALL v3 GAP EXPERIMENTS DONE ====="
