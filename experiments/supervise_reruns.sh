#!/bin/bash
# Unattended supervisor for the three targeted re-runs (experiments/RERUNS.md).
# Runs them in priority order, relaunches the resume-safe launcher if it dies (up to
# MAX_ATTEMPTS per run, waiting for any orphaned grid workers first), and writes a
# one-screen progress report every minute to $PROGRESS. Survives Claude/terminal exits
# (nohup); does NOT survive a machine reboot — just rerun it, everything resumes.
#
#   nohup ./experiments/supervise_reruns.sh > artifacts/reruns_supervisor.out 2>&1 &
#   cat artifacts/reruns_progress.txt            # completion % per run, one line each
set -u
cd "$(dirname "$0")/.."
mkdir -p artifacts
PROGRESS=artifacts/reruns_progress.txt
MAX_ATTEMPTS=20
BACKOFF=90

# name | launcher subcommand | artifacts root | expected rows
RUNS=(
  "self_prf_recap|self-prf-recap|artifacts/final_synthetic_v3_self_prf_recap|20"
  "baf_anchor|baf-anchor|artifacts/final_synthetic_v3_baf_anchor|120"
  "seedB|seedb|artifacts/final_synthetic_seedB|440"
)

rows() { # $1 = root -> "done timedout"
  python3 - "$1" <<'PY'
import csv, glob, sys
n = to = 0
for f in glob.glob(f"{sys.argv[1]}/results/**/results_*.csv", recursive=True):
    for r in csv.DictReader(open(f), delimiter=";"):
        n += 1; to += r.get("ILASP_TRAIN_TIMED_OUT") == "1"
print(n, to)
PY
}

avail_gb() {
  local page; page=$(sysctl -n hw.pagesize)
  vm_stat | awk -v p="$page" '/Pages free/{gsub(/\./,"",$3);f=$3} /Pages inactive/{gsub(/\./,"",$3);i=$3}
    /Pages speculative/{gsub(/\./,"",$3);s=$3} /Pages purgeable/{gsub(/\./,"",$3);g=$3}
    END{printf "%.1f",(f+i+s+g)*p/1073741824}'
}

report() { # rewrite the whole progress file
  {
    echo "reruns supervisor — $(date '+%F %T') — avail RAM $(avail_gb) GB — grid $(pgrep -f '[r]un_experiment_grid.py' >/dev/null && echo RUNNING || echo idle)"
    for spec in "${RUNS[@]}"; do
      IFS='|' read -r name sub root expected <<<"$spec"
      if [ -d "$root/results" ]; then
        read -r n to <<<"$(rows "$root")"
        printf "  %-15s %4d/%-4d rows  %3d%%  (%d timed out)%s\n" "$name" "$n" "$expected" $((100*n/expected)) "$to" \
          "$([ "$n" -ge "$expected" ] && echo '  DONE' || echo '')"
      else
        printf "  %-15s    not started\n" "$name"
      fi
    done
    echo "  current: ${CURRENT:-none}  attempt ${ATTEMPT:-0}/$MAX_ATTEMPTS"
  } > "$PROGRESS.tmp" && mv "$PROGRESS.tmp" "$PROGRESS"
}

ticker() { while true; do report; sleep 60; done; }
CURRENT=none; ATTEMPT=0
ticker & TICK=$!
trap 'kill $TICK 2>/dev/null' EXIT INT TERM

for spec in "${RUNS[@]}"; do
  IFS='|' read -r name sub root expected <<<"$spec"
  CURRENT=$name; ATTEMPT=0
  while true; do
    read -r n to <<<"$( [ -d "$root/results" ] && rows "$root" || echo "0 0" )"
    if [ "$n" -ge "$expected" ]; then
      echo "[$(date '+%F %T')] $name COMPLETE ($n/$expected rows, $to timed out)"; break
    fi
    ATTEMPT=$((ATTEMPT+1))
    if [ "$ATTEMPT" -gt "$MAX_ATTEMPTS" ]; then
      echo "[$(date '+%F %T')] $name GAVE UP after $MAX_ATTEMPTS attempts at $n/$expected rows"; break
    fi
    # never collide with orphaned grid workers still finishing useful work
    while pgrep -f '[r]un_experiment_grid.py' >/dev/null; do sleep 60; done
    echo "[$(date '+%F %T')] $name attempt $ATTEMPT (have $n/$expected rows)"
    ./experiments/run_reruns.sh "$sub"
    rc=$?
    echo "[$(date '+%F %T')] $name launcher exited rc=$rc"
    [ $rc -ne 0 ] && sleep $BACKOFF
  done
  report
done
CURRENT="all done"; report
echo "[$(date '+%F %T')] SUPERVISOR FINISHED"
