#!/usr/bin/env python3
"""Verify clingo-ASPARTIX == klingo-ASPARTIX at per-instance custom depth.

Depths are loaded from a CSV produced by stats collection runs.
Checkpoint-safe:
- caches clingo baselines in clingo_rows.csv,
- appends completed comparisons in detailed_rows.csv,
- resumable with same --run-id.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pty
import re
import select
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple


SEM_FILE = {
    "ADM": "admissible.lp",
    "CMP": "complete.lp",
    "STB": "stable.lp",
    "GRD": "grounded.lp",
    "PRF": "preferred.lp",
}

VERSIONS = list("ABCDEFG")


@dataclass(frozen=True)
class Example:
    version: str
    bucket: str
    path: str


def now_ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def parse_bool(s: str) -> Optional[bool]:
    if s == "True":
        return True
    if s == "False":
        return False
    return None


def format_bool(v: Optional[bool]) -> str:
    if v is True:
        return "True"
    if v is False:
        return "False"
    return ""


def parse_models(text: str) -> Tuple[Set[FrozenSet[str]], int]:
    lines = text.splitlines()
    sets: Set[FrozenSet[str]] = set()
    answers = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Answer:"):
            answers += 1
            i += 1
            atoms_lines: List[str] = []
            while i < len(lines):
                s = lines[i].strip()
                if (
                    not s
                    or s.startswith("Answer:")
                    or "SATISFIABLE" in s
                    or "UNSATISFIABLE" in s
                    or s.startswith("Models")
                    or s.startswith("Calls")
                    or s.startswith("Time")
                    or s.startswith("CPU Time")
                ):
                    i -= 1
                    break
                atoms_lines.append(s)
                i += 1
            atoms = " ".join(atoms_lines)
            in_atoms = frozenset(re.findall(r"\bin\(([^)]+)\)", atoms))
            sets.add(in_atoms)
        i += 1
    return sets, answers


def run_cmd_pty(cmd: Sequence[str], timeout_s: float) -> Tuple[int, str, bool, float]:
    master_fd, slave_fd = pty.openpty()
    start = time.time()
    proc = subprocess.Popen(cmd, stdout=slave_fd, stderr=slave_fd)
    os.close(slave_fd)
    timed_out = False
    out = bytearray()
    try:
        while True:
            if proc.poll() is not None:
                break
            if time.time() - start > timeout_s:
                timed_out = True
                proc.kill()
                break
            r, _, _ = select.select([master_fd], [], [], 0.2)
            if master_fd in r:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out.extend(chunk)
        for _ in range(5):
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out.extend(chunk)
            else:
                break
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)
    elapsed = time.time() - start
    text = out.decode("utf-8", errors="replace")
    return proc.returncode, text, timed_out, elapsed


def run_clingo_models(
    clingo_bin: str, files: Sequence[str], timeout_s: float
) -> Tuple[Optional[bool], Set[FrozenSet[str]], int, bool, float]:
    cmd = [clingo_bin, "-n", "0", *files]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        text = proc.stdout + "\n" + proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(
            "utf-8", errors="replace"
        )
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(
            "utf-8", errors="replace"
        )
        text = out + "\n" + err
        timed_out = True
    sets, answers = parse_models(text)
    if "UNSATISFIABLE" in text:
        sat: Optional[bool] = False
    elif answers > 0 or "SATISFIABLE" in text:
        sat = True
    else:
        sat = None
    return sat, sets, answers, timed_out, time.time() - start


def run_klingo_models(
    venv_python: str,
    klingo_script: str,
    mode: str,
    depth: int,
    files: Sequence[str],
    timeout_s: float,
) -> Tuple[Optional[bool], Set[FrozenSet[str]], int, bool, bool, float, int]:
    mode_flag = f"--{mode}"
    cmd = [
        venv_python,
        klingo_script,
        mode_flag,
        "-k",
        str(depth),
        "--mode",
        "all",
        "-n",
        "0",
        *files,
    ]
    rc, text, timed_out, elapsed = run_cmd_pty(cmd, timeout_s)
    sets, answers = parse_models(text)
    has_unknown = ("UNKNOWN" in text) or timed_out or (rc not in (0, 10, 20, 30))
    if "UNSATISFIABLE" in text:
        sat: Optional[bool] = False
    elif answers > 0 or "SATISFIABLE" in text:
        sat = True
    else:
        sat = None
    return sat, sets, answers, has_unknown, timed_out, elapsed, rc


def collect_examples(base: Path) -> List[Example]:
    out: List[Example] = []
    for v in VERSIONS:
        for bucket in ("pos", "neg"):
            d = base / "Real_World_Examples" / "asp_files" / f"version{v}" / bucket
            if not d.exists():
                continue
            for p in sorted(d.glob("*.lp")):
                out.append(Example(version=v, bucket=bucket, path=str(p)))
    return out


def read_completed_keys(csv_path: Path, cols: Sequence[str]) -> Set[Tuple[str, ...]]:
    if not csv_path.exists():
        return set()
    done: Set[Tuple[str, ...]] = set()
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            done.add(tuple(row[c] for c in cols))
    return done


def append_csv(path: Path, fieldnames: Sequence[str], row: Dict[str, str]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def summarize(rows: Iterable[Dict[str, str]], group_cols: Sequence[str]) -> List[Dict[str, str]]:
    agg: Dict[Tuple[str, ...], Dict[str, float]] = {}
    for r in rows:
        key = tuple(r[c] for c in group_cols)
        a = agg.setdefault(
            key,
            {
                "n": 0.0,
                "strict_match": 0.0,
                "sat_match": 0.0,
                "unknown": 0.0,
                "timeout": 0.0,
                "klingo_elapsed_s_sum": 0.0,
                "clingo_elapsed_s_sum": 0.0,
                "depth_sum": 0.0,
            },
        )
        a["n"] += 1.0
        a["strict_match"] += 1.0 if r["strict_in_set_match"] == "True" else 0.0
        a["sat_match"] += 1.0 if r["sat_match"] == "True" else 0.0
        a["unknown"] += 1.0 if r["klingo_has_unknown"] == "True" else 0.0
        a["timeout"] += 1.0 if r["klingo_timed_out"] == "True" else 0.0
        try:
            a["klingo_elapsed_s_sum"] += float(r["klingo_elapsed_s"])
        except Exception:
            pass
        try:
            a["clingo_elapsed_s_sum"] += float(r["clingo_elapsed_s"])
        except Exception:
            pass
        try:
            a["depth_sum"] += float(r["depth"])
        except Exception:
            pass
    out: List[Dict[str, str]] = []
    for key, a in sorted(agg.items()):
        n = max(a["n"], 1.0)
        row = {c: key[i] for i, c in enumerate(group_cols)}
        row.update(
            {
                "n_examples": str(int(a["n"])),
                "strict_match_rate": f"{a['strict_match'] / n:.6f}",
                "sat_match_rate": f"{a['sat_match'] / n:.6f}",
                "unknown_rate": f"{a['unknown'] / n:.6f}",
                "timeout_rate": f"{a['timeout'] / n:.6f}",
                "avg_depth": f"{a['depth_sum'] / n:.3f}",
                "avg_clingo_elapsed_s": f"{a['clingo_elapsed_s_sum'] / n:.3f}",
                "avg_klingo_elapsed_s": f"{a['klingo_elapsed_s_sum'] / n:.3f}",
            }
        )
        out.append(row)
    return out


def load_depth_map(csv_path: Path, depth_col: str) -> Dict[Tuple[str, str], int]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Depth CSV not found: {csv_path}")
    out: Dict[Tuple[str, str], int] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        required = {"semantics", "example_path", depth_col}
        missing = required - set(r.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns in depth CSV: {sorted(missing)}")
        for row in r:
            sem = row["semantics"]
            ex = row["example_path"]
            try:
                d = int(float(row[depth_col]))
            except Exception:
                d = 0
            if d < 0:
                d = 0
            key = (sem, ex)
            if key not in out:
                out[key] = d
            else:
                out[key] = max(out[key], d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=f"verify_klingo_eq_clingo_custom_depth_{now_ts()}")
    ap.add_argument("--mode", choices=("3nd", "3nd-star", "bnm"), default="3nd")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--klingo-timeout", type=float, default=120.0)
    ap.add_argument("--clingo-timeout", type=float, default=60.0)
    ap.add_argument("--depth-csv", required=True, help="CSV path with semantics/example_path/depth_col")
    ap.add_argument("--depth-col", default="choices_n1", help="Depth column in --depth-csv")
    ap.add_argument("--base", default=".", help="Repository root")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    run_dir = base / "Real_World_Examples" / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    clingo_csv = run_dir / "clingo_rows.csv"
    detailed_csv = run_dir / "detailed_rows.csv"
    summary_depth_csv = run_dir / "summary_depth.csv"
    summary_sem_csv = run_dir / "summary_semantics.csv"
    summary_json = run_dir / "summary.json"

    depth_map = load_depth_map(Path(args.depth_csv).resolve(), args.depth_col)

    clingo_bin = os.environ.get("CLINGO_BIN") or "clingo"
    venv_python = str((base / ".venv" / "bin" / "python").resolve())
    klingo_script = str(Path("/Users/fdasaro/Desktop/klingo-codex/klingo"))

    examples = collect_examples(base)
    if not examples:
        print("No A..G examples found.", file=sys.stderr)
        return 2

    clingo_fields = [
        "version",
        "bucket",
        "example_path",
        "semantics",
        "clingo_sat",
        "clingo_models_unique",
        "clingo_answers_raw",
        "clingo_timed_out",
        "clingo_elapsed_s",
        "clingo_in_sets_json",
    ]
    done_clingo = read_completed_keys(clingo_csv, ["version", "bucket", "example_path", "semantics"])
    clingo_cache: Dict[Tuple[str, str, str, str], Tuple[Optional[bool], Set[FrozenSet[str]], float]] = {}

    if clingo_csv.exists():
        with clingo_csv.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (row["version"], row["bucket"], row["example_path"], row["semantics"])
                try:
                    sets = {
                        frozenset(s)
                        for s in json.loads(row["clingo_in_sets_json"])
                        if isinstance(s, list)
                    }
                except Exception:
                    sets = set()
                try:
                    elapsed = float(row.get("clingo_elapsed_s", "0"))
                except Exception:
                    elapsed = 0.0
                clingo_cache[key] = (parse_bool(row.get("clingo_sat", "")), sets, elapsed)

    for ex in examples:
        for sem, sem_file in SEM_FILE.items():
            key = (ex.version, ex.bucket, ex.path, sem)
            if key in done_clingo:
                continue
            sem_lp = base / "config" / "ASPARTIX" / sem_file
            sat, sets, answers, timed_out, elapsed = run_clingo_models(
                clingo_bin=clingo_bin,
                files=[str(sem_lp), ex.path],
                timeout_s=args.clingo_timeout,
            )
            row = {
                "version": ex.version,
                "bucket": ex.bucket,
                "example_path": ex.path,
                "semantics": sem,
                "clingo_sat": format_bool(sat),
                "clingo_models_unique": str(len(sets)),
                "clingo_answers_raw": str(answers),
                "clingo_timed_out": str(bool(timed_out)),
                "clingo_elapsed_s": f"{elapsed:.3f}",
                "clingo_in_sets_json": json.dumps([sorted(s) for s in sorted(sets, key=lambda x: (len(x), tuple(sorted(x))))]),
            }
            append_csv(clingo_csv, clingo_fields, row)
            clingo_cache[key] = (sat, sets, elapsed)

    detailed_fields = [
        "version",
        "bucket",
        "example_path",
        "semantics",
        "mode",
        "depth",
        "clingo_sat",
        "clingo_models_unique",
        "clingo_timed_out",
        "clingo_elapsed_s",
        "klingo_rc",
        "klingo_sat",
        "klingo_models_unique",
        "klingo_answers_raw",
        "klingo_has_unknown",
        "klingo_timed_out",
        "klingo_elapsed_s",
        "sat_match",
        "strict_in_set_match",
    ]
    done = read_completed_keys(detailed_csv, ["version", "bucket", "example_path", "semantics", "mode", "depth"])

    tasks: List[Tuple[Example, str, int]] = []
    for ex in examples:
        for sem in SEM_FILE:
            depth = depth_map.get((sem, ex.path), 0)
            key = (ex.version, ex.bucket, ex.path, sem, args.mode, str(depth))
            if key not in done:
                tasks.append((ex, sem, depth))

    print(f"[INFO] run_dir={run_dir}")
    print(f"[INFO] depth_csv={Path(args.depth_csv).resolve()} depth_col={args.depth_col}")
    print(f"[INFO] examples={len(examples)} tasks_total={len(examples) * len(SEM_FILE)} pending={len(tasks)}")
    print(f"[INFO] mode={args.mode} workers={args.workers} klingo_timeout={args.klingo_timeout}s")

    def worker(task: Tuple[Example, str, int]) -> Dict[str, str]:
        ex, sem, depth = task
        sem_lp = base / "config" / "ASPARTIX" / SEM_FILE[sem]
        key = (ex.version, ex.bucket, ex.path, sem)
        clingo_sat, clingo_sets, clingo_elapsed = clingo_cache[key]
        sat, sets, answers, has_unknown, timed_out, elapsed, rc = run_klingo_models(
            venv_python=venv_python,
            klingo_script=klingo_script,
            mode=args.mode,
            depth=depth,
            files=[str(sem_lp), ex.path],
            timeout_s=args.klingo_timeout,
        )
        sat_match = (sat is not None) and (clingo_sat is not None) and (sat == clingo_sat)
        strict_match = sat_match and (not timed_out) and (sets == clingo_sets)
        return {
            "version": ex.version,
            "bucket": ex.bucket,
            "example_path": ex.path,
            "semantics": sem,
            "mode": args.mode,
            "depth": str(depth),
            "clingo_sat": format_bool(clingo_sat),
            "clingo_models_unique": str(len(clingo_sets)),
            "clingo_timed_out": "False",
            "clingo_elapsed_s": f"{clingo_elapsed:.3f}",
            "klingo_rc": str(rc),
            "klingo_sat": format_bool(sat),
            "klingo_models_unique": str(len(sets)),
            "klingo_answers_raw": str(answers),
            "klingo_has_unknown": str(bool(has_unknown)),
            "klingo_timed_out": str(bool(timed_out)),
            "klingo_elapsed_s": f"{elapsed:.3f}",
            "sat_match": str(bool(sat_match)),
            "strict_in_set_match": str(bool(strict_match)),
        }

    completed = 0
    last_log = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex_pool:
        futs = [ex_pool.submit(worker, t) for t in tasks]
        for fut in as_completed(futs):
            row = fut.result()
            append_csv(detailed_csv, detailed_fields, row)
            completed += 1
            if completed % 50 == 0 or time.time() - last_log > 30:
                print(f"[PROGRESS] completed={completed}/{len(tasks)}")
                last_log = time.time()

    rows: List[Dict[str, str]] = []
    with detailed_csv.open(newline="", encoding="utf-8") as f:
        rows.extend(csv.DictReader(f))

    summary_depth = summarize(rows, ["mode", "depth"])
    summary_sem = summarize(rows, ["mode", "semantics"])

    fields = [
        "mode",
        "depth",
        "n_examples",
        "strict_match_rate",
        "sat_match_rate",
        "unknown_rate",
        "timeout_rate",
        "avg_depth",
        "avg_clingo_elapsed_s",
        "avg_klingo_elapsed_s",
    ]
    with summary_depth_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_depth)

    fields_sem = [
        "mode",
        "semantics",
        "n_examples",
        "strict_match_rate",
        "sat_match_rate",
        "unknown_rate",
        "timeout_rate",
        "avg_depth",
        "avg_clingo_elapsed_s",
        "avg_klingo_elapsed_s",
    ]
    with summary_sem_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields_sem)
        w.writeheader()
        w.writerows(summary_sem)

    strict_ok = sum(1 for r in rows if r["strict_in_set_match"] == "True")
    sat_ok = sum(1 for r in rows if r["sat_match"] == "True")
    timeouts = sum(1 for r in rows if r["klingo_timed_out"] == "True")
    unknown = sum(1 for r in rows if r["klingo_has_unknown"] == "True")
    payload = {
        "run_id": args.run_id,
        "mode": args.mode,
        "depth_csv": str(Path(args.depth_csv).resolve()),
        "depth_col": args.depth_col,
        "workers": args.workers,
        "klingo_timeout": args.klingo_timeout,
        "clingo_timeout": args.clingo_timeout,
        "n_rows": len(rows),
        "strict_match_rate": strict_ok / max(len(rows), 1),
        "sat_match_rate": sat_ok / max(len(rows), 1),
        "timeout_rate": timeouts / max(len(rows), 1),
        "unknown_rate": unknown / max(len(rows), 1),
    }
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[DONE] rows={len(rows)} strict={strict_ok}/{len(rows)} sat={sat_ok}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

