import json
import os

from arglas.artifact_paths import resolve_repo_path
from arglas.solver_policy import load_semantics_config, semantics_wants_ilasp_heuristics


def _dedupe_keep_order(values):
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _read_ilasp_args(block, label):
    if not block:
        return []
    args = block.get("ilasp_args", [])
    if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
        raise ValueError(f"Invalid {label}.ilasp_args: expected list[str].")
    return list(args)


def load_ilasp_config(path="ilasp_config.json"):
    path = resolve_repo_path(path, "ilasp_config.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_ilasp_args(
    semantics=None,
    ilasp_config_path="ilasp_config.json",
    semantics_config_path="semantics_config.json",
    extra_args=None,
):
    ilasp_config = load_ilasp_config(ilasp_config_path)
    args = []
    args.extend(_read_ilasp_args(ilasp_config.get("global", {}), "global"))
    if semantics:
        args.extend(_read_ilasp_args(ilasp_config.get(semantics, {}), semantics))

    if extra_args:
        if any(not isinstance(x, str) for x in extra_args):
            raise ValueError("extra_args must be a sequence of strings.")
        args.extend(extra_args)

    args = _dedupe_keep_order(args)

    if semantics:
        semantics_config = load_semantics_config(
            resolve_repo_path(semantics_config_path, "semantics_config.json")
        )
        wants_heuristics = semantics_wants_ilasp_heuristics(semantics_config, semantics)
        if wants_heuristics:
            if "--learn-heuristics" not in args:
                args.append("--learn-heuristics")
        else:
            args = [arg for arg in args if arg != "--learn-heuristics"]

    return args
