#!/usr/bin/env python3
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")))
import argparse
import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from arglas.artifact_paths import artifacts_root, resolve_repo_path


def sanitize_decimal(value) -> str:
    return str(value).replace(".", "_")


def load_config(path: str):
    with open(resolve_repo_path(path), "r", encoding="utf-8") as f:
        return json.load(f)


def semantics_list(config: dict):
    value = config["semantics"]
    if isinstance(value, str):
        return [value]
    return [str(x) for x in value]


def results_dir_for(config: dict, artifact_root: Path, semantics: str, partial: float, noise: float):
    template = config.get(
        "results_dir_template",
        "{semantics}_partial_{partial_token}_noise_{noise_token}_ratio_{ratio_token}",
    )
    dirname = template.format(
        semantics=semantics,
        partial_token=sanitize_decimal(partial),
        noise_token=sanitize_decimal(noise),
        ratio_token=str(config.get("ratio_token", "1")),
        partial=partial,
        noise=noise,
    )
    return artifact_root / "results" / dirname


def read_rows(results_dir: Path):
    rows = []
    for path in sorted(results_dir.glob("results_*.csv")):
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row:
                    rows.append(row)
    return rows


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return math.nan


def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0


def aggregate_rows(rows):
    if not rows:
        return {
            "rows": 0,
            "accuracy": math.nan,
            "f1": math.nan,
            "mcc": math.nan,
            "fp": math.nan,
            "fn": math.nan,
            "timeout_rate": math.nan,
            "train_success_rate": math.nan,
        }
    # Quality metrics are aggregated over SUCCEEDED rows only: a failed-training row
    # has no learned model (acc/F1/MCC are 0 sentinels, not a measurement), so
    # including it would bias the means downward. Failure is reported separately via
    # timeout_rate / train_success_rate over ALL rows.
    succ = [r for r in rows if safe_int(r.get("ILASP_TRAIN_SUCCEEDED")) == 1]
    quality = succ if succ else rows
    return {
        "rows": len(rows),
        "accuracy": float(np.nanmean([safe_float(r.get("ACCURACY")) for r in quality])),
        "f1": float(np.nanmean([safe_float(r.get("F1")) for r in quality])),
        "mcc": float(np.nanmean([safe_float(r.get("MCC")) for r in quality])),
        "fp": float(np.nanmean([safe_float(r.get("FP")) for r in quality])),
        "fn": float(np.nanmean([safe_float(r.get("FN")) for r in quality])),
        "timeout_rate": float(np.nanmean([safe_int(r.get("ILASP_TRAIN_TIMED_OUT")) for r in rows])),
        "train_success_rate": float(np.nanmean([safe_int(r.get("ILASP_TRAIN_SUCCEEDED")) for r in rows])),
    }


def aggregate_by_total(rows):
    buckets = defaultdict(list)
    for row in rows:
        total = safe_int(row.get("NFILES_POS")) + safe_int(row.get("NFILES_NEG"))
        buckets[total].append(row)
    points = []
    for total in sorted(buckets):
        agg = aggregate_rows(buckets[total])
        agg["total"] = total
        points.append(agg)
    return points


def write_summary_csv(path: Path, summary_rows: list[dict]):
    fieldnames = [
        "semantics",
        "partial",
        "noise",
        "rows",
        "accuracy",
        "f1",
        "mcc",
        "fp",
        "fn",
        "timeout_rate",
        "train_success_rate",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)


