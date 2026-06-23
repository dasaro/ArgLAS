#!/usr/bin/env python3
"""
Generalized extractor for real-world labeled AAFs.

The script reconstructs per-participant `.lp` files from raw questionnaire data,
explicitly supporting all paper phases:
 - Part A (attack drawing): first individual / group / final individual
 - Part B (acceptability): first individual / group / final individual

It writes one dataset per (attack source, label source) combination and tracks
provenance in CSV/JSON manifests.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from zipfile import ZipFile

import xml.etree.ElementTree as ET


XML_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

PAPER_PART_A_PHASE_TO_COLUMN = {
    "first": "1ST_RESPONSE",
    "group": "GROUP_RESPONSE",
    "final": "2ND_RESPONSE",
}

PAPER_PART_B_PHASE_TO_COLUMN = {
    "first": "1ST_RESPONSE",
    "group": "GROUP_RESP",
    "final": "2ND_RESPONSE",
}

PAPER_PART_A_COLUMN_TO_PHASE = {v: k for k, v in PAPER_PART_A_PHASE_TO_COLUMN.items()}
PAPER_PART_B_COLUMN_TO_PHASE = {v: k for k, v in PAPER_PART_B_PHASE_TO_COLUMN.items()}

LABEL_MAP = {
    "accept": "in",
    "reject": "out",
    "undecided": "undec",
}

PAPER_REFERENCE = {
    "citation": (
        "PLOS ONE (2022), doi:10.1371/journal.pone.0273225; "
        "Method sections 'Part A' and 'Part B'."
    ),
    "paper_pdf": "Real_World_Examples/Paper/pone.0273225.pdf",
    "protocol_summary": (
        "Both Part A and Part B use three phases: first individual, group, "
        "final individual."
    ),
    "local_mapping_note": "Real_World_Examples/RAW_DATA_PAPER_MAPPING.md",
}


def normalize_header(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_")
    return cleaned.upper()


def excel_col_to_index(cell_ref: str) -> Optional[int]:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    if not match:
        return None
    index = 0
    for ch in match.group(1):
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index


def read_shared_strings(zip_file: ZipFile) -> List[str]:
    path = "xl/sharedStrings.xml"
    if path not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read(path))
    out: List[str] = []
    for node in root.findall("m:si", XML_NS):
        out.append("".join(text_node.text or "" for text_node in node.findall(".//m:t", XML_NS)))
    return out


def read_xlsx_sheet(path: Path, sheet_name: str) -> List[Dict[str, str]]:
    with ZipFile(path) as zip_file:
        shared = read_shared_strings(zip_file)

        workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
        rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
        rel_id_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        }

        rel_id: Optional[str] = None
        for sheet in workbook.find("m:sheets", XML_NS).findall("m:sheet", XML_NS):
            if sheet.attrib.get("name") == sheet_name:
                rel_id = sheet.attrib.get(f"{{{XML_NS['r']}}}id")
                break

        if rel_id is None:
            raise ValueError(f"Sheet not found: {sheet_name}")

        target = rel_id_to_target[rel_id]
        if not target.startswith("xl/"):
            target = f"xl/{target}"

        root = ET.fromstring(zip_file.read(target))
        rows_xml = root.find("m:sheetData", XML_NS).findall("m:row", XML_NS)
        if not rows_xml:
            return []

        parsed_rows: List[Dict[int, str]] = []
        for row_node in rows_xml:
            row_data: Dict[int, str] = {}
            for cell in row_node.findall("m:c", XML_NS):
                col_idx = excel_col_to_index(cell.attrib.get("r", ""))
                if col_idx is None:
                    continue
                cell_type = cell.attrib.get("t")
                v_node = cell.find("m:v", XML_NS)
                if v_node is not None:
                    raw = v_node.text or ""
                    if cell_type == "s" and raw.isdigit():
                        index = int(raw)
                        value = shared[index] if 0 <= index < len(shared) else raw
                    else:
                        value = raw
                else:
                    inline_text = cell.find("m:is/m:t", XML_NS)
                    value = inline_text.text if inline_text is not None else ""
                row_data[col_idx] = value
            parsed_rows.append(row_data)

        if not parsed_rows:
            return []

        header_row = parsed_rows[0]
        max_header_col = max(header_row.keys()) if header_row else 0
        headers = [normalize_header(header_row.get(i, f"COL_{i}")) for i in range(1, max_header_col + 1)]

        records: List[Dict[str, str]] = []
        for row_data in parsed_rows[1:]:
            if not row_data:
                continue
            record = {headers[i - 1]: row_data.get(i, "") for i in range(1, max_header_col + 1)}
            if any(str(v).strip() for v in record.values()):
                records.append(record)
        return records


def parse_relation_atom(relation: str) -> Optional[Tuple[str, str]]:
    match = re.fullmatch(r"\s*([A-Za-z]+)_attacks_([A-Za-z]+)\s*", relation or "")
    if not match:
        return None
    return match.group(1).lower(), match.group(2).lower()


def normalize_attack_response(value: str) -> Optional[bool]:
    v = (value or "").strip().lower()
    if v == "attack":
        return True
    if v == "no_attack":
        return False
    if v in {"", "na", "n/a"}:
        return None
    return None


def normalize_label_response(value: str) -> Optional[str]:
    v = (value or "").strip().lower()
    if not v:
        return None
    return LABEL_MAP.get(v)


def parse_csv_list(raw: str) -> List[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def resolve_phases(raw: str, valid: Sequence[str]) -> List[str]:
    if raw.strip().lower() == "all":
        return list(valid)
    phases = [p.lower() for p in parse_csv_list(raw)]
    bad = [p for p in phases if p not in valid]
    if bad:
        raise ValueError(f"Invalid phase(s): {bad}. Valid: {list(valid)} or 'all'.")
    return phases


def resolve_versions(raw: str) -> List[str]:
    versions = [v.upper() for v in parse_csv_list(raw)]
    if not versions:
        raise ValueError("At least one version must be selected.")
    for v in versions:
        if not re.fullmatch(r"[A-Z]", v):
            raise ValueError(f"Invalid version token: {v}")
    return versions


def build_pid(participant: str, version: str) -> str:
    return f"p{str(participant).strip()}_version{str(version).strip().upper()}"


def to_source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def detect_response_columns(headers: Iterable[str]) -> List[str]:
    out: List[str] = []
    for col in headers:
        c = normalize_header(col)
        if "CORRECT" in c:
            continue
        if "RESPONSE" in c or c.endswith("RESP"):
            out.append(c)
    return sorted(set(out))


def resolve_response_sources(
    selector: str,
    headers: Iterable[str],
    paper_map: Dict[str, str],
) -> List[Tuple[str, str]]:
    header_set = set(normalize_header(h) for h in headers)
    normalized_selector = (selector or "").strip().lower()

    if normalized_selector == "paper":
        missing = [col for col in paper_map.values() if normalize_header(col) not in header_set]
        if missing:
            raise ValueError(f"Missing paper response column(s): {missing}")
        return [(phase, paper_map[phase]) for phase in ("first", "group", "final")]

    if normalized_selector == "all":
        response_cols = detect_response_columns(header_set)
        if not response_cols:
            raise ValueError("No response columns detected in selected sheet.")
        return [(to_source_key(col), col) for col in response_cols]

    tokens = [t.strip() for t in parse_csv_list(selector)]
    if not tokens:
        raise ValueError("At least one response source must be selected.")

    out: List[Tuple[str, str]] = []
    for token in tokens:
        token_lower = token.lower()
        if token_lower in paper_map:
            out.append((token_lower, paper_map[token_lower]))
            continue

        normalized_token = normalize_header(token)
        if normalized_token in header_set:
            out.append((to_source_key(normalized_token), normalized_token))
            continue

        raise ValueError(
            f"Unsupported response source token '{token}'. "
            f"Use paper aliases {list(paper_map.keys())}, explicit column names, or 'all'."
        )

    # preserve input order while removing duplicates
    dedup: List[Tuple[str, str]] = []
    seen = set()
    for key, col in out:
        if (key, col) in seen:
            continue
        seen.add((key, col))
        dedup.append((key, col))
    return dedup


def policy_resolve_attack(
    row: Dict[str, str],
    attack_col: str,
    policy: str,
) -> Optional[bool]:
    direct = normalize_attack_response(row.get(attack_col, ""))
    if direct is not None:
        return direct

    if policy == "drop_participant":
        return None
    if policy == "no_attack":
        return False
    if policy == "group_fallback":
        return normalize_attack_response(row.get(PAPER_PART_A_PHASE_TO_COLUMN["group"], ""))
    if policy == "first_fallback":
        return normalize_attack_response(row.get(PAPER_PART_A_PHASE_TO_COLUMN["first"], ""))
    raise ValueError(f"Unsupported policy: {policy}")


def write_lp_file(
    out_path: Path,
    args: Sequence[str],
    attacks: Sequence[Tuple[str, str]],
    labels: Dict[str, str],
) -> None:
    lines: List[str] = []
    for arg in args:
        lines.append(f"arg({arg}).")
    for src, tgt in sorted(set(attacks)):
        lines.append(f"att({src},{tgt}).")
    for status in ("in", "out", "undec"):
        status_args = sorted(arg for arg, label in labels.items() if label == status)
        for arg in status_args:
            lines.append(f"{status}({arg}).")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Extract per-participant AAF `.lp` files from raw questionnaire data, "
            "supporting all paper response phases."
        )
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=script_dir / "Raw_Data_original.xlsx",
        help="Path to source workbook (default: Real_World_Examples/Raw_Data_original.xlsx).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / "asp_files_extracted",
        help="Output root directory for extracted datasets.",
    )
    parser.add_argument(
        "--versions",
        type=str,
        default="A,B,C,D,E,F,G",
        help="Comma-separated versions to include (e.g., A,B,C).",
    )
    parser.add_argument(
        "--attack-sources",
        type=str,
        default="paper",
        help=(
            "Part A response sources. Use paper aliases (first,group,final), "
            "explicit column names, comma lists, 'paper', or 'all'."
        ),
    )
    parser.add_argument(
        "--label-sources",
        type=str,
        default="paper",
        help=(
            "Part B response sources. Use paper aliases (first,group,final), "
            "explicit column names, comma lists, 'paper', or 'all'."
        ),
    )
    parser.add_argument(
        "--attack-phases",
        type=str,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--label-phases",
        type=str,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--na-attack-policy",
        choices=("drop_participant", "no_attack", "group_fallback", "first_fallback"),
        default="drop_participant",
        help=(
            "Policy when selected Part A phase is NA/empty for a relation. "
            "drop_participant is the strict option."
        ),
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow writing into a non-empty output directory.",
    )
    args = parser.parse_args()

    versions = resolve_versions(args.versions)
    # Backward compatibility for older callers using --attack-phases/--label-phases.
    attack_selector = args.attack_sources
    if args.attack_phases is not None:
        attack_phases = resolve_phases(args.attack_phases, PAPER_PART_A_PHASE_TO_COLUMN.keys())
        attack_selector = ",".join(attack_phases)
    label_selector = args.label_sources
    if args.label_phases is not None:
        label_phases = resolve_phases(args.label_phases, PAPER_PART_B_PHASE_TO_COLUMN.keys())
        label_selector = ",".join(label_phases)

    if not args.data_path.exists():
        raise FileNotFoundError(f"Workbook not found: {args.data_path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()) and not args.allow_overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {args.output_dir}. "
            "Pass --allow-overwrite to proceed."
        )

    part_a_rows = read_xlsx_sheet(args.data_path, "PART_A")
    part_b_rows = read_xlsx_sheet(args.data_path, "PART_B")
    part_a_headers = list(part_a_rows[0].keys()) if part_a_rows else []
    part_b_headers = list(part_b_rows[0].keys()) if part_b_rows else []

    attack_sources = resolve_response_sources(
        attack_selector,
        part_a_headers,
        PAPER_PART_A_PHASE_TO_COLUMN,
    )
    label_sources = resolve_response_sources(
        label_selector,
        part_b_headers,
        PAPER_PART_B_PHASE_TO_COLUMN,
    )

    by_pid_part_a: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    by_pid_part_b: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    pid_to_version: Dict[str, str] = {}

    for row in part_a_rows:
        version = str(row.get("VERSION", "")).strip().upper()
        participant = str(row.get("PARTICIPANT", "")).strip()
        if version not in versions or not participant:
            continue
        pid = build_pid(participant, version)
        by_pid_part_a[pid].append(row)
        pid_to_version[pid] = version

    for row in part_b_rows:
        version = str(row.get("VERSION", "")).strip().upper()
        participant = str(row.get("PARTICIPANT", "")).strip()
        if version not in versions or not participant:
            continue
        pid = build_pid(participant, version)
        by_pid_part_b[pid].append(row)
        pid_to_version[pid] = version

    available_pids = sorted(set(by_pid_part_a) & set(by_pid_part_b))

    manifest_rows: List[Dict[str, str]] = []
    combo_stats: Dict[str, Counter] = defaultdict(Counter)

    for attack_key, attack_col in attack_sources:
        attack_phase = PAPER_PART_A_COLUMN_TO_PHASE.get(attack_col, "")
        for label_key, label_col in label_sources:
            label_phase = PAPER_PART_B_COLUMN_TO_PHASE.get(label_col, "")
            combo_name = f"att_{to_source_key(attack_key)}__lab_{to_source_key(label_key)}"

            for pid in available_pids:
                version = pid_to_version[pid]
                part_a = by_pid_part_a[pid]
                part_b = by_pid_part_b[pid]

                args_set = {str(r.get("ITEM", "")).strip().lower() for r in part_b if str(r.get("ITEM", "")).strip()}
                if not args_set:
                    combo_stats[combo_name]["skipped_no_args"] += 1
                    continue
                args_sorted = sorted(args_set)

                attacks: List[Tuple[str, str]] = []
                na_count = 0
                drop_for_attack = False
                for row in part_a:
                    relation = parse_relation_atom(str(row.get("RELATION", "")))
                    if relation is None:
                        continue
                    src, tgt = relation
                    attack_value = policy_resolve_attack(row, attack_col, args.na_attack_policy)
                    if attack_value is None:
                        na_count += 1
                        drop_for_attack = True
                        break
                    if attack_value:
                        attacks.append((src, tgt))
                if drop_for_attack:
                    combo_stats[combo_name]["skipped_na_attack"] += 1
                    continue

                labels: Dict[str, str] = {}
                bad_labels = 0
                for row in part_b:
                    arg = str(row.get("ITEM", "")).strip().lower()
                    if not arg:
                        continue
                    label = normalize_label_response(str(row.get(label_col, "")))
                    if label is None:
                        bad_labels += 1
                        break
                    labels[arg] = label
                if bad_labels > 0:
                    combo_stats[combo_name]["skipped_bad_label"] += 1
                    continue
                if set(labels) != set(args_sorted):
                    combo_stats[combo_name]["skipped_incomplete_label_set"] += 1
                    continue

                participant_stem = pid.split("_", 1)[0]  # pXX
                out_dir = args.output_dir / f"version{version}" / combo_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"{participant_stem}.lp"
                write_lp_file(out_file, args_sorted, attacks, labels)

                combo_stats[combo_name]["generated"] += 1
                manifest_rows.append(
                    {
                        "pid": pid,
                        "version": version,
                        "participant_file": f"{participant_stem}.lp",
                        "file_path": str(out_file),
                        "attack_source_key": attack_key,
                        "attack_phase": attack_phase,
                        "attack_column": attack_col,
                        "label_source_key": label_key,
                        "label_phase": label_phase,
                        "label_column": label_col,
                        "n_args": str(len(args_sorted)),
                        "n_attacks": str(len(set(attacks))),
                        "n_in": str(sum(1 for v in labels.values() if v == "in")),
                        "n_out": str(sum(1 for v in labels.values() if v == "out")),
                        "n_undec": str(sum(1 for v in labels.values() if v == "undec")),
                        "na_attack_relations": str(na_count),
                        "paper_reference": PAPER_REFERENCE["citation"],
                    }
                )

    manifest_csv_path = args.output_dir / "extraction_manifest.csv"
    if manifest_rows:
        fieldnames = list(manifest_rows[0].keys())
        with manifest_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest_rows)
    else:
        manifest_csv_path.write_text("", encoding="utf-8")

    summary = {
        "data_path": str(args.data_path),
        "output_dir": str(args.output_dir),
        "versions": versions,
        "attack_selector": attack_selector,
        "label_selector": label_selector,
        "attack_sources": [
            {
                "source_key": key,
                "column": col,
                "paper_phase": PAPER_PART_A_COLUMN_TO_PHASE.get(col, ""),
            }
            for key, col in attack_sources
        ],
        "label_sources": [
            {
                "source_key": key,
                "column": col,
                "paper_phase": PAPER_PART_B_COLUMN_TO_PHASE.get(col, ""),
            }
            for key, col in label_sources
        ],
        "na_attack_policy": args.na_attack_policy,
        "phase_columns": {
            "part_a": PAPER_PART_A_PHASE_TO_COLUMN,
            "part_b": PAPER_PART_B_PHASE_TO_COLUMN,
        },
        "available_response_columns": {
            "part_a": detect_response_columns(part_a_headers),
            "part_b": detect_response_columns(part_b_headers),
        },
        "paper_reference": PAPER_REFERENCE,
        "participants_with_both_parts": len(available_pids),
        "generated_files": len(manifest_rows),
        "combination_stats": {k: dict(v) for k, v in sorted(combo_stats.items())},
        "manifest_csv": str(manifest_csv_path),
    }

    summary_path = args.output_dir / "extraction_manifest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        f"Extracted {len(manifest_rows)} AAF files across "
        f"{len(attack_sources) * len(label_sources)} source combinations."
    )
    print(f"CSV manifest: {manifest_csv_path}")
    print(f"JSON summary: {summary_path}")


if __name__ == "__main__":
    main()
