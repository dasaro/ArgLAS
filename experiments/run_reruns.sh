#!/bin/bash
# Targeted re-runs recommended by the 2026-07-17 status audit (docs/aij_paper/review_round3_todo.md).
# Each run is stop/resume-safe (kill any time; rerun the same command to resume) and lives
# in its own artifacts root, never in data/. Full guide: experiments/RERUNS.md
#
#   ./experiments/run_reruns.sh baf-anchor      [smoke]   # 120 runs, ~2-4 h wall (worst 8 h)
#   ./experiments/run_reruns.sh self-prf-recap  [smoke]   # 20 runs at a 4x cap, up to ~12 h wall
#   ./experiments/run_reruns.sh seedb           [smoke]   # 360 + 80 runs, ~1-2 h wall
#   ./experiments/run_reruns.sh status                    # row counts per re-run
#   ./experiments/run_reruns.sh collect <name>            # copy a finished run into data/<name>/
#
# Run the real thing detached:  nohup ./experiments/run_reruns.sh baf-anchor > baf_anchor.out 2>&1 &
set -u
cd "$(dirname "$0")/.."

die() { echo "[reruns] FATAL: $1" >&2; exit 1; }
CMD="${1:-}"; MODE="${2:-full}"

# ---------------------------------------------------------------- shared helpers
guard_no_grid() {
  if pgrep -f "[r]un_experiment_grid.py" >/dev/null 2>&1; then
    die "an experiment grid is already running (never edit config/ or arglas/ while it runs)"
  fi
}

seed_pool() { # $1 = committed pool dir (data/<x>/aafs), $2 = artifacts root
  if [ -z "$(ls "$2/aafs" 2>/dev/null)" ]; then
    echo "[reruns] seeding $2/aafs from the committed pool $1 ($(ls "$1" | wc -l | tr -d ' ') frameworks)"
    mkdir -p "$2" && cp -R "$1" "$2/aafs" || die "could not copy the committed pool"
  else
    echo "[reruns] pool already present in $2/aafs (resume)"
  fi
}

# Smoke = the same config shrunk to ONE cell and TWO folds in a separate *_smoke root,
# so the real root is never polluted with a partial dataset (the runner refuses to mix).
smoke_cfg() { # $1 = real config path, $2 = smoke root; prints the derived config path
  mkdir -p "$2"
  python3 - "$1" "$2" <<'PY'
import json, sys, os
src, root = sys.argv[1], sys.argv[2]
c = json.load(open(src))
c["semantics"] = c["semantics"][:1]
# keep ALL partials: the grid pre-labels every (semantics x partial) pool before scheduling,
# and the p<1 cells score their complete-information surface on the p=1.0 sibling pool
c["noises"] = c["noises"][:1]
c["f_values"] = c["f_values"][:1]; c["f_neg_values"] = c["f_neg_values"][:1]
c["iterations"] = 2
c["test_examples_per_class"] = min(c["test_examples_per_class"], 12)
c["train_timeout_seconds"] = min(c["train_timeout_seconds"], 900)
c["labelled_requirements"] = {"default": {"min_pos": 20, "min_neg": 20}}
if c.get("aaf_generation"):
    c["aaf_generation"]["count_per_size"] = 20   # 100 AAFs instead of 500 for the smoke
for k in ("run_name", "train_run_dir_prefix", "train_output_run_dir_prefix"):
    c[k] = c[k] + "_smoke"
c["display_name"] = "SMOKE: " + c["display_name"]
out = os.path.join(root, "smoke_config.json")
json.dump(c, open(out, "w"), indent=2)
print(out)
PY
}

launch() { # $1 = root, $2 = config path
  echo "===== [$(date '+%F %T')] launching $2 (root: $1) ====="
  FABIO_ARTIFACTS_ROOT="$1" python3 experiments/run_experiment_grid.py --config "$2"
  rc=$?
  [ $rc -eq 0 ] && echo "===== [$(date '+%F %T')] DONE: $2 =====" \
                || echo "===== $2 exited rc=$rc — rerun the same command to resume ====="
  return $rc
}

rows_in() { # $1 = root
  python3 - "$1" <<'PY'
import csv, glob, sys
root = sys.argv[1]
n = ok = to = 0
for f in glob.glob(f"{root}/results/**/results_*.csv", recursive=True):
    for r in csv.DictReader(open(f), delimiter=";"):
        n += 1
        ok += r.get("ILASP_TRAIN_SUCCEEDED") == "1" and r.get("ILASP_TRAIN_TIMED_OUT") != "1"
        to += r.get("ILASP_TRAIN_TIMED_OUT") == "1"
print(f"{n} rows ({ok} ok, {to} timed out)")
PY
}

