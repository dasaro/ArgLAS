#!/bin/bash
# Memory-safe runner for the v3 "large" regime (n=10-12 dense: the campaign's
# heaviest ILASP tasks; a single noisy f=60 task can peak ~7-8 GB).
#
# Two machine crashes came from 7 parallel workers exhausting 24 GB. macOS
# rejects ulimit -v, so the fix is:
#   (1) workers=1 in the config -- one heavy task at a time cannot coincide with
#       another, so peak memory ~= one task (~7-8 GB) << 24 GB. This alone makes
#       OOM essentially impossible.
#   (2) a KILL backstop watchdog -- if available memory ever hits a true
#       emergency (< 1.8 GB), it SIGKILLs the largest ILASP to FREE memory (a
#       paused process still holds its memory, so pausing would only stall; kill
#       actually frees). A killed task is recorded as a failure and the grid
#       continues -- it never OOMs the machine.
# Resume-safe: rerun this script; completed rows are skipped.
set -u
cd "$(dirname "$0")/.."
ROOT=artifacts/final_synthetic_v3_large
CFG=experiments/run_configs/v3_breadth_large.json
rm -f "$ROOT"/logs/*.lock

KILL_GB=1.8   # emergency floor: below this, kill the largest ILASP to free memory

avail_gb() {  # macOS available memory: free+inactive+speculative+purgeable pages
  local page; page=$(sysctl -n hw.pagesize)
  vm_stat | awk -v p="$page" '
    /Pages free/        {gsub(/\./,"",$3); f=$3}
    /Pages inactive/    {gsub(/\./,"",$3); i=$3}
    /Pages speculative/ {gsub(/\./,"",$3); s=$3}
    /Pages purgeable/   {gsub(/\./,"",$3); g=$3}
    END {printf "%.1f", (f+i+s+g)*p/1073741824}'
}

watchdog() {
  while true; do
    a=$(avail_gb)
    if awk "BEGIN{exit !($a < $KILL_GB)}"; then
      # free memory by killing the single largest ILASP (recorded as a failure;
      # the grid keeps going). With workers=1 this should essentially never fire.
      victim=$(ps -axo pid,rss,comm | awk '$3=="ILASP"{print $2,$1}' | sort -rn | head -1 | awk '{print $2}')
      if [ -n "$victim" ]; then
        echo "[watchdog $(date '+%F %T')] EMERGENCY avail ${a}GB < ${KILL_GB} -- SIGKILL largest ILASP pid $victim"
        kill -9 "$victim" 2>/dev/null
        sleep 8
      fi
    fi
    sleep 4
  done
}
watchdog & WD=$!
trap 'kill $WD 2>/dev/null' EXIT INT TERM

echo "===== [$(date '+%F %T')] large regime (workers=1, kill-watchdog pid $WD, avail $(avail_gb)GB) ====="
FABIO_ARTIFACTS_ROOT="$ROOT" python3 experiments/run_experiment_grid.py --config "$CFG"
rc=$?
kill "$WD" 2>/dev/null
if [ "$rc" -eq 0 ]; then
  echo "===== [$(date '+%F %T')] ALL v3 GAP EXPERIMENTS DONE (large via memory-safe runner) ====="
else
  echo "===== large exited rc=$rc -- rerun ./run_large_safe.sh to resume ====="
fi
exit "$rc"
