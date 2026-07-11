#!/usr/bin/env python3
"""Progress bar for an ArgLAS benchmark campaign.

Reads the run config + the artifact root's results/ tree and prints overall
completion, per-noise breakdown, run health (succeeded / timed-out / failed) and
rolling quality (accuracy / MCC). Completion is computed via the SAME logic the
watchdog uses (watch_experiment_grid.completion_snapshot), so the bar and the
supervisor always agree on what "done" means.

  one-shot:  python3 -m arglas benchmark progress --config experiments/run_configs/<cfg>.json
  live:      python3 -m arglas benchmark progress --config experiments/run_configs/<cfg>.json --watch 30
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")))
import argparse
import csv
import glob
import os
import sys
import time
from pathlib import Path

from arglas.artifact_paths import artifacts_root
from watch_experiment_grid import completion_snapshot, load_config, semantics_list


def _fmt_dur(secs):
    secs = int(max(0, secs))
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def _bar(frac, width=34):
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    return "█" * n + "░" * (width - n)


def _scan_rows(results_root: Path):
    rows = []
    for f in glob.glob(str(results_root / "*" / "results_*.csv")):
        try:
            with open(f, newline="") as fh:
                rows.extend(csv.DictReader(fh, delimiter=";"))
        except Exception:
            pass
    return rows


def _fmean(rows, key):
    vals = []
    for r in rows:
        v = r.get(key)
        if v not in (None, ""):
            try:
                vals.append(float(v))
            except ValueError:
                pass
    return (sum(vals) / len(vals)) if vals else float("nan")


def render(config, root):
    root = Path(root)
    iterations = int(config.get("iterations", 1))
    rows_per_iteration = int(config.get("rows_per_iteration", len(config["f_values"])))
    sems = semantics_list(config)
    partials = [float(x) for x in config["partials"]]
    noises = sorted(float(x) for x in config["noises"])
    n_cells = len(sems) * len(partials) * len(noises)
    total = n_cells * iterations * rows_per_iteration

    complete, partial, missing, total_rows = completion_snapshot(root, config, iterations)
    rows = _scan_rows(root / "results")
    done = total_rows

    succ = [r for r in rows if r.get("ILASP_TRAIN_SUCCEEDED") == "1"]
    timed = [r for r in rows if r.get("ILASP_TRAIN_TIMED_OUT") == "1"]
    failed = [r for r in rows if r.get("ILASP_TRAIN_SUCCEEDED") == "0"]

    cells_per_noise = len(sems) * len(partials)
    exp_per_noise = cells_per_noise * iterations * rows_per_iteration
    per_noise = {}
    for n in noises:
        cnt = sum(1 for r in rows if r.get("NOISE") not in (None, "")
                  and abs(float(r["NOISE"]) - n) < 1e-9)
        per_noise[n] = (cnt, exp_per_noise)

    mtimes = [os.path.getmtime(f) for f in glob.glob(str(root / "results" / "*" / "results_*.csv"))]
    eta = ""
    if mtimes and 0 < done < total:
        elapsed = time.time() - min(mtimes)
        rate = done / elapsed if elapsed > 0 else 0
        if rate > 0:
            eta = (f" · elapsed {_fmt_dur(elapsed)} · {rate * 60:.1f} rows/min"
                   f" · ETA ~{_fmt_dur((total - done) / rate)}")

    frac = done / total if total else 0.0
    out = []
    out.append(f"ArgLAS campaign · {config.get('run_name', '?')}")
    out.append(f"  {root}")
    out.append(f"[{_bar(frac)}] {done}/{total} rows ({frac * 100:.1f}%) · "
               f"cells {complete}/{n_cells} done"
               f"{f' ({partial} partial)' if partial else ''}{eta}")
    out.append(f"  health: ok {len(succ)} · timed-out {len(timed)} · failed {len(failed)}")
    if succ:
        out.append(f"  quality (succeeded so far): acc {_fmean(succ, 'ACCURACY'):.3f} "
                   f"· MCC {_fmean(succ, 'MCC'):.3f}")
    pn = " · ".join(f"n{n:g} {c}/{e}{' ✓' if c >= e and e else ''}"
                        for n, (c, e) in per_noise.items())
    out.append(f"  by noise: {pn}")
    done_flag = total > 0 and complete == n_cells and partial == 0 and missing == 0
    if done_flag:
        out.append("  ✓ ALL CELLS COMPLETE")
    return "\n".join(out), done_flag


def main(argv=None):
    ap = argparse.ArgumentParser(prog="arglas benchmark progress",
                                 description="Progress bar for an ArgLAS benchmark campaign.")
    ap.add_argument("--config", required=True, help="Path to the run JSON config.")
    ap.add_argument("--artifacts_root", default=None,
                    help="Artifact root (default: $FABIO_ARTIFACTS_ROOT or the configured default).")
    ap.add_argument("--watch", type=float, default=0.0,
                    help="Refresh interval in seconds (0 = print once and exit).")
    args = ap.parse_args(argv)

    config = load_config(args.config)
    root = args.artifacts_root or os.environ.get("FABIO_ARTIFACTS_ROOT") or str(artifacts_root())

    while True:
        text, done_flag = render(config, root)
        if args.watch:
            sys.stdout.write("\033[2J\033[H")
        print(text, flush=True)
        if not args.watch or done_flag:
            return 0
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