# ---------------------------------------------------------------- the three re-runs
case "$CMD" in
  baf-anchor)
    guard_no_grid
    ROOT=artifacts/final_synthetic_v3_baf_anchor; CFG=experiments/run_configs/v3_baf_anchor.json
    if [ "$MODE" = "smoke" ]; then
      ROOT="${ROOT}_smoke"; seed_pool data/v3_baf/aafs "$ROOT"
      launch "$ROOT" "$(smoke_cfg "$CFG" "$ROOT")" || exit $?
      # The smoke GUARDS the BAF sibling-pool fix: every p<1 row must carry a populated
      # complete-information score (MCC_FULL), or the smoke fails.
      python3 - "$ROOT" <<'PY' || die "SMOKE FAILED: a p<1 row has an empty MCC_FULL (sibling full-pool lookup broken)"
import csv, glob, sys
root = sys.argv[1]; bad = 0
for f in sorted(glob.glob(f"{root}/results/**/results_*.csv", recursive=True)):
    for r in csv.DictReader(open(f), delimiter=";"):
        full = r["MCC_FULL"]
        print(f"  p={r['P_PARTIAL']}  MCC={r['MCC'][:6]}  MCC_FULL={full[:6] or 'EMPTY!'}  TEST_FULL_SET_POS={r['TEST_FULL_SET_POS'] or '-'}")
        if float(r["P_PARTIAL"]) < 1.0 and not full:
            bad += 1
sys.exit(1 if bad else 0)
PY
      echo "[reruns] SMOKE OK — MCC_FULL populated on every p<1 row"
      exit 0
    fi
    seed_pool data/v3_baf/aafs "$ROOT"
    launch "$ROOT" "$CFG"
    ;;

  self-prf-recap)
    guard_no_grid
    ROOT=artifacts/final_synthetic_v3_self_prf_recap; CFG=experiments/run_configs/v3_self_prf_recap.json
    if [ "$MODE" = "smoke" ]; then
      ROOT="${ROOT}_smoke"; seed_pool data/v3_self/aafs "$ROOT"
      launch "$ROOT" "$(smoke_cfg "$CFG" "$ROOT")" || exit $?
      echo "[reruns] SMOKE OK (PRF, q=0.1, one cell, 2 folds, cap 900 s)"; exit 0
    fi
    seed_pool data/v3_self/aafs "$ROOT"   # SAME 500 frameworks + SAME seeds as data/v3_self
    launch "$ROOT" "$CFG"
    ;;

  seedb)
    guard_no_grid
    ROOT=artifacts/final_synthetic_seedB
    if [ "$MODE" = "smoke" ]; then
      ROOT="${ROOT}_smoke"
      launch "$ROOT" "$(smoke_cfg experiments/run_configs/seedB_clean.json "$ROOT")" || exit $?
      echo "[reruns] SMOKE OK (fresh seed-B pool generated, STB clean, one cell, 2 folds)"; exit 0
    fi
    # both configs share the root (and hence the single fresh pool draw, seed 20260901)
    launch "$ROOT" experiments/run_configs/seedB_clean.json || exit $?
    launch "$ROOT" experiments/run_configs/seedB_noisy.json
    ;;

  status)
    for r in final_synthetic_v3_baf_anchor final_synthetic_v3_self_prf_recap final_synthetic_seedB; do
      [ -d "artifacts/$r/results" ] && echo "  $r: $(rows_in artifacts/$r)" || echo "  $r: not started"
    done
    pgrep -fl "run_experiment_grid.py" >/dev/null 2>&1 && echo "  (a grid is RUNNING)" || echo "  (no grid running)"
    ;;

  collect)
    NAME="${2:-}"; [ -n "$NAME" ] || die "usage: collect <baf_anchor|self_prf_recap|seedB>"
    case "$NAME" in
      baf_anchor)     ROOT=artifacts/final_synthetic_v3_baf_anchor ;;
      self_prf_recap) ROOT=artifacts/final_synthetic_v3_self_prf_recap ;;
      seedB)          ROOT=artifacts/final_synthetic_seedB ;;
      *) die "unknown re-run '$NAME'" ;;
    esac
    [ -d "$ROOT/results" ] || die "$ROOT has no results yet"
    DEST="data/$NAME"
    [ -e "$DEST" ] && die "$DEST already exists — remove it first if you really mean to overwrite the committed record"
    mkdir -p "$DEST"
    cp -R "$ROOT/results" "$DEST/results"
    cp -R "$ROOT/aafs" "$DEST/aafs"
    # the learned programs the derived audits address via LEARNED_MODEL_FILENAME
    [ -d "$ROOT/train_output" ] && cp -R "$ROOT/train_output" "$DEST/train_output"
    cat > "$DEST/README.md" <<EOF
# $NAME — targeted re-run (collected $(date '+%F'))

Produced by \`./experiments/run_reruns.sh\` (see experiments/RERUNS.md) with the seeded config
under experiments/run_configs/; results/ holds the per-fold rows (semicolon-delimited, same
45-column schema as data/exp1_v2), aafs/ the exact framework pool, train_output/ the learned
programs referenced by LEARNED_MODEL_FILENAME. $(rows_in "$ROOT")
EOF
    echo "[reruns] collected into $DEST — review, then: git add $DEST && git commit"
    ;;

  *)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
