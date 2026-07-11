#!/usr/bin/env python3
"""Compare ASPARTIX+klingo to ILASP-learned theories at per-file custom depths.

Depth per (semantics, example) comes from a clingo --stats CSV.
For each pair, evaluate a small set of offsets around that depth.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
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
                    or s.startswith("Consequences")
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


def run_cmd_capture(cmd: Sequence[str], timeout_s: float) -> Tuple[int, str, bool, float]:
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
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        rc = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(
            "utf-8", errors="replace"
        )
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(
            "utf-8", errors="replace"
        )
        text = out + "\n" + err
        rc = -9
        timed_out = True
    return rc, text, timed_out, time.time() - start


def run_clingo_models(
    clingo_bin: str, files: Sequence[str], timeout_s: float
) -> Tuple[Optional[bool], Set[FrozenSet[str]], int, bool, float]:
    rc, text, timed_out, elapsed = run_cmd_capture([clingo_bin, "-n", "0", *files], timeout_s)
    sets, answers = parse_models(text)
    if "UNSATISFIABLE" in text:
        sat: Optional[bool] = False
    elif answers > 0 or "SATISFIABLE" in text:
        sat = True
    else:
        sat = None
    _ = rc
    return sat, sets, answers, timed_out, elapsed


def run_klingo_models(
    venv_python: str,
    klingo_script: str,
    mode: str,
    depth: int,
    files: Sequence[str],
    timeout_s: float,
) -> Tuple[Optional[bool], Set[FrozenSet[str]], int, bool, bool, float, int]:
    mode_flag = f"--{mode}"
    cmd = [venv_python, klingo_script, mode_flag, "-k", str(depth), "--mode", "all", "-n", "0", *files]
    rc, text, timed_out, elapsed = run_cmd_capture(cmd, timeout_s)
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
            k = (sem, ex)
            if k not in out:
                out[k] = d
            else:
                out[k] = max(out[k], d)
    return out


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
                "depth_sum": 0.0,
                "klingo_elapsed_s_sum": 0.0,
            },
        )
        a["n"] += 1.0
        a["strict_match"] += 1.0 if r["strict_in_set_match"] == "True" else 0.0
        a["sat_match"] += 1.0 if r["sat_match"] == "True" else 0.0
        a["unknown"] += 1.0 if r["klingo_has_unknown"] == "True" else 0.0
        a["timeout"] += 1.0 if r["klingo_timed_out"] == "True" else 0.0
        try:
            a["depth_sum"] += float(r["depth"])
        except Exception:
            pass
        try:
            a["klingo_elapsed_s_sum"] += float(r["klingo_elapsed_s"])
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
                "avg_klingo_elapsed_s": f"{a['klingo_elapsed_s_sum'] / n:.3f}",
            }
        )
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=f"klingo_learned_custom_depths_{now_ts()}")
    ap.add_argument("--mode", choices=("3nd-star", "3nd", "bnm"), default="3nd-star")
    ap.add_argument("--depth-csv", required=True)
    ap.add_argument("--depth-col", default="choices")
    ap.add_argument("--offsets", nargs="+", type=int, default=[-1, 0, 1])
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--clingo-timeout", type=float, default=60.0)
    ap.add_argument("--base", default=".", help="Repository root")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    run_dir = base / "Real_World_Examples" / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    learned_csv = run_dir / "learned_rows.csv"
    detailed_csv = run_dir / "detailed_rows.csv"
    summary_offset_csv = run_dir / "summary_offset.csv"
    summary_sem_offset_csv = run_dir / "summary_sem_offset.csv"
    summary_json = run_dir / "summary.json"

    depth_map = load_depth_map(Path(args.depth_csv).resolve(), args.depth_col)

    clingo_bin = os.environ.get("CLINGO_BIN") or "clingo"
    venv_python = str((base / ".venv" / "bin" / "python").resolve())
    klingo_script = str(Path("/Users/fdasaro/Desktop/klingo-codex/klingo"))

    examples = collect_examples(base)
    if not examples:
        print("No A..G examples found.", file=sys.stderr)
        return 2

    learned_fields = [
        "version",
        "bucket",
        "example_path",
        "learned_sat",
        "learned_models_unique",
        "learned_answers_raw",
        "learned_timed_out",
        "learned_elapsed_s",
        "learned_in_sets_json",
    ]
    done_learned = read_completed_keys(learned_csv, ["version", "bucket", "example_path"])
    learned_cache: Dict[Tuple[str, str, str], Tuple[Optional[bool], Set[FrozenSet[str]]]] = {}
    if learned_csv.exists():
        with learned_csv.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (row["version"], row["bucket"], row["example_path"])
                try:
                    sets = {
                        frozenset(s)
                        for s in json.loads(row["learned_in_sets_json"])
                        if isinstance(s, list)
                    }
                except Exception:
                    sets = set()
                learned_cache[key] = (parse_bool(row.get("learned_sat", "")), sets)

    for ex in examples:
        key = (ex.version, ex.bucket, ex.path)
        if key in done_learned:
            continue
        learned_lp = base / "Real_World_Examples" / "learned_encodings" / f"version{ex.version}.lp"
        sat, sets, answers, timed_out, elapsed = run_clingo_models(
            clingo_bin=clingo_bin,
            files=[str(learned_lp), ex.path],
            timeout_s=args.clingo_timeout,
        )
        row = {
            "version": ex.version,
            "bucket": ex.bucket,
            "example_path": ex.path,
            "learned_sat": format_bool(sat),
            "learned_models_unique": str(len(sets)),
            "learned_answers_raw": str(answers),
            "learned_timed_out": str(bool(timed_out)),
            "learned_elapsed_s": f"{elapsed:.3f}",
            "learned_in_sets_json": json.dumps([sorted(s) for s in sorted(sets, key=lambda x: (len(x), tuple(sorted(x))))]),
        }
        append_csv(learned_csv, learned_fields, row)
        learned_cache[key] = (sat, sets)

    detailed_fields = [
        "version",
        "bucket",
        "example_path",
        "semantics",
        "mode",
        "offset",
        "base_depth",
        "depth",
        "learned_sat",
        "learned_models_unique",
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
    done = read_completed_keys(
        detailed_csv,
        ["version", "bucket", "example_path", "semantics", "mode", "offset", "depth"],
    )

    tasks: List[Tuple[Example, str, int, int, int]] = []
    for ex in examples:
        for sem in SEM_FILE:
            base_depth = depth_map.get((sem, ex.path), 0)
            eval_depths: Set[Tuple[int, int]] = set()
            for off in args.offsets:
                d = base_depth + off
                if d < 0:
                    d = 0
                eval_depths.add((off, d))
            for off, d in sorted(eval_depths):
                key = (ex.version, ex.bucket, ex.path, sem, args.mode, str(off), str(d))
                if key not in done:
                    tasks.append((ex, sem, base_depth, off, d))

    print(f"[INFO] run_dir={run_dir}")
    print(f"[INFO] depth_csv={Path(args.depth_csv).resolve()} depth_col={args.depth_col}")
    print(f"[INFO] offsets={args.offsets}")
    print(f"[INFO] examples={len(examples)} pending_tasks={len(tasks)}")

    def worker(task: Tuple[Example, str, int, int, int]) -> Dict[str, str]:
        ex, sem, base_depth, off, depth = task
        sem_lp = base / "config" / "ASPARTIX" / SEM_FILE[sem]
        key = (ex.version, ex.bucket, ex.path)
        learned_sat, learned_sets = learned_cache[key]
        sat, sets, answers, has_unknown, timed_out, elapsed, rc = run_klingo_models(
            venv_python=venv_python,
            klingo_script=klingo_script,
            mode=args.mode,
            depth=depth,
            files=[str(sem_lp), ex.path],
            timeout_s=args.timeout,
        )
        sat_match = (sat is not None) and (learned_sat is not None) and (sat == learned_sat)
        strict_match = sat_match and (not timed_out) and (sets == learned_sets)
        return {
            "version": ex.version,
            "bucket": ex.bucket,
            "example_path": ex.path,
            "semantics": sem,
            "mode": args.mode,
            "offset": str(off),
            "base_depth": str(base_depth),
            "depth": str(depth),
            "learned_sat": format_bool(learned_sat),
            "learned_models_unique": str(len(learned_sets)),
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
            if completed % 200 == 0 or time.time() - last_log > 30:
                print(f"[PROGRESS] completed={completed}/{len(tasks)}")
                last_log = time.time()

    rows: List[Dict[str, str]] = []
    with detailed_csv.open(newline="", encoding="utf-8") as f:
        rows.extend(csv.DictReader(f))

    summary_offset = summarize(rows, ["mode", "offset"])
    summary_sem_offset = summarize(rows, ["mode", "semantics", "offset"])

    with summary_offset_csv.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "mode",
            "offset",
            "n_examples",
            "strict_match_rate",
            "sat_match_rate",
            "unknown_rate",
            "timeout_rate",
            "avg_depth",
            "avg_klingo_elapsed_s",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_offset)

    with summary_sem_offset_csv.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "mode",
            "semantics",
            "offset",
            "n_examples",
            "strict_match_rate",
            "sat_match_rate",
            "unknown_rate",
            "timeout_rate",
            "avg_depth",
            "avg_klingo_elapsed_s",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_sem_offset)

    strict_ok = sum(1 for r in rows if r["strict_in_set_match"] == "True")
    sat_ok = sum(1 for r in rows if r["sat_match"] == "True")
    payload = {
        "run_id": args.run_id,
        "mode": args.mode,
        "depth_csv": str(Path(args.depth_csv).resolve()),
        "depth_col": args.depth_col,
        "offsets": args.offsets,
        "n_rows": len(rows),
        "strict_match_rate": strict_ok / max(len(rows), 1),
        "sat_match_rate": sat_ok / max(len(rows), 1),
    }
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[DONE] rows={len(rows)} strict={strict_ok}/{len(rows)} sat={sat_ok}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