def heatmap(ax, matrix, x_labels, y_labels, title, vmin=None, vmax=None, cmap="viridis"):
    masked = np.ma.masked_invalid(matrix)
    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Noise")
    ax.set_ylabel("Partial")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def plot_semantics_bundle(output_dir: Path, semantics: str, partials: list[float], noises: list[float], summary_map: dict):
    x_labels = [str(n) for n in noises]
    y_labels = [str(p) for p in partials]
    metrics = [
        ("completion", "Completion", 0.0, 1.0, "Blues"),
        ("accuracy", "Accuracy", 0.0, 1.0, "viridis"),
        ("f1", "F1", 0.0, 1.0, "magma"),
        ("fp", "False Positives", None, None, "cividis"),
        ("fn", "False Negatives", None, None, "cividis"),
        ("timeout_rate", "Timeout Rate", 0.0, 1.0, "Reds"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    for ax, (key, title, vmin, vmax, cmap) in zip(axes.ravel(), metrics):
        matrix = np.full((len(partials), len(noises)), np.nan)
        for i, partial in enumerate(partials):
            for j, noise in enumerate(noises):
                matrix[i, j] = summary_map[(partial, noise)].get(key, math.nan)
        heatmap(ax, matrix, x_labels, y_labels, f"{semantics} {title}", vmin=vmin, vmax=vmax, cmap=cmap)
    fig.savefig(output_dir / f"{semantics.lower()}_heatmaps.png", dpi=180)
    plt.close(fig)


def plot_overall_lines(output_dir: Path, semantics_values: list[str], totals: list[int], series_map: dict):
    for metric, title, ylim in [
        ("accuracy", "Accuracy vs Total", (0.0, 1.0)),
        ("f1", "F1 vs Total", (0.0, 1.0)),
        ("mcc", "MCC vs Total", (-1.0, 1.0)),
        ("fp", "False Positives vs Total", None),
        ("fn", "False Negatives vs Total", None),
    ]:
        fig, axes = plt.subplots(len(semantics_values), 1, figsize=(10, 3.2 * len(semantics_values)), constrained_layout=True)
        if len(semantics_values) == 1:
            axes = [axes]
        for ax, semantics in zip(axes, semantics_values):
            for key, points in sorted(series_map[semantics].items()):
                label = f"p={key[0]}, n={key[1]}"
                xs = [p["total"] for p in points]
                ys = [p.get(metric, math.nan) for p in points]
                ax.plot(xs, ys, marker="o", label=label)
            if ylim:
                ax.set_ylim(*ylim)
            ax.set_xticks(totals)
            ax.set_title(f"{semantics} {title}")
            ax.set_xlabel("n_pos + n_neg")
            ax.set_ylabel(metric.upper())
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7, ncol=2)
        fig.savefig(output_dir / f"overall_{metric}.png", dpi=180)
        plt.close(fig)


def build_parser():
    parser = argparse.ArgumentParser(description="Plot benchmark progress from current result CSVs.")
    parser.add_argument("--config", required=True, help="JSON benchmark config.")
    parser.add_argument("--output_dir", default=None, help="Optional explicit output directory.")
    parser.add_argument("--timestamp_tag", default=None, help="Optional timestamp tag for snapshot naming.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    artifact_root = Path(artifacts_root())
    run_name = config["run_name"]
    ts = args.timestamp_tag or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output = (
        Path(args.output_dir)
        if args.output_dir
        else artifact_root / "plots" / f"{run_name}_snapshots" / ts
    )
    base_output.mkdir(parents=True, exist_ok=True)
    latest_link = artifact_root / "plots" / f"{run_name}_latest"
    latest_link.parent.mkdir(parents=True, exist_ok=True)
    latest_link.unlink(missing_ok=True)
    latest_link.symlink_to(base_output.resolve())

    sems = semantics_list(config)
    partials = [float(x) for x in config["partials"]]
    noises = [float(x) for x in config["noises"]]
    totals = sorted({2 * int(x) for x in config["f_values"]}) if config["f_values"] == config.get("f_neg_values", config["f_values"]) else sorted({int(a) + int(b) for a in config["f_values"] for b in config.get("f_neg_values", config["f_values"])})
    expected_rows = int(config.get("iterations", 1)) * int(config.get("rows_per_iteration", len(config["f_values"])))

    summary_rows = []
    series_map = defaultdict(dict)

    for semantics in sems:
        semantics_summary = {}
        for partial in partials:
            for noise in noises:
                rows = read_rows(results_dir_for(config, artifact_root, semantics, partial, noise))
                agg = aggregate_rows(rows)
                agg["completion"] = (agg["rows"] / expected_rows) if expected_rows > 0 else math.nan
                semantics_summary[(partial, noise)] = agg
                summary_rows.append(
                    {
                        "semantics": semantics,
                        "partial": partial,
                        "noise": noise,
                        "rows": agg["rows"],
                        "accuracy": agg["accuracy"],
                        "f1": agg["f1"],
                        "mcc": agg["mcc"],
                        "fp": agg["fp"],
                        "fn": agg["fn"],
                        "timeout_rate": agg["timeout_rate"],
                        "train_success_rate": agg["train_success_rate"],
                    }
                )
                series_map[semantics][(partial, noise)] = aggregate_by_total(rows)
        plot_semantics_bundle(base_output, semantics, partials, noises, semantics_summary)

    plot_overall_lines(base_output, sems, totals, series_map)
    write_summary_csv(base_output / "summary.csv", summary_rows)
    with open(base_output / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2)
    print(str(base_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
