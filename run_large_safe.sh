#!/bin/bash
# Memory-safe runner for the v3 "large" regime (n=10-12 dense: the campaign's
# heaviest ILASP/clingo tasks). Two crashes were caused by 7 parallel workers
# exhausting 24 GB RAM. Safety = low concurrency (workers=2 in the config) + a
# memory watchdog that pauses the solvers if available memory hits the danger
# zone and resumes them once it recovers, so the machine cannot OOM.
# Resume-safe: rerun this script; completed rows are skipped.
set -u
cd "$(dirname "$0")"
ROOT=artifacts/final_synthetic_v3_large
CFG=run_configs/v3_breadth_large.json
rm -f "$ROOT"/logs/*.lock

PAUSE_GB=2.5      # pause solvers when available memory drops below this
RESUME_GB=4.5     # resume once it climbs back above this

avail_gb() {  # macOS available memory: free+inactive+speculative+purgeable pages
  local page; page=$(sysctl -n hw.pagesize)
  vm_stat | awk -v p="$page" '
    /Pages free/        {gsub(/\./,"",$3); f=$3}
    /Pages inactive/    {gsub(/\./,"",$3); i=$3}
    /Pages speculative/ {gsub(/\./,"",$3); s=$3}
    /Pages purgeable/   {gsub(/\./,"",$3); g=$3}
    END {printf "%.1f", (f+i+s+g)*p/1073741824}'
}

# --- watchdog: pause/resume clingo+ILASP under memory pressure -------------
watchdog() {
  local paused=0 a
  while true; do
    a=$(avail_gb)
    if [ "$paused" -eq 0 ] && awk "BEGIN{exit !($a < $PAUSE_GB)}"; then
      echo "[watchdog $(date '+%F %T')] available ${a}GB < ${PAUSE_GB} -- SIGSTOP solvers"
      pkill -STOP -x ILASP 2>/dev/null; pkill -STOP -x clingo 2>/dev/null
      paused=1
    elif [ "$paused" -eq 1 ] && awk "BEGIN{exit !($a > $RESUME_GB)}"; then
      echo "[watchdog $(date '+%F %T')] available ${a}GB > ${RESUME_GB} -- SIGCONT solvers"
      pkill -CONT -x ILASP 2>/dev/null; pkill -CONT -x clingo 2>/dev/null
      paused=0
    fi
    sleep 5
  done
}
watchdog & WD=$!
# make sure a pause never outlives the watchdog, and clean up on exit
cleanup() { kill "$WD" 2>/dev/null; pkill -CONT -x ILASP 2>/dev/null; pkill -CONT -x clingo 2>/dev/null; }
trap cleanup EXIT INT TERM

echo "===== [$(date '+%F %T')] large regime (workers=2, watchdog pid $WD, avail $(avail_gb)GB) ====="
FABIO_ARTIFACTS_ROOT="$ROOT" python3 run_experiment_grid.py --config "$CFG"
rc=$?
cleanup
if [ "$rc" -eq 0 ]; then
  echo "===== [$(date '+%F %T')] ALL v3 GAP EXPERIMENTS DONE (large via memory-safe runner) ====="
else
  echo "===== large exited rc=$rc -- rerun ./run_large_safe.sh to resume ====="
fi
exit "$rc"
