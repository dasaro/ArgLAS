#!/usr/bin/env python3
"""
Positive-test k-fold cross-validation for real-world A..G datasets.

Per fold:
- train on k-1 folds using positive examples plus synthetic negatives generated
  from train positives;
- test on the held-out fold using positive examples only.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import clingo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from arglas.ilasp_policy import resolve_ilasp_args
from build_real_world_dataset import ParsedAAF, render_ilasp_example, run_ilasp


def timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_versions(raw: str) -> List[str]:
    out = [v.strip().upper() for v in raw.split(",") if v.strip()]
    if not out:
        raise ValueError("At least one version is required.")
    for v in out:
        if len(v) != 1 or not v.isalpha():
            raise ValueError(f"Invalid version token: {v}")
    return out


def make_folds(items: Sequence[Path], k: int, seed: int) -> List[List[Path]]:
    shuffled = list(items)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    folds: List[List[Path]] = [[] for _ in range(k)]
    for idx, path in enumerate(shuffled):
        folds[idx % k].append(path)
    return folds


def model_satisfies_example(background_file: Path, model_file: Path, example_file: Path) -> bool:
    ctl = clingo.Control(["0"])
    ctl.load(str(background_file))
    ctl.load(str(model_file))
    ctl.load(str(example_file))
    ctl.ground([("base", [])])
    return ctl.solve().satisfiable


def build_negative_from_positive_partial(
    parsed: ParsedAAF,
    rng: random.Random,
    policy: str,
    flip_k: int,
    rn_reliable_fraction: float,
) -> ParsedAAF | None:
    labels = dict(parsed.labels)
    if not labels:
        return None

    if policy == "full_relabel":
        for arg, current in list(labels.items()):
            alternatives = [s for s in ("in", "out", "undec") if s != current]
            labels[arg] = rng.choice(alternatives)
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    flippable = [arg for arg, val in labels.items() if val in {"in", "out"}]
    if not flippable:
        return None

    if policy == "flip_one":
        arg = rng.choice(flippable)
        labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    if policy == "flip_k":
        k_value = min(len(flippable), max(1, int(flip_k)))
        for arg in rng.sample(flippable, k_value):
            labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    if policy == "rn_hardmix":
        max_k = min(len(flippable), max(2, int(flip_k)))
        k_value = max_k if (max_k > 1 and rng.random() < rn_reliable_fraction) else 1
        for arg in rng.sample(flippable, k_value):
            labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    raise ValueError(f"Unsupported negative policy: {policy}")


def parse_lp_instance_lenient(path: Path) -> ParsedAAF:
    args: set[str] = set()
    attacks: set[Tuple[str, str]] = set()
    labels: Dict[str, str] = {}

    text = path.read_text(encoding="utf-8")

    # Accept compact formatting where multiple atoms can appear on one line.
    for arg in re.findall(r"\barg\(\s*([a-z][a-zA-Z0-9_]*)\s*\)\.", text):
        args.add(arg)

    for src, tgt in re.findall(
        r"\batt\(\s*([a-z][a-zA-Z0-9_]*)\s*,\s*([a-z][a-zA-Z0-9_]*)\s*\)\.",
        text,
    ):
        attacks.add((src, tgt))

    for status, arg in re.findall(
        r"\b(in|out|undec)\(\s*([a-z][a-zA-Z0-9_]*)\s*\)\.",
        text,
    ):
        labels[arg] = status

    if not args:
        raise ValueError(f"No arg/1 facts found in {path}")
    if not labels:
        raise ValueError(f"No labels found in {path}")

    return ParsedAAF(args=sorted(args), attacks=sorted(attacks), labels=labels)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    parser = argparse.ArgumentParser(
        description=(
            "K-fold CV on real-world examples: train with pos+synthetic-neg from train folds, "
            "test on held-out positives only."
        )
    )
    parser.add_argument("--pos-root", type=Path, default=script_dir.parent / "asp_files")
    parser.add_argument("--versions", type=str, default="A,B,C,D,E,F,G")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--weight", type=int, default=100)
    parser.add_argument("--negative-ratio", type=float, default=1.0, help="Target n_neg_train / n_pos_train.")
    parser.add_argument(
        "--negative-policy",
        type=str,
        choices=("full_relabel", "flip_one", "flip_k", "rn_hardmix"),
        default="full_relabel",
    )
    parser.add_argument("--negative-flip-k", type=int, default=2, help="Max flips for rn_hardmix.")
    parser.add_argument(
        "--rn-reliable-fraction",
        type=float,
        default=0.7,
        help="Reliable-negative fraction for rn_hardmix.",
    )
    parser.add_argument("--train-timeout-seconds", type=int, default=1200)
    parser.add_argument(
        "--semantics",
        type=str,
        default=None,
        help="Optional semantics key used to resolve central ILASP policy (e.g. PRF).",
    )
    parser.add_argument("--ilasp-extra-args", type=str, default="")
    parser.add_argument("--ilasp-config", type=Path, default=REPO_ROOT / "config/ilasp_config.json")
    parser.add_argument("--semantics-config", type=Path, default=REPO_ROOT / "config/semantics_config.json")
    parser.add_argument("--background-file", type=Path, default=REPO_ROOT / "config/background_knowledge.lp")
    parser.add_argument("--mode-file", type=Path, default=REPO_ROOT / "config/mode_declarations.las")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir.parent / "runs" / f"cv_pos_only_{timestamp_tag()}",
    )
    args = parser.parse_args()

    if args.folds < 2:
        raise ValueError("--folds must be >= 2.")
    if args.weight <= 0:
        raise ValueError("--weight must be > 0.")
    if args.negative_ratio < 0:
        raise ValueError("--negative-ratio must be >= 0.")
    if args.negative_flip_k <= 0:
        raise ValueError("--negative-flip-k must be > 0.")
    if not (0.0 <= args.rn_reliable_fraction <= 1.0):
        raise ValueError("--rn-reliable-fraction must be in [0,1].")
    if args.train_timeout_seconds <= 0:
        raise ValueError("--train-timeout-seconds must be > 0.")
    if not args.background_file.exists():
        raise FileNotFoundError(f"Missing background file: {args.background_file}")
    if not args.mode_file.exists():
        raise FileNotFoundError(f"Missing mode file: {args.mode_file}")

    versions = parse_versions(args.versions)
    ilasp_extra_args = resolve_ilasp_args(
        semantics=args.semantics,
        ilasp_config_path=str(args.ilasp_config),
        semantics_config_path=str(args.semantics_config),
        extra_args=[a.strip() for a in args.ilasp_extra_args.split(",") if a.strip()],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = args.output_dir / "tasks"
    models_dir = args.output_dir / "models"
    logs_dir = args.output_dir / "logs"
    for d in (tasks_dir, models_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    run_config = {
        "timestamp": timestamp_tag(),
        "pos_root": str(args.pos_root),
        "versions": versions,
        "folds_requested": args.folds,
        "seed": args.seed,
        "weight": args.weight,
        "negative_ratio": args.negative_ratio,
        "negative_policy": args.negative_policy,
        "negative_flip_k": args.negative_flip_k,
        "rn_reliable_fraction": args.rn_reliable_fraction,
        "train_timeout_seconds": args.train_timeout_seconds,
        "semantics": args.semantics,
        "ilasp_extra_args": ilasp_extra_args,
        "ilasp_config": str(args.ilasp_config),
        "semantics_config": str(args.semantics_config),
        "background_file": str(args.background_file),
        "mode_file": str(args.mode_file),
    }
    (args.output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    background_text = args.background_file.read_text(encoding="utf-8").strip()
    mode_text = args.mode_file.read_text(encoding="utf-8").strip()

    fold_rows: List[Dict[str, object]] = []

    for v in versions:
        pos_dir = args.pos_root / f"version{v}" / "pos"
        if not pos_dir.exists():
            continue
        pos_files = sorted(pos_dir.glob("*.lp"))
        n_pos = len(pos_files)
        if n_pos < 2:
            continue

        k = min(args.folds, n_pos)
        folds = make_folds(pos_files, k=k, seed=args.seed + ord(v))
        rng = random.Random(args.seed + 1000 + ord(v))

        for fold_idx in range(k):
            test_files = list(folds[fold_idx])
            train_files = [p for j, fold in enumerate(folds) if j != fold_idx for p in fold]
            if not test_files or not train_files:
                continue

            directives: List[str] = []
            train_parsed: List[Tuple[str, ParsedAAF]] = []
            for p in train_files:
                parsed = parse_lp_instance_lenient(p)
                train_parsed.append((p.stem, parsed))
                directives.append(
                    render_ilasp_example(
                        example_type="pos",
                        example_id=f"{p.stem}_pos",
                        weight=args.weight,
                        parsed=parsed,
                    )
                )

            target_neg = int(round(len(train_parsed) * args.negative_ratio))
            if args.negative_ratio > 0 and target_neg == 0:
                target_neg = 1

            neg_candidates: List[Tuple[str, ParsedAAF]] = []
            for stem, parsed in train_parsed:
                neg = build_negative_from_positive_partial(
                    parsed=parsed,
                    rng=rng,
                    policy=args.negative_policy,
                    flip_k=args.negative_flip_k,
                    rn_reliable_fraction=args.rn_reliable_fraction,
                )
                if neg is not None:
                    neg_candidates.append((stem, neg))

            realized_neg = 0
            if target_neg > 0 and neg_candidates:
                if target_neg <= len(neg_candidates):
                    selected = rng.sample(neg_candidates, target_neg)
                else:
                    shuffled = neg_candidates[:]
                    rng.shuffle(shuffled)
                    selected = [shuffled[i % len(shuffled)] for i in range(target_neg)]

                for idx, (stem, parsed_neg) in enumerate(selected, start=1):
                    directives.append(
                        render_ilasp_example(
                            example_type="neg",
                            example_id=f"{stem}_neg{idx}",
                            weight=args.weight,
                            parsed=parsed_neg,
                        )
                    )
                    realized_neg += 1

            task_text = "\n".join(directives) + "\n\n" + background_text + "\n\n" + mode_text + "\n"
            task_file = tasks_dir / f"version{v}_fold{fold_idx + 1}.las"
            model_file = models_dir / f"version{v}_fold{fold_idx + 1}.lp"
            log_file = logs_dir / f"version{v}_fold{fold_idx + 1}.log"
            task_file.write_text(task_text, encoding="utf-8")

            train_result = run_ilasp(
                task_file=task_file,
                model_file=model_file,
                log_file=log_file,
                timeout_seconds=args.train_timeout_seconds,
                extra_args=ilasp_extra_args,
            )

            tp = 0
            fn = 0
            if train_result["succeeded"]:
                for ex in test_files:
                    try:
                        sat = model_satisfies_example(args.background_file, model_file, ex)
                    except Exception:
                        sat = False
                    if sat:
                        tp += 1
                    else:
                        fn += 1
            else:
                fn = len(test_files)

            recall = (tp / (tp + fn)) if (tp + fn) else 0.0
            fold_rows.append(
                {
                    "version": v,
                    "fold": fold_idx + 1,
                    "k_folds_used": k,
                    "n_pos_total": n_pos,
                    "n_train_pos": len(train_files),
                    "n_train_neg": realized_neg,
                    "neg_ratio_target": f"{args.negative_ratio:.6f}",
                    "neg_policy": args.negative_policy,
                    "n_test_pos": len(test_files),
                    "tp_pos": tp,
                    "fn_pos": fn,
                    "recall_pos": f"{recall:.6f}",
                    "train_succeeded": int(bool(train_result["succeeded"])),
                    "train_timed_out": int(bool(train_result["timed_out"])),
                    "train_return_code": "" if train_result["return_code"] is None else train_result["return_code"],
                    "train_elapsed_seconds": f"{float(train_result['elapsed_seconds']):.6f}",
                    "task_file": str(task_file),
                    "model_file": str(model_file),
                    "log_file": str(log_file),
                }
            )

    fold_csv = args.output_dir / "cv_fold_results.csv"
    if fold_rows:
        with fold_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(fold_rows[0].keys()))
            writer.writeheader()
            writer.writerows(fold_rows)
    else:
        fold_csv.write_text("", encoding="utf-8")

    by_version: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in fold_rows:
        by_version[str(row["version"])].append(row)

    summary_rows: List[Dict[str, object]] = []
    for v in sorted(by_version):
        rows = by_version[v]
        recalls = [float(r["recall_pos"]) for r in rows]
        elapsed = [float(r["train_elapsed_seconds"]) for r in rows]
        succeeded = [int(r["train_succeeded"]) for r in rows]
        timed_out = [int(r["train_timed_out"]) for r in rows]
        total_tp = sum(int(r["tp_pos"]) for r in rows)
        total_fn = sum(int(r["fn_pos"]) for r in rows)
        micro_recall = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) else 0.0

        summary_rows.append(
            {
                "version": v,
                "n_folds": len(rows),
                "avg_n_train_neg": f"{statistics.mean(int(r['n_train_neg']) for r in rows):.6f}",
                "avg_recall_pos": f"{statistics.mean(recalls):.6f}",
                "std_recall_pos": f"{statistics.pstdev(recalls):.6f}" if len(recalls) > 1 else "0.000000",
                "micro_recall_pos": f"{micro_recall:.6f}",
                "train_success_rate": f"{(sum(succeeded) / len(succeeded)):.6f}",
                "train_timeout_rate": f"{(sum(timed_out) / len(timed_out)):.6f}",
                "avg_train_elapsed_seconds": f"{statistics.mean(elapsed):.6f}",
            }
        )

    overall_row: Dict[str, object] | None = None
    if fold_rows:
        recalls_all = [float(r["recall_pos"]) for r in fold_rows]
        elapsed_all = [float(r["train_elapsed_seconds"]) for r in fold_rows]
        succeeded_all = [int(r["train_succeeded"]) for r in fold_rows]
        timed_out_all = [int(r["train_timed_out"]) for r in fold_rows]
        total_tp_all = sum(int(r["tp_pos"]) for r in fold_rows)
        total_fn_all = sum(int(r["fn_pos"]) for r in fold_rows)
        micro_all = (total_tp_all / (total_tp_all + total_fn_all)) if (total_tp_all + total_fn_all) else 0.0
        overall_row = {
            "version": "ALL",
            "n_folds": len(fold_rows),
            "avg_n_train_neg": f"{statistics.mean(int(r['n_train_neg']) for r in fold_rows):.6f}",
            "avg_recall_pos": f"{statistics.mean(recalls_all):.6f}",
            "std_recall_pos": f"{statistics.pstdev(recalls_all):.6f}" if len(recalls_all) > 1 else "0.000000",
            "micro_recall_pos": f"{micro_all:.6f}",
            "train_success_rate": f"{(sum(succeeded_all) / len(succeeded_all)):.6f}",
            "train_timeout_rate": f"{(sum(timed_out_all) / len(timed_out_all)):.6f}",
            "avg_train_elapsed_seconds": f"{statistics.mean(elapsed_all):.6f}",
        }
        summary_rows.append(overall_row)

    summary_csv = args.output_dir / "cv_summary_by_version.csv"
    if summary_rows:
        with summary_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
    else:
        summary_csv.write_text("", encoding="utf-8")

    print("✅ CV (train with synthetic negatives, test on positives) completed.")
    print(f"Output dir: {args.output_dir}")
    print(f"Fold results: {fold_csv}")
    print(f"Summary: {summary_csv}")
    if overall_row is not None:
        print(
            "Overall micro recall="
            f"{overall_row['micro_recall_pos']} | "
            f"train success rate={overall_row['train_success_rate']} | "
            f"timeout rate={overall_row['train_timeout_rate']}"
        )


if __name__ == "__main__":
    main()
