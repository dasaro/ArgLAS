#!/usr/bin/env python3
"""
End-to-end builder for the real-world learning pipeline.

Pipeline stages:
1) Extract participant-specific AAF/label `.lp` files from raw workbook.
2) Preserve/validate paper graph structure metadata for versions A..G.
3) Build positive/negative datasets (configurable negative ratio/policy).
4) Build ILASP tasks with weighted examples (confidence-aware or constant).
5) Run ILASP training per version and store learned theories/logs.

Defaults follow the current paper-oriented approximation:
- one negative per positive (ratio = 1.0)
- example weight fixed to 100 (confidence recorded but not used for weight)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ilasp_policy import resolve_ilasp_args

# Reuse authoritative extraction/parsing utilities implemented for raw workbook.
from extract_labeled_aafs import build_pid, parse_relation_atom, read_xlsx_sheet


STATUSES = ("in", "out", "undec")

PAPER_GRAPH_STRUCTURE = {
    "A": {"family": "floating_reinstatement", "expected_n_args": 4, "expected_relation_prompts": 12},
    "B": {"family": "floating_reinstatement", "expected_n_args": 4, "expected_relation_prompts": 12},
    "C": {"family": "floating_reinstatement", "expected_n_args": 4, "expected_relation_prompts": 12},
    "D": {"family": "simple_reinstatement", "expected_n_args": 3, "expected_relation_prompts": 6},
    "E": {"family": "simple_reinstatement", "expected_n_args": 3, "expected_relation_prompts": 6},
    "F": {"family": "simple_reinstatement", "expected_n_args": 3, "expected_relation_prompts": 6},
    "G": {"family": "three_cycle", "expected_n_args": 5, "expected_relation_prompts": 20},
}

PAPER_REFERENCE = {
    "citation": "PLOS ONE (2022), doi:10.1371/journal.pone.0273225",
    "paper_pdf": "Real_World_Examples/Paper/pone.0273225.pdf",
    "method_note": "Part A and Part B protocols include first/group/final response phases.",
}


@dataclass
class ParsedAAF:
    args: List[str]
    attacks: List[Tuple[str, str]]
    labels: Dict[str, str]


def parse_versions(raw: str) -> List[str]:
    versions = [v.strip().upper() for v in raw.split(",") if v.strip()]
    if not versions:
        raise ValueError("At least one version is required.")
    for v in versions:
        if v not in PAPER_GRAPH_STRUCTURE:
            raise ValueError(f"Unsupported version: {v}. Expected subset of {sorted(PAPER_GRAPH_STRUCTURE)}")
    return versions


def timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def is_probable_asp_rule(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("%") or stripped.startswith("["):
        return False
    if not stripped.endswith("."):
        return False
    return (
        stripped.startswith(":-")
        or stripped.startswith(":~")
        or stripped.startswith("#")
        or stripped.startswith("{")
        or stripped[0].isalpha()
    )


def extract_hypothesis_rules(ilasp_output: str) -> List[str]:
    lines = ilasp_output.splitlines()

    rules_after_final: List[str] = []
    in_final_hypothesis = False
    for line in lines:
        stripped = line.strip()
        if "Final Hypothesis" in stripped:
            in_final_hypothesis = True
            continue
        if not in_final_hypothesis:
            continue
        if is_probable_asp_rule(stripped):
            rules_after_final.append(stripped)

    if rules_after_final:
        return rules_after_final

    return [line.strip() for line in lines if is_probable_asp_rule(line)]


def parse_lp_instance(path: Path) -> ParsedAAF:
    arg_re = re.compile(r"^arg\(([a-z][a-zA-Z0-9_]*)\)\.$")
    att_re = re.compile(r"^att\(([a-z][a-zA-Z0-9_]*),([a-z][a-zA-Z0-9_]*)\)\.$")
    lab_re = re.compile(r"^(in|out|undec)\(([a-z][a-zA-Z0-9_]*)\)\.$")

    args = set()
    attacks = set()
    labels: Dict[str, str] = {}

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        m_arg = arg_re.match(line)
        if m_arg:
            args.add(m_arg.group(1))
            continue
        m_att = att_re.match(line)
        if m_att:
            attacks.add((m_att.group(1), m_att.group(2)))
            continue
        m_lab = lab_re.match(line)
        if m_lab:
            labels[m_lab.group(2)] = m_lab.group(1)
            continue

    if not args:
        raise ValueError(f"No arg/1 facts found in {path}")
    if set(labels.keys()) != args:
        missing = sorted(args - set(labels.keys()))
        extra = sorted(set(labels.keys()) - args)
        raise ValueError(f"Label/arg mismatch in {path}: missing={missing}, extra={extra}")

    return ParsedAAF(args=sorted(args), attacks=sorted(attacks), labels=labels)


def write_lp_instance(path: Path, parsed: ParsedAAF) -> None:
    lines: List[str] = []
    for arg in parsed.args:
        lines.append(f"arg({arg}).")
    for src, tgt in parsed.attacks:
        lines.append(f"att({src},{tgt}).")
    for status in STATUSES:
        for arg in sorted(a for a, s in parsed.labels.items() if s == status):
            lines.append(f"{status}({arg}).")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def confidence_column_for_label_phase(label_phase: str, label_column: str) -> Optional[str]:
    phase = (label_phase or "").strip().lower()
    if phase == "first":
        return "1ST_CONFIDENCE"
    if phase == "final":
        return "2ND_CONFIDENCE"
    if phase == "group":
        return None

    col = (label_column or "").strip().upper()
    if col.startswith("1ST_"):
        return "1ST_CONFIDENCE"
    if col.startswith("2ND_"):
        return "2ND_CONFIDENCE"
    return None


def compute_weight(
    confidence_value: Optional[float],
    weight_mode: str,
    base_weight: int,
    confidence_max: float,
) -> int:
    if weight_mode == "constant":
        return int(base_weight)

    if confidence_value is None:
        return int(base_weight)

    if weight_mode == "confidence_linear":
        scaled = (float(confidence_value) / float(confidence_max)) * float(base_weight)
        return max(1, int(round(scaled)))

    raise ValueError(f"Unsupported weight mode: {weight_mode}")


def build_confidence_map(
    data_path: Path,
    versions: Sequence[str],
    label_phase: str,
    label_column: str,
) -> Tuple[Dict[str, Optional[float]], Optional[str]]:
    part_b_rows = read_xlsx_sheet(data_path, "PART_B")
    confidence_col = confidence_column_for_label_phase(label_phase, label_column)

    if confidence_col is None:
        return {}, None

    by_pid_values: Dict[str, List[float]] = defaultdict(list)
    for row in part_b_rows:
        version = str(row.get("VERSION", "")).strip().upper()
        participant = str(row.get("PARTICIPANT", "")).strip()
        if version not in versions or not participant:
            continue
        pid = build_pid(participant, version)
        raw = str(row.get(confidence_col, "")).strip()
        if not raw:
            continue
        try:
            by_pid_values[pid].append(float(raw))
        except ValueError:
            continue

    confidence_map: Dict[str, Optional[float]] = {}
    for pid, vals in by_pid_values.items():
        confidence_map[pid] = (sum(vals) / len(vals)) if vals else None
    return confidence_map, confidence_col


def build_structure_report(data_path: Path, versions: Sequence[str]) -> Dict[str, dict]:
    part_a_rows = read_xlsx_sheet(data_path, "PART_A")
    part_b_rows = read_xlsx_sheet(data_path, "PART_B")

    args_per_pid: Dict[str, set] = defaultdict(set)
    rels_per_pid: Dict[str, set] = defaultdict(set)

    for row in part_b_rows:
        version = str(row.get("VERSION", "")).strip().upper()
        participant = str(row.get("PARTICIPANT", "")).strip()
        item = str(row.get("ITEM", "")).strip().lower()
        if version not in versions or not participant or not item:
            continue
        pid = build_pid(participant, version)
        args_per_pid[pid].add(item)

    for row in part_a_rows:
        version = str(row.get("VERSION", "")).strip().upper()
        participant = str(row.get("PARTICIPANT", "")).strip()
        relation = parse_relation_atom(str(row.get("RELATION", "")))
        if version not in versions or not participant or relation is None:
            continue
        pid = build_pid(participant, version)
        rels_per_pid[pid].add(relation)

    report: Dict[str, dict] = {}
    for version in versions:
        expected = PAPER_GRAPH_STRUCTURE[version]
        pids = sorted(
            pid for pid in set(args_per_pid) | set(rels_per_pid) if pid.endswith(f"_version{version}")
        )
        observed_n_args = sorted({len(args_per_pid.get(pid, set())) for pid in pids})
        observed_n_relation_prompts = sorted({len(rels_per_pid.get(pid, set())) for pid in pids})
        report[version] = {
            "family": expected["family"],
            "expected_n_args": expected["expected_n_args"],
            "expected_relation_prompts": expected["expected_relation_prompts"],
            "participants": len(pids),
            "observed_n_args_values": observed_n_args,
            "observed_relation_prompt_values": observed_n_relation_prompts,
            "matches_expected_n_args": observed_n_args == [expected["expected_n_args"]],
            "matches_expected_relation_prompts": observed_n_relation_prompts == [expected["expected_relation_prompts"]],
        }
    return report


def run_extractor(
    script_path: Path,
    data_path: Path,
    output_dir: Path,
    versions: Sequence[str],
    attack_source: str,
    label_source: str,
    na_attack_policy: str,
) -> None:
    command = [
        sys.executable,
        str(script_path),
        "--data-path",
        str(data_path),
        "--output-dir",
        str(output_dir),
        "--versions",
        ",".join(versions),
        "--attack-sources",
        attack_source,
        "--label-sources",
        label_source,
        "--na-attack-policy",
        na_attack_policy,
        "--allow-overwrite",
    ]
    subprocess.run(command, check=True)


def select_single_combo(rows: List[dict]) -> Tuple[str, str, str, str]:
    combos = sorted(
        {
            (
                row["attack_source_key"],
                row["attack_phase"],
                row["label_source_key"],
                row["label_phase"],
            )
            for row in rows
        }
    )
    if len(combos) != 1:
        raise ValueError(
            "Expected exactly one extracted source combo. "
            f"Found {len(combos)} combos: {combos}. "
            "Pass one attack source and one label source."
        )
    return combos[0]


def render_ilasp_example(
    example_type: str,
    example_id: str,
    weight: int,
    parsed: ParsedAAF,
) -> str:
    include_atoms: List[str] = []
    exclude_atoms: List[str] = []

    # Encode labels as ILASP partial interpretations over in/out only:
    # - in(a):   include in(a), exclude out(a)
    # - out(a):  include out(a), exclude in(a)
    # - undec(a): exclude both in(a) and out(a)
    for arg in sorted(parsed.args):
        status = parsed.labels.get(arg)
        if status == "in":
            include_atoms.append(f"in({arg})")
            exclude_atoms.append(f"out({arg})")
        elif status == "out":
            include_atoms.append(f"out({arg})")
            exclude_atoms.append(f"in({arg})")
        elif status == "undec":
            exclude_atoms.append(f"in({arg})")
            exclude_atoms.append(f"out({arg})")
        else:
            raise ValueError(f"Unsupported label status '{status}' for arg '{arg}'")

    context = [f"arg({a})." for a in parsed.args] + [f"att({s},{t})." for s, t in parsed.attacks]
    include_str = ", ".join(include_atoms)
    exclude_str = ", ".join(exclude_atoms)
    context_str = " ".join(context)
    return f"#{example_type}({example_id}@{int(weight)}, {{{include_str}}}, {{{exclude_str}}}, {{{context_str}}})."


def build_negative_from_positive(
    parsed: ParsedAAF,
    rng: random.Random,
    policy: str,
    flip_k: int = 2,
    rn_reliable_fraction: float = 0.7,
) -> Optional[ParsedAAF]:
    labels = dict(parsed.labels)

    if policy == "flip_one":
        # Flip exactly one argument between in/out. Keep undec unchanged.
        flippable = [arg for arg in parsed.args if labels.get(arg) in {"in", "out"}]
        if not flippable:
            return None
        arg = rng.choice(flippable)
        labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    if policy == "flip_k":
        # Flip exactly k arguments between in/out. Keep undec unchanged.
        flippable = [arg for arg in parsed.args if labels.get(arg) in {"in", "out"}]
        k_value = int(flip_k)
        if k_value <= 0 or len(flippable) < k_value:
            return None
        for arg in rng.sample(flippable, k_value):
            labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    if policy == "full_relabel":
        for arg in parsed.args:
            current = labels[arg]
            alternatives = [s for s in STATUSES if s != current]
            labels[arg] = rng.choice(alternatives)
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    if policy == "rn_hardmix":
        # Reliable-negative + hard-negative mix without external validation:
        # with probability rn_reliable_fraction, apply a stronger multi-flip mutation
        # (reliable synthetic negative); otherwise apply a single flip (hard negative).
        flippable = [arg for arg in parsed.args if labels.get(arg) in {"in", "out"}]
        if not flippable:
            return None
        max_k = min(len(flippable), max(2, int(flip_k)))
        if max_k <= 1:
            k_value = 1
        else:
            k_value = max_k if rng.random() < rn_reliable_fraction else 1
        for arg in rng.sample(flippable, k_value):
            labels[arg] = "out" if labels[arg] == "in" else "in"
        return ParsedAAF(args=list(parsed.args), attacks=list(parsed.attacks), labels=labels)

    raise ValueError(f"Unsupported negative policy: {policy}")


def run_ilasp(task_file: Path, model_file: Path, log_file: Path, timeout_seconds: int, extra_args: Sequence[str]) -> dict:
    command = ["ILASP", "--version=4"] + list(extra_args) + ["-d", str(task_file)]

    start = time.perf_counter()
    timed_out = False
    output_text = ""
    return_code: Optional[int] = None

    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return_code = proc.returncode
        output_text = proc.stdout or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        return_code = None
        output_text = (e.stdout or "") + "\n[Timeout] ILASP timed out.\n"

    elapsed_seconds = time.perf_counter() - start
    if timed_out:
        elapsed_seconds = min(elapsed_seconds, float(timeout_seconds))

    log_file.write_text(output_text, encoding="utf-8")

    succeeded = (not timed_out) and (return_code == 0)
    if succeeded:
        rules = extract_hypothesis_rules(output_text)
        if rules:
            model_file.write_text("\n".join(rules) + "\n", encoding="utf-8")
        else:
            model_file.write_text("% ILASP completed with empty hypothesis.\n", encoding="utf-8")
    else:
        model_file.write_text(
            "% ILASP training failed.\n"
            f"% timed_out={int(timed_out)} return_code={return_code}\n",
            encoding="utf-8",
        )

    return {
        "timed_out": timed_out,
        "return_code": return_code,
        "succeeded": succeeded,
        "elapsed_seconds": elapsed_seconds,
        "command": command,
    }


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    parser = argparse.ArgumentParser(description="Build and train real-world ILASP datasets end-to-end.")
    parser.add_argument("--data-path", type=Path, default=script_dir / "Raw_Data_original.xlsx")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / f"runs/real_world_{timestamp_tag()}",
        help="Run output directory. New run directories are recommended to avoid overwrite.",
    )
    parser.add_argument("--versions", type=str, default="A,B,C,D,E,F,G")
    parser.add_argument("--attack-source", type=str, default="first")
    parser.add_argument("--label-source", type=str, default="first")
    parser.add_argument(
        "--na-attack-policy",
        choices=("drop_participant", "no_attack", "group_fallback", "first_fallback"),
        default="drop_participant",
    )
    parser.add_argument("--negative-ratio", type=float, default=1.0, help="Target n_neg / n_pos ratio.")
    parser.add_argument(
        "--negative-policy",
        choices=("full_relabel", "flip_one", "flip_k", "rn_hardmix"),
        default="full_relabel",
        help=(
            "Negative generation policy. "
            "flip_one swaps exactly one argument label in<->out and leaves undec unchanged; "
            "flip_k swaps exactly k argument labels in<->out and leaves undec unchanged; "
            "rn_hardmix mixes reliable (multi-flip) and hard (single-flip) negatives."
        ),
    )
    parser.add_argument(
        "--negative-flip-k",
        type=int,
        default=2,
        help="Max number of in/out flips for rn_hardmix reliable negatives.",
    )
    parser.add_argument(
        "--rn-reliable-fraction",
        type=float,
        default=0.7,
        help="Fraction of rn_hardmix negatives generated with multi-flip reliable mutations.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--weight-mode", choices=("constant", "confidence_linear"), default="constant")
    parser.add_argument("--base-weight", type=int, default=100)
    parser.add_argument("--confidence-max", type=float, default=4.0)
    parser.add_argument(
        "--background-file",
        type=Path,
        default=repo_root / "background_knowledge.lp",
    )
    parser.add_argument(
        "--mode-file",
        type=Path,
        default=repo_root / "mode_declarations.las",
    )
    parser.add_argument("--train-timeout-seconds", type=int, default=1200)
    parser.add_argument(
        "--semantics",
        type=str,
        default=None,
        help="Optional semantics key used to resolve central ILASP policy (e.g. PRF).",
    )
    parser.add_argument("--ilasp-extra-args", type=str, default="")
    parser.add_argument(
        "--ilasp-config",
        type=Path,
        default=REPO_ROOT / "ilasp_config.json",
    )
    parser.add_argument(
        "--semantics-config",
        type=Path,
        default=REPO_ROOT / "semantics_config.json",
    )
    parser.add_argument("--skip-ilasp", action="store_true")
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    versions = parse_versions(args.versions)
    if args.negative_ratio < 0:
        raise ValueError("--negative-ratio must be >= 0.")
    if args.negative_flip_k <= 0:
        raise ValueError("--negative-flip-k must be > 0.")
    if not (0.0 <= args.rn_reliable_fraction <= 1.0):
        raise ValueError("--rn-reliable-fraction must be in [0,1].")

    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.allow_overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {args.output_dir}. "
            "Pass --allow-overwrite or choose a new output directory."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    extracted_dir = args.output_dir / "extracted"
    asp_dir = args.output_dir / "asp_files"
    ilasp_tasks_dir = args.output_dir / "ilasp_tasks"
    learned_dir = args.output_dir / "learned_encodings"
    logs_dir = args.output_dir / "logs"
    for d in (extracted_dir, asp_dir, ilasp_tasks_dir, learned_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    extractor_script = script_dir / "extract_labeled_aafs.py"
    if not extractor_script.exists():
        raise FileNotFoundError(f"Missing extractor script: {extractor_script}")
    if not args.background_file.exists():
        raise FileNotFoundError(f"Missing background file: {args.background_file}")
    if not args.mode_file.exists():
        raise FileNotFoundError(f"Missing mode file: {args.mode_file}")

    run_config = {
        "timestamp": timestamp_tag(),
        "paper_reference": PAPER_REFERENCE,
        "versions": versions,
        "attack_source": args.attack_source,
        "label_source": args.label_source,
        "na_attack_policy": args.na_attack_policy,
        "negative_ratio": args.negative_ratio,
        "negative_policy": args.negative_policy,
        "negative_flip_k": args.negative_flip_k,
        "rn_reliable_fraction": args.rn_reliable_fraction,
        "weight_mode": args.weight_mode,
        "base_weight": args.base_weight,
        "confidence_max": args.confidence_max,
        "train_timeout_seconds": args.train_timeout_seconds,
        "skip_ilasp": args.skip_ilasp,
        "semantics": args.semantics,
        "ilasp_extra_args": [a.strip() for a in args.ilasp_extra_args.split(",") if a.strip()],
        "ilasp_config": str(args.ilasp_config),
        "semantics_config": str(args.semantics_config),
        "data_path": str(args.data_path),
        "background_file": str(args.background_file),
        "mode_file": str(args.mode_file),
    }
    (args.output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    print("[Stage 1/5] Extracting participant AAFs...")
    run_extractor(
        script_path=extractor_script,
        data_path=args.data_path,
        output_dir=extracted_dir,
        versions=versions,
        attack_source=args.attack_source,
        label_source=args.label_source,
        na_attack_policy=args.na_attack_policy,
    )

    manifest_csv = extracted_dir / "extraction_manifest.csv"
    manifest_json = extracted_dir / "extraction_manifest.json"
    if not manifest_csv.exists():
        raise FileNotFoundError(f"Missing extraction manifest: {manifest_csv}")
    manifest_rows: List[dict] = list(csv.DictReader(manifest_csv.open("r", encoding="utf-8")))
    if not manifest_rows:
        raise RuntimeError("Extraction produced zero rows.")

    attack_key, attack_phase, label_key, label_phase = select_single_combo(manifest_rows)
    label_column = manifest_rows[0].get("label_column", "")

    confidence_map, confidence_column = build_confidence_map(
        data_path=args.data_path,
        versions=versions,
        label_phase=label_phase,
        label_column=label_column,
    )
    structure_report = build_structure_report(args.data_path, versions)
    (args.output_dir / "paper_structure_report.json").write_text(
        json.dumps(
            {
                "paper_reference": PAPER_REFERENCE,
                "graph_structure": structure_report,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[Stage 2/5] Building positive dataset...")
    examples_manifest_rows: List[dict] = []
    pos_by_version: Dict[str, List[dict]] = defaultdict(list)

    for row in manifest_rows:
        version = row["version"].strip().upper()
        if version not in versions:
            continue
        pid = row["pid"].strip()
        src = Path(row["file_path"])
        if not src.exists():
            raise FileNotFoundError(f"Extracted file missing: {src}")

        participant_file = row["participant_file"].strip()
        dest = asp_dir / f"version{version}" / "pos" / participant_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        confidence = confidence_map.get(pid)
        weight = compute_weight(
            confidence_value=confidence,
            weight_mode=args.weight_mode,
            base_weight=args.base_weight,
            confidence_max=args.confidence_max,
        )

        info = {
            "version": version,
            "pid": pid,
            "kind": "pos",
            "source_pid": pid,
            "file_path": str(dest),
            "weight": str(weight),
            "confidence_value": "" if confidence is None else f"{confidence:.6g}",
            "confidence_column": confidence_column or "",
            "attack_source_key": attack_key,
            "attack_phase": attack_phase,
            "label_source_key": label_key,
            "label_phase": label_phase,
        }
        pos_by_version[version].append(info)
        examples_manifest_rows.append(info)

    print("[Stage 3/5] Generating negative examples...")
    rng = random.Random(args.seed)
    neg_by_version: Dict[str, List[dict]] = defaultdict(list)
    parsed_cache: Dict[str, ParsedAAF] = {}

    def get_parsed(info: Dict[str, str]) -> ParsedAAF:
        key = info["file_path"]
        cached = parsed_cache.get(key)
        if cached is not None:
            return cached
        parsed = parse_lp_instance(Path(key))
        parsed_cache[key] = parsed
        return parsed

    for version in versions:
        positives = sorted(pos_by_version[version], key=lambda x: x["pid"])
        n_pos = len(positives)
        if n_pos == 0:
            continue

        source_pool = positives
        if args.negative_policy in {"flip_one", "flip_k", "rn_hardmix"}:
            min_flippable = 1 if args.negative_policy != "flip_k" else int(args.negative_flip_k)
            source_pool = [
                info
                for info in positives
                if sum(1 for label in get_parsed(info).labels.values() if label in {"in", "out"}) >= min_flippable
            ]
            if not source_pool:
                raise ValueError(
                    f"Cannot generate {args.negative_policy} negatives for version {version}: "
                    f"not enough flippable in/out labels for k={args.negative_flip_k}."
                )

        target_neg = int(round(n_pos * args.negative_ratio))
        if args.negative_ratio > 0 and target_neg == 0:
            target_neg = 1

        if target_neg == 0:
            continue

        if target_neg <= len(source_pool):
            selected = rng.sample(source_pool, target_neg)
        else:
            pool = source_pool[:]
            rng.shuffle(pool)
            selected = [pool[i % len(pool)] for i in range(target_neg)]

        counts = Counter(x["pid"] for x in selected)
        seen_counter: Dict[str, int] = defaultdict(int)

        for src_info in selected:
            src_pid = src_info["pid"]
            seen_counter[src_pid] += 1
            occurrence = seen_counter[src_pid]

            src_path = Path(src_info["file_path"])
            parsed_pos = get_parsed(src_info)
            parsed_neg = build_negative_from_positive(
                parsed_pos,
                rng=rng,
                policy=args.negative_policy,
                flip_k=args.negative_flip_k,
                rn_reliable_fraction=args.rn_reliable_fraction,
            )
            if parsed_neg is None:
                # Defensive guard: should be unreachable because source_pool already filters this.
                continue

            pos_stem = src_path.stem
            if counts[src_pid] == 1:
                neg_name = f"{pos_stem}.lp"
                neg_example_id = f"{src_pid}_neg"
            else:
                neg_name = f"{pos_stem}_neg{occurrence}.lp"
                neg_example_id = f"{src_pid}_neg{occurrence}"

            neg_path = asp_dir / f"version{version}" / "neg" / neg_name
            neg_path.parent.mkdir(parents=True, exist_ok=True)
            write_lp_instance(neg_path, parsed_neg)

            info = {
                "version": version,
                "pid": neg_example_id,
                "kind": "neg",
                "source_pid": src_pid,
                "file_path": str(neg_path),
                "weight": src_info["weight"],
                "confidence_value": src_info["confidence_value"],
                "confidence_column": src_info["confidence_column"],
                "attack_source_key": attack_key,
                "attack_phase": attack_phase,
                "label_source_key": label_key,
                "label_phase": label_phase,
            }
            neg_by_version[version].append(info)
            examples_manifest_rows.append(info)

    print("[Stage 4/5] Building ILASP tasks...")
    background_text = args.background_file.read_text(encoding="utf-8").strip()
    mode_text = args.mode_file.read_text(encoding="utf-8").strip()
    ilasp_extra_args = resolve_ilasp_args(
        semantics=args.semantics,
        ilasp_config_path=str(args.ilasp_config),
        semantics_config_path=str(args.semantics_config),
        extra_args=[a.strip() for a in args.ilasp_extra_args.split(",") if a.strip()],
    )

    task_summary: Dict[str, dict] = {}
    for version in versions:
        pos_infos = sorted(pos_by_version[version], key=lambda x: x["pid"])
        neg_infos = sorted(neg_by_version[version], key=lambda x: x["pid"])

        if not pos_infos:
            continue

        directives: List[str] = []
        for info in pos_infos:
            parsed = parse_lp_instance(Path(info["file_path"]))
            directives.append(
                render_ilasp_example(
                    example_type="pos",
                    example_id=f"{info['pid']}_pos",
                    weight=int(info["weight"]),
                    parsed=parsed,
                )
            )
        for info in neg_infos:
            parsed = parse_lp_instance(Path(info["file_path"]))
            directives.append(
                render_ilasp_example(
                    example_type="neg",
                    example_id=info["pid"],
                    weight=int(info["weight"]),
                    parsed=parsed,
                )
            )

        rng.shuffle(directives)
        task_file = ilasp_tasks_dir / f"version{version}.las"
        task_text = "\n".join(directives) + "\n\n" + background_text + "\n\n" + mode_text + "\n"
        task_file.write_text(task_text, encoding="utf-8")

        task_summary[version] = {
            "task_file": str(task_file),
            "n_pos": len(pos_infos),
            "n_neg": len(neg_infos),
            "negative_ratio_realized": (len(neg_infos) / len(pos_infos)) if pos_infos else 0.0,
        }

    training_rows: List[dict] = []
    if not args.skip_ilasp:
        print("[Stage 5/5] Training ILASP per version...")
        for version in versions:
            if version not in task_summary:
                continue
            task_file = Path(task_summary[version]["task_file"])
            model_file = learned_dir / f"version{version}.lp"
            log_file = logs_dir / f"version{version}.log"

            result = run_ilasp(
                task_file=task_file,
                model_file=model_file,
                log_file=log_file,
                timeout_seconds=args.train_timeout_seconds,
                extra_args=ilasp_extra_args,
            )
            training_rows.append(
                {
                    "version": version,
                    "task_file": str(task_file),
                    "model_file": str(model_file),
                    "log_file": str(log_file),
                    "n_pos": task_summary[version]["n_pos"],
                    "n_neg": task_summary[version]["n_neg"],
                    "timed_out": int(result["timed_out"]),
                    "return_code": "" if result["return_code"] is None else result["return_code"],
                    "succeeded": int(result["succeeded"]),
                    "elapsed_seconds": f"{result['elapsed_seconds']:.6f}",
                    "command": " ".join(result["command"]),
                }
            )

    examples_manifest_path = args.output_dir / "examples_manifest.csv"
    if examples_manifest_rows:
        fieldnames = list(examples_manifest_rows[0].keys())
        with examples_manifest_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(examples_manifest_rows)
    else:
        examples_manifest_path.write_text("", encoding="utf-8")

    training_csv_path = args.output_dir / "training_summary.csv"
    if training_rows:
        fieldnames = list(training_rows[0].keys())
        with training_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(training_rows)
    else:
        training_csv_path.write_text("", encoding="utf-8")

    run_summary = {
        "paper_reference": PAPER_REFERENCE,
        "config": run_config,
        "selected_combo": {
            "attack_source_key": attack_key,
            "attack_phase": attack_phase,
            "label_source_key": label_key,
            "label_phase": label_phase,
            "confidence_column": confidence_column,
        },
        "paper_structure_report": structure_report,
        "task_summary": task_summary,
        "examples_manifest_csv": str(examples_manifest_path),
        "training_summary_csv": str(training_csv_path),
    }
    (args.output_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2), encoding="utf-8")

    print("✅ Real-world pipeline completed.")
    print(f"Run directory: {args.output_dir}")
    print(f"Task summary versions: {sorted(task_summary.keys())}")
    if not args.skip_ilasp:
        completed = sum(int(row["succeeded"]) for row in training_rows)
        print(f"ILASP training succeeded for {completed}/{len(training_rows)} versions.")


if __name__ == "__main__":
    main()
