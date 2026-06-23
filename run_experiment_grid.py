#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from artifact_paths import artifacts_root, repo_root, resolve_repo_path


BOOL_TRUE = {"1", "true", "yes", "on"}
BOOL_FALSE = {"0", "false", "no", "off"}


def now_ts():
    return subprocess.check_output(["date", "+%Y-%m-%d %H:%M:%S %Z"], text=True).strip()


def log_line(path: Path, message: str, lock: Optional[threading.Lock] = None):
    line = f"[{now_ts()}] {message}"
    if lock is None:
        print(line, flush=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return
    with lock:
        print(line, flush=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def load_config(path: str):
    with open(resolve_repo_path(path), "r", encoding="utf-8") as f:
        return json.load(f)


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    return int(raw)


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    return float(raw)


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    lowered = raw.strip().lower()
    if lowered in BOOL_TRUE:
        return True
    if lowered in BOOL_FALSE:
        return False
    raise ValueError(f"Invalid boolean env {name}={raw!r}")


def sanitize_decimal(value) -> str:
    return str(value).replace(".", "_")


def stable_seed_from_parts(*parts) -> int:
    blob = "||".join(str(part) for part in parts)
    return int(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16], 16)


def partial_suffix(partial: float) -> str:
    return "full" if abs(float(partial) - 1.0) < 1e-9 else f"partial_{partial}"


def pick_python_bin(root_dir: Path, explicit: Optional[str]) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    env_python = os.environ.get("PYTHON_BIN")
    if env_python:
        candidates.append(env_python)
    candidates.extend(
        [
            str(root_dir / ".venv" / "bin" / "python"),
            str(root_dir / ".venv311" / "bin" / "python"),
            "python3",
            "python",
        ]
    )

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            proc = subprocess.run(
                [candidate, "-c", "import clingo"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except FileNotFoundError:
            continue
        if proc.returncode == 0:
            return candidate
    raise RuntimeError("No Python interpreter with clingo available.")


def count_labelled_examples(dataset_dir: Path, semantics: str):
    if not dataset_dir.exists():
        return 0, 0
    pos = 0
    neg = 0
    for path in dataset_dir.glob("*.lp"):
        name = path.name
        if f"_{semantics}_POS_" in name:
            pos += 1
        elif f"_{semantics}_NEG_" in name:
            neg += 1
    return pos, neg


def count_aafs(aaf_dir: Path):
    counts = {}
    if not aaf_dir.exists():
        return counts
    for path in aaf_dir.glob("aaf_*_*.lp"):
        parts = path.stem.split("_")
        if len(parts) < 3:
            continue
        try:
            n_args = int(parts[1])
        except ValueError:
            continue
        counts[n_args] = counts.get(n_args, 0) + 1
    return counts


class ExperimentRunner:
    def __init__(self, config: dict):
        self.repo_root = Path(repo_root())
        self.artifact_root = Path(artifacts_root())
        self.config = config
        self.run_name = config["run_name"]
        self.display_name = config.get("display_name", self.run_name)
        semantics_value = config["semantics"]
        if isinstance(semantics_value, str):
            self.semantics_list = [semantics_value]
        else:
            self.semantics_list = [str(x) for x in semantics_value]
        if not self.semantics_list:
            raise ValueError("config.semantics must contain at least one semantics label")
        self.semantics = self.semantics_list[0]
        self.partials = [float(x) for x in config["partials"]]
        self.noises = [float(x) for x in config["noises"]]
        self.f_values = [int(x) for x in config["f_values"]]
        self.f_neg_values = [int(x) for x in config.get("f_neg_values", config["f_values"])]
        self.workers = env_int("WORKERS", int(config.get("workers", 1)))
        self.iterations = env_int("ITERATIONS", int(config.get("iterations", 1)))
        self.train_timeout_seconds = env_int(
            "TRAIN_TIMEOUT_SECONDS",
            int(config.get("train_timeout_seconds", 1200)),
        )
        self.test_par_timeout_seconds = env_int(
            "TEST_PAR_TIMEOUT_SECONDS",
            int(config.get("test_par_timeout_seconds", 1200)),
        )
        self.par2_factor = env_float("PAR2_FACTOR", float(config.get("par2_factor", 2.0)))
        self.overwrite_existing_iterations = env_bool(
            "OVERWRITE_EXISTING_ITERATIONS",
            bool(config.get("overwrite_existing_iterations", False)),
        )
        self.dry_run = env_bool("DRY_RUN", bool(config.get("dry_run", False)))
        self.allow_empty = bool(config.get("allow_empty", True))
        self.negative_policy = config.get("negative_policy", "oracle_neg")
        self.negative_flip_k = int(config.get("negative_flip_k", 1))
        self.eval_match_policy = config.get("eval_match_policy", "full_exact_model")
        self.test_set_policy = config.get("test_set_policy", "fixed_balanced_holdout")
        self.test_examples_per_class = config.get("test_examples_per_class")
        self.test_sampling_seed = int(config.get("test_sampling_seed", 0))
        self.task_sampling_seed_base = int(config.get("task_sampling_seed_base", 0))
        self.label_seed_base = int(config.get("label_seed_base", 0))
        self.master_seed = int(config.get("master_seed", 0))
        self.aaf_generation = config.get("aaf_generation")
        self.results_dir_template = config.get(
            "results_dir_template",
            "{semantics}_partial_{partial_token}_noise_{noise_token}_ratio_{ratio_token}",
        )
        self.ratio_token = str(config.get("ratio_token", "1"))
        self.rows_per_iteration = int(config.get("rows_per_iteration", len(self.f_values)))
        self.train_run_dir_prefix = config.get("train_run_dir_prefix", self.run_name)
        self.train_output_run_dir_prefix = config.get("train_output_run_dir_prefix", self.run_name)
        self.labelled_requirements = config.get("labelled_requirements", {"min_pos": 0, "min_neg": 0})
        self.extra_train_test_args = [str(x) for x in config.get("train_test_extra_args", [])]
        self.plot_interval_seconds = int(config.get("plot_interval_seconds", config.get("watch_interval_seconds", 3600)))
        self.python_bin = pick_python_bin(self.repo_root, config.get("python_bin"))
        self.child_env = os.environ.copy()
        self.child_env["FABIO_ARTIFACTS_ROOT"] = str(self.artifact_root)
        self.run_ts = subprocess.check_output(["date", "+%Y%m%d_%H%M%S"], text=True).strip()
        self.logs_dir = self.artifact_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.run_log = self.logs_dir / f"{self.run_name}_{self.run_ts}.log"
        self.latest_log = self.logs_dir / f"{self.run_name}_latest.log"
        self.lock_file = self.logs_dir / f"{self.run_name}.lock"
        self.train_dir = self.artifact_root / "train" / f"{self.train_run_dir_prefix}_{self.run_ts}"
        self.train_output_dir = self.artifact_root / "train_output" / f"{self.train_output_run_dir_prefix}_{self.run_ts}"
        self.aaf_dir = self.artifact_root / "aafs"
        self.log_lock = threading.Lock()
        self.failure_lock = threading.Lock()
        self.failures = []
        self.stop_requested = threading.Event()

    def log(self, message: str):
        log_line(self.run_log, message, lock=self.log_lock)

    def acquire_lock(self):
        owner = None
        if self.lock_file.exists():
            try:
                owner = int(self.lock_file.read_text(encoding="utf-8").strip())
            except Exception:
                owner = None
            if owner and owner != os.getpid():
                try:
                    os.kill(owner, 0)
                except OSError:
                    self.lock_file.unlink(missing_ok=True)
                else:
                    raise RuntimeError(
                        f"Another launcher is already running for {self.run_name} (pid={owner})."
                    )
        self.lock_file.write_text(str(os.getpid()), encoding="utf-8")

    def release_lock(self):
        if not self.lock_file.exists():
            return
        try:
            owner = int(self.lock_file.read_text(encoding="utf-8").strip())
        except Exception:
            owner = None
        if owner in (None, os.getpid()):
            self.lock_file.unlink(missing_ok=True)

    def update_latest_log_link(self):
        self.latest_log.unlink(missing_ok=True)
        self.latest_log.symlink_to(self.run_log.name)

    def write_run_metadata(self):
        metadata = dict(self.config)
        metadata["_resolved"] = {
            "repo_root": str(self.repo_root),
            "artifact_root": str(self.artifact_root),
            "python_bin": self.python_bin,
            "run_ts": self.run_ts,
            "semantics": self.semantics_list,
            "workers": self.workers,
            "iterations": self.iterations,
            "test_sampling_seed": self.test_sampling_seed,
            "task_sampling_seed_base": self.task_sampling_seed_base,
            "label_seed_base": self.label_seed_base,
            "master_seed": self.master_seed,
        }
        out_path = self.logs_dir / f"{self.run_name}_{self.run_ts}_config.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
        return out_path

    def labelled_requirement_for(self, semantics: str):
        req = self.labelled_requirements
        if "min_pos" in req or "min_neg" in req:
            return {
                "min_pos": int(req.get("min_pos", 0)),
                "min_neg": int(req.get("min_neg", 0)),
            }
        if semantics in req:
            entry = req[semantics]
        else:
            entry = req.get("default", {})
        return {
            "min_pos": int(entry.get("min_pos", 0)),
            "min_neg": int(entry.get("min_neg", 0)),
        }

    def ensure_aafs(self):
        if not self.aaf_generation:
            if not self.aaf_dir.exists():
                raise RuntimeError(
                    f"AAF directory missing and no aaf_generation block configured: {self.aaf_dir}"
                )
            return
        nmin = int(self.aaf_generation["nmin"])
        nmax = int(self.aaf_generation["nmax"])
        count_per_size = int(self.aaf_generation["count_per_size"])
        seed = int(self.aaf_generation.get("seed", self.master_seed))
        existing = count_aafs(self.aaf_dir)
        expected_sizes = list(range(nmin, nmax + 1))
        if all(existing.get(n, 0) >= count_per_size for n in expected_sizes):
            self.log(
                "[SKIP] AAF generation already satisfied: "
                + " ".join(f"n={n}:{existing.get(n, 0)}" for n in expected_sizes)
            )
            return
        if any(existing.get(n, 0) > 0 for n in expected_sizes):
            raise RuntimeError(
                f"AAF directory {self.aaf_dir} contains a partial dataset; refusing to mix old/new AAFs."
            )
        self.aaf_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.python_bin,
            "-m",
            "arglas",
            "generate-aafs",
            str(nmin),
            str(nmax),
            str(count_per_size),
            "--output_dir",
            str(self.aaf_dir),
            "--seed",
            str(seed),
            "--quiet",
        ]
        self.log(
            f"[GEN ] AAFs n={nmin}..{nmax} count_per_size={count_per_size} seed={seed} -> {self.aaf_dir}"
        )
        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            env=self.child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.returncode != 0:
            self.log(proc.stdout.rstrip())
            raise RuntimeError(f"AAF generation failed rc={proc.returncode}")
        if proc.stdout.strip():
            self.log(proc.stdout.rstrip())

    def ensure_labelled_dataset(self, semantics: str, partial: float):
        dataset_dir = self.artifact_root / "labelled" / f"labelled_{semantics}_{partial_suffix(partial)}"
        pos_count, neg_count = count_labelled_examples(dataset_dir, semantics)
        req = self.labelled_requirement_for(semantics)
        min_pos = req["min_pos"]
        min_neg = req["min_neg"]
        if pos_count >= min_pos and neg_count >= min_neg:
            self.log(
                f"[SKIP] labelled {semantics} partial={partial} already has POS={pos_count} NEG={neg_count}"
            )
            return

        self.log(
            f"[GEN ] labelled {semantics} partial={partial} (POS={pos_count} NEG={neg_count})"
        )
        cmd = [
            self.python_bin,
            "-m",
            "arglas",
            "label",
            "--input_dir",
            str(self.aaf_dir),
            "--base_output_dir",
            str(self.artifact_root / "labelled"),
            "--semantics",
            semantics,
            "--p_partial",
            str(partial),
            "--seed",
            str(stable_seed_from_parts("label", self.label_seed_base, semantics, partial)),
        ]
        if self.allow_empty:
            cmd.append("--allow_empty")
        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            env=self.child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.returncode != 0:
            self.log(proc.stdout.rstrip())
            raise RuntimeError(
                f"Label generation failed for {semantics} partial={partial} rc={proc.returncode}"
            )
        if proc.stdout.strip():
            self.log(proc.stdout.rstrip())

    def build_jobs(self):
        # Schedule noise-ascending, then partial, then semantics-interleaved.
        # Rationale (audit): the previous semantics-outermost order starved GRD
        # (it sat at the tail of every worker queue and never ran). Ordering by
        # ascending noise runs the cheap noise=0 cells first across ALL semantics
        # (so every semantics makes early progress and any cell-level failure
        # surfaces within minutes), with the expensive high-noise cells last.
        jobs = [
            (semantics, partial, noise)
            for semantics in self.semantics_list
            for partial in self.partials
            for noise in self.noises
        ]
        jobs.sort(key=lambda j: (j[2], j[1], self.semantics_list.index(j[0])))
        return jobs

    def results_dir_for_job(self, semantics: str, partial: float, noise: float) -> Path:
        dirname = self.results_dir_template.format(
            semantics=semantics,
            partial_token=sanitize_decimal(partial),
            noise_token=sanitize_decimal(noise),
            ratio_token=self.ratio_token,
            partial=partial,
            noise=noise,
        )
        return self.artifact_root / "results" / dirname

    def train_test_cmd(self, semantics: str, partial: float, noise: float, results_dir: Path):
        cmd = [
            self.python_bin,
            "-m",
            "arglas",
            "learn",
            "--semantics",
            semantics,
            "--partial",
            str(partial),
            "--f_values",
            *[str(x) for x in self.f_values],
            "--f_neg_values",
            *[str(x) for x in self.f_neg_values],
            "--n_values",
            str(noise),
            "--iterations",
            str(self.iterations),
            "--base_output_dir",
            str(self.artifact_root / "labelled"),
            "--train_dir",
            str(self.train_dir),
            "--train_output_dir",
            str(self.train_output_dir),
            "--results_dir",
            str(results_dir),
            "--no_prefix",
            "--negative_policy",
            self.negative_policy,
            "--negative_flip_k",
            str(self.negative_flip_k),
            "--eval_match_policy",
            self.eval_match_policy,
            "--test_set_policy",
            self.test_set_policy,
            "--test_sampling_seed",
            str(self.test_sampling_seed),
            "--task_sampling_seed_base",
            str(self.task_sampling_seed_base),
            "--train_timeout_seconds",
            str(self.train_timeout_seconds),
            "--test_par_timeout_seconds",
            str(self.test_par_timeout_seconds),
            "--par2_factor",
            str(self.par2_factor),
        ]
        if self.test_examples_per_class is not None:
            cmd.extend(["--test_examples_per_class", str(self.test_examples_per_class)])
        if self.overwrite_existing_iterations:
            cmd.append("--overwrite_existing_iterations")
        if self.dry_run:
            cmd.append("--dry_run")
        cmd.extend(self.extra_train_test_args)
        return cmd

    def worker_loop(self, worker_id: int, jobs: list[tuple[float, float]], worker_log: Path):
        assigned = [job for idx, job in enumerate(jobs) if idx % self.workers == (worker_id - 1)]
        ran = 0
        failed = 0
        worker_log.parent.mkdir(parents=True, exist_ok=True)
        with open(worker_log, "a", encoding="utf-8") as wf:
            for semantics, partial, noise in assigned:
                if self.stop_requested.is_set():
                    break
                results_dir = self.results_dir_for_job(semantics, partial, noise)
                results_dir.mkdir(parents=True, exist_ok=True)
                self.train_dir.mkdir(parents=True, exist_ok=True)
                self.train_output_dir.mkdir(parents=True, exist_ok=True)
                self.log(
                    f"[W{worker_id}] [RUN ] {semantics} partial={partial} noise={noise} -> {results_dir}"
                )
                print(f"[{now_ts()}] [RUN ] semantics={semantics} partial={partial} noise={noise}", file=wf, flush=True)
                cmd = self.train_test_cmd(semantics, partial, noise, results_dir)
                proc = subprocess.run(
                    cmd,
                    cwd=str(self.repo_root),
                    env=self.child_env,
                    stdout=wf,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if proc.returncode != 0:
                    failed += 1
                    # Record-and-continue (audit defect #7). A single bad cell must
                    # NOT abort a multi-day campaign: previously this set
                    # stop_requested and broke ALL workers, after which the watchdog
                    # RED-halted on a deterministic poison cell. Now we log+record
                    # the failure and move on to the next assigned job. run() still
                    # returns non-zero at the end if any cell failed, so the
                    # operator still sees the failure list. External SIGTERM still
                    # stops cleanly via the stop_requested check at the loop top.
                    self.log(
                        f"[SKIP] [W{worker_id}] {semantics} partial={partial} noise={noise} rc={proc.returncode} (recorded, continuing)"
                    )
                    with self.failure_lock:
                        self.failures.append((worker_id, semantics, partial, noise, proc.returncode, str(worker_log)))
                    continue
                ran += 1
                self.log(f"[W{worker_id}] [OK  ] {semantics} partial={partial} noise={noise}")
        self.log(f"[W{worker_id}] done (ran={ran}, failed={failed})")

    def run(self) -> int:
        if self.workers < 1:
            raise ValueError("workers must be >= 1")
        self.acquire_lock()
        self.update_latest_log_link()
        try:
            self.log(f"[START] {self.display_name} with {self.workers} workers")
            config_path = self.write_run_metadata()
            self.log(f"[CONF] {config_path}")
            self.ensure_aafs()
            self.log(f"        semantics={' '.join(self.semantics_list)}")
            self.log(f"        partials={' '.join(str(x) for x in self.partials)}")
            self.log(f"        noises={' '.join(str(x) for x in self.noises)}")
            self.log(
                f"        totals via pos={' '.join(str(x) for x in self.f_values)} neg={' '.join(str(x) for x in self.f_neg_values)}"
            )
            self.log(f"        iterations={self.iterations}")
            self.log(f"        master_seed={self.master_seed}")
            self.log(f"        label_seed_base={self.label_seed_base}")
            self.log(f"        task_sampling_seed_base={self.task_sampling_seed_base}")
            self.log(f"        test_sampling_seed={self.test_sampling_seed}")
            self.log(f"        overwrite_existing_iterations={int(self.overwrite_existing_iterations)}")
            self.log(f"        dry_run={int(self.dry_run)}")

            for semantics in self.semantics_list:
                for partial in self.partials:
                    self.ensure_labelled_dataset(semantics, partial)

            jobs = self.build_jobs()
            worker_logs = []
            threads = []
            for worker_id in range(1, self.workers + 1):
                worker_log = self.logs_dir / f"{self.run_name}_{self.run_ts}_worker{worker_id}.log"
                worker_logs.append(str(worker_log))
                thread = threading.Thread(
                    target=self.worker_loop,
                    args=(worker_id, jobs, worker_log),
                    daemon=False,
                )
                thread.start()
                threads.append(thread)

            self.log(f"[WLOGS] {' '.join(worker_logs)}")
            for thread in threads:
                thread.join()

            if self.failures:
                self.log(f"[FAIL] {self.display_name} failed (see worker logs).")
                return 1

            self.log(f"[DONE ] {self.display_name} completed successfully")
            return 0
        finally:
            self.release_lock()


def build_parser(add_help=True):
    parser = argparse.ArgumentParser(
        description="Generic experiment-grid launcher.",
        add_help=add_help,
    )
    parser.add_argument("--config", required=True, help="Path to JSON run config.")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    config = load_config(args.config)
    runner = ExperimentRunner(config)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
