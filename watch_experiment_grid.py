#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from artifact_paths import artifacts_root, repo_root, resolve_repo_path


STOP = False


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_line(path: Path, message: str):
    line = f"[{now_ts()}] {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def on_signal(signum, _frame):
    global STOP
    STOP = True
    print(f"[{now_ts()}] Received signal {signum}. Stopping watchdog...", flush=True)


def load_config(path: str):
    with open(resolve_repo_path(path), "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_decimal(value) -> str:
    return str(value).replace(".", "_")


def semantics_list(config: dict):
    value = config["semantics"]
    if isinstance(value, str):
        return [value]
    return [str(x) for x in value]


def read_lock_pid(lock_path: Path):
    if not lock_path.exists():
        return None
    try:
        return int(lock_path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_pid_alive(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def process_table():
    proc = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    rows = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        rows.append((pid, parts[1]))
    return rows


def latest_launcher_log(logs_dir: Path, run_name: str):
    latest_link = logs_dir / f"{run_name}_latest.log"
    if not latest_link.exists():
        return None
    if latest_link.is_symlink():
        try:
            return (latest_link.parent / os.readlink(latest_link)).resolve()
        except Exception:
            return latest_link.resolve()
    return latest_link.resolve()


def summarize_failure_reason(logs_dir: Path, run_name: str):
    launcher_log = latest_launcher_log(logs_dir, run_name)
    if launcher_log is None or not launcher_log.exists():
        return "no previous launcher log found"
    try:
        with open(launcher_log, "r", encoding="utf-8", errors="replace") as f:
            tail = [x.rstrip("\n") for x in f.readlines()[-240:]]
    except Exception:
        return f"unable to read {launcher_log.name}"

    fail_lines = [x for x in tail if "[FAIL]" in x or "[ERR ]" in x]
    if fail_lines:
        return fail_lines[-1].strip()
    for line in reversed(tail):
        if line.strip():
            return f"last log line: {line.strip()}"
    return "launcher log empty"


def condition_status(results_dir: Path, iterations: int, rows_per_iteration: int):
    rows = 0
    csv_files = sorted(results_dir.glob("results_*.csv"))
    for path in csv_files:
        try:
            with open(path, "r", newline="") as f:
                reader = csv.reader(f, delimiter=";")
                next(reader, None)
                rows += sum(1 for row in reader if row)
        except Exception:
            pass
    expected_rows = iterations * rows_per_iteration
    if len(csv_files) >= iterations and rows >= expected_rows:
        return "complete", rows
    if csv_files or rows:
        return "partial", rows
    return "missing", rows


def completion_snapshot(artifact_root: Path, config: dict, iterations: int):
    results_template = config.get(
        "results_dir_template",
        "{semantics}_partial_{partial_token}_noise_{noise_token}_ratio_{ratio_token}",
    )
    semantics_values = semantics_list(config)
    ratio_token = str(config.get("ratio_token", "1"))
    partials = [float(x) for x in config["partials"]]
    noises = [float(x) for x in config["noises"]]
    rows_per_iteration = int(config.get("rows_per_iteration", len(config["f_values"])))

    complete = 0
    partial = 0
    missing = 0
    total_rows = 0
    for semantics in semantics_values:
        for part in partials:
            for noise in noises:
                dirname = results_template.format(
                    semantics=semantics,
                    partial_token=sanitize_decimal(part),
                    noise_token=sanitize_decimal(noise),
                    ratio_token=ratio_token,
                    partial=part,
                    noise=noise,
                )
                status, rows = condition_status(artifact_root / "results" / dirname, iterations, rows_per_iteration)
                total_rows += rows
                if status == "complete":
                    complete += 1
                elif status == "partial":
                    partial += 1
                else:
                    missing += 1
    return complete, partial, missing, total_rows


def is_full_run_complete(artifact_root: Path, config: dict, iterations: int):
    partials = [float(x) for x in config["partials"]]
    noises = [float(x) for x in config["noises"]]
    complete, partial, missing, _ = completion_snapshot(artifact_root, config, iterations)
    return complete == len(semantics_list(config)) * len(partials) * len(noises) and partial == 0 and missing == 0


def find_active_processes(rows, self_pid: int, config: dict, artifact_root: Path, config_path: Path):
    semantics_values = semantics_list(config)
    train_prefix = config.get("train_run_dir_prefix", config["run_name"])
    train_marker = str((artifact_root / "train" / f"{train_prefix}_").resolve())
    config_marker = str(config_path.resolve())
    config_basename = config_path.name

    active = []
    for pid, cmd in rows:
        if pid == self_pid:
            continue
        if (
            (
                ("-m arglas" in cmd or "arglas benchmark run" in cmd)
                and " benchmark run " in f" {cmd} "
                and (config_marker in cmd or config_basename in cmd)
            )
            or ("run_experiment_grid.py" in cmd and "--config" in cmd and config_marker in cmd)
        ):
            active.append((pid, "launcher", cmd))
            continue
        if (
            (
                "train_test.py" in cmd
                or (
                    ("-m arglas" in cmd or "arglas learn" in cmd)
                    and " learn " in f" {cmd} "
                )
            )
            and any(f"--semantics {semantics}" in cmd for semantics in semantics_values)
            and train_marker in cmd
        ):
            active.append((pid, "worker", cmd))
            continue
        if "ILASP --version=4" in cmd and train_marker in cmd:
            active.append((pid, "ilasp", cmd))
            continue
    return active


def expected_active_workers(config: dict, complete: int, partial: int, missing: int, workers: int):
    total_conditions = len(semantics_list(config)) * len(config["partials"]) * len(config["noises"])
    remaining = max(0, total_conditions - complete)
    if partial > 0:
        remaining = max(remaining, partial)
    return min(workers, remaining)


def terminate_processes(processes):
    for pid, _kind, _cmd in processes:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    time.sleep(2)
    for pid, _kind, _cmd in processes:
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def write_status_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def generate_progress_plots(repo_root_dir: Path, artifact_root: Path, config_path: Path):
    env = os.environ.copy()
    env["FABIO_ARTIFACTS_ROOT"] = str(artifact_root)
    proc = subprocess.run(
        [
            sys.executable,
            str(repo_root_dir / "plot_benchmark_progress.py"),
            "--config",
            str(config_path),
        ],
        cwd=str(repo_root_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or f"plotting failed rc={proc.returncode}")
    return proc.stdout.strip().splitlines()[-1].strip()


def spawn_launcher(repo_root_dir: Path, artifact_root: Path, config: dict, config_path: Path, workers: int):
    logs_dir = artifact_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_log = logs_dir / f"watchdog_restart_{config['run_name']}_{run_ts}.out"
    env = os.environ.copy()
    env["WORKERS"] = str(workers)
    env["FABIO_ARTIFACTS_ROOT"] = str(artifact_root)
    with open(out_log, "a", encoding="utf-8") as out_f:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "arglas",
                "benchmark",
                "run",
                "--config",
                str(config_path),
            ],
            cwd=str(repo_root_dir),
            stdout=out_f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
    return proc.pid, out_log


def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Generic experiment-grid watchdog.",
        add_help=add_help,
    )
    parser.add_argument("--config", required=True, help="Path to JSON run config.")
    parser.add_argument("--interval_seconds", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--once", action="store_true")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    config_path = Path(resolve_repo_path(args.config)).resolve()
    config = load_config(str(config_path))
    repo_root_dir = Path(repo_root())
    artifact_root = Path(artifacts_root())
    run_name = config["run_name"]
    display_name = config.get("display_name", run_name)
    interval_seconds = args.interval_seconds or int(config.get("watch_interval_seconds", 3600))
    workers = args.workers or int(config.get("workers", 1))
    iterations = args.iterations or int(config.get("iterations", 1))
    plot_interval_seconds = int(config.get("plot_interval_seconds", interval_seconds))
    max_consecutive_restarts = int(config.get("max_consecutive_restarts", 3))
    max_worker_shortfall_checks = int(config.get("max_worker_shortfall_checks", 2))

    lock_path = artifact_root / "logs" / f"watch_{run_name}.pid"
    event_log = artifact_root / "logs" / f"watch_{run_name}_events.log"
    status_json = artifact_root / "logs" / f"watch_{run_name}_status.json"

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be > 0")
    if workers <= 0:
        raise ValueError("workers must be > 0")
    if iterations <= 0:
        raise ValueError("iterations must be > 0")

    existing_pid = read_lock_pid(lock_path)
    if existing_pid and existing_pid != os.getpid() and is_pid_alive(existing_pid):
        log_line(event_log, f"[SKIP] {display_name} watchdog already active (pid={existing_pid}).")
        return 1

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    log_line(
        event_log,
        f"[START] {display_name} watchdog active (pid={os.getpid()}, interval={interval_seconds}s, workers={workers}, plot_interval={plot_interval_seconds}s).",
    )

    last_plot_at = 0.0
    consecutive_restarts = 0
    consecutive_worker_shortfalls = 0
    last_total_rows = None

    try:
        while not STOP:
            complete, partial, missing, total_rows = completion_snapshot(artifact_root, config, iterations)
            if is_full_run_complete(artifact_root, config, iterations):
                log_line(event_log, f"[DONE ] {display_name} complete (conditions={complete}, rows={total_rows}).")
                break

            rows = process_table()
            active = find_active_processes(rows, os.getpid(), config, artifact_root, config_path)
            active_workers = [item for item in active if item[1] == "worker"]
            active_ilasp = [item for item in active if item[1] == "ilasp"]
            target_workers = expected_active_workers(config, complete, partial, missing, workers)
            launcher_lock = artifact_root / "logs" / f"{run_name}.lock"
            launcher_pid = read_lock_pid(launcher_lock)
            if is_pid_alive(launcher_pid) and launcher_pid not in {pid for pid, _, _ in active}:
                active.append((launcher_pid, "launcher_lock", f"pid={launcher_pid} via {launcher_lock.name}"))
            if active:
                pids = ", ".join(str(x[0]) for x in active[:8])
                if len(active) > 8:
                    pids += ", ..."
                log_line(
                    event_log,
                    f"[OK  ] Active run detected ({len(active)} process(es)): {pids} | workers={len(active_workers)}/{target_workers} ilasp={len(active_ilasp)} | complete={complete} partial={partial} missing={missing} rows={total_rows}",
                )
                if target_workers > 0 and len(active_workers) < target_workers:
                    consecutive_worker_shortfalls += 1
                    log_line(
                        event_log,
                        f"[WARN] Worker shortfall detected ({len(active_workers)}/{target_workers}) "
                        f"check={consecutive_worker_shortfalls}/{max_worker_shortfall_checks}",
                    )
                    if consecutive_worker_shortfalls >= max_worker_shortfall_checks:
                        reason = (
                            f"worker shortfall persisted for {consecutive_worker_shortfalls} checks "
                            f"({len(active_workers)}/{target_workers})"
                        )
                        log_line(event_log, f"[FAIL] {reason}; restarting run processes.")
                        terminate_processes(active)
                        active = []
                else:
                    consecutive_worker_shortfalls = 0
            else:
                reason = summarize_failure_reason(artifact_root / "logs", run_name)
                log_line(
                    event_log,
                    f"[FAIL] No active launcher/workers. Reason summary: {reason} | complete={complete} partial={partial} missing={missing} rows={total_rows}",
                )
            if not active:
                consecutive_restarts += 1
                if consecutive_restarts > max_consecutive_restarts:
                    log_line(
                        event_log,
                        f"[RED ] Restart threshold exceeded ({consecutive_restarts-1}>{max_consecutive_restarts}). Stopping watchdog without relaunch.",
                    )
                    break
                pid, out_log = spawn_launcher(repo_root_dir, artifact_root, config, config_path, workers)
                log_line(event_log, f"[RESTART] Started launcher pid={pid}, out_log={out_log}")
            else:
                if last_total_rows is None or total_rows > last_total_rows:
                    consecutive_restarts = 0

            now = time.time()
            latest_plot_dir = None
            if (now - last_plot_at) >= plot_interval_seconds or args.once:
                try:
                    latest_plot_dir = generate_progress_plots(repo_root_dir, artifact_root, config_path)
                    log_line(event_log, f"[PLOT] Progress plots refreshed: {latest_plot_dir}")
                    last_plot_at = now
                except Exception as exc:
                    log_line(event_log, f"[WARN] Plot refresh failed: {exc}")

            write_status_json(
                status_json,
                {
                    "timestamp": now_ts(),
                    "display_name": display_name,
                    "run_name": run_name,
                    "complete_conditions": complete,
                    "partial_conditions": partial,
                    "missing_conditions": missing,
                    "total_rows": total_rows,
                    "expected_workers": target_workers,
                    "active_processes": [
                        {"pid": pid, "kind": kind, "command": cmd}
                        for pid, kind, cmd in active
                    ],
                    "consecutive_restarts": consecutive_restarts,
                    "consecutive_worker_shortfalls": consecutive_worker_shortfalls,
                    "latest_plot_dir": latest_plot_dir,
                },
            )
            last_total_rows = total_rows

            if args.once:
                break

            sleep_left = interval_seconds
            while sleep_left > 0 and not STOP:
                time.sleep(min(1, sleep_left))
                sleep_left -= 1
    finally:
        try:
            if read_lock_pid(lock_path) == os.getpid():
                lock_path.unlink(missing_ok=True)
        except Exception:
            pass
        log_line(event_log, f"[STOP] {display_name} watchdog stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
