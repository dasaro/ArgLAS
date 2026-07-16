import json
import os
import shutil

from arglas.artifact_paths import resolve_repo_path
from arglas.solver_policy import (
    dedupe_keep_order,
    load_semantics_config,
    semantics_wants_ilasp_heuristics,
)

DEFAULT_ILASP_VERSION_ARG = "--version=4"


def require_ilasp():
    """Fail fast with an actionable message when the ILASP binary is missing."""
    if shutil.which("ILASP") is None:
        raise SystemExit(
            "ILASP 4.x not found on PATH — see README Requirements / ilasp.com"
        )


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
    ilasp_config=None,
):
    if ilasp_config is None:
        ilasp_config = load_ilasp_config(ilasp_config_path)
    args = []
    args.extend(_read_ilasp_args(ilasp_config.get("global", {}), "global"))
    if semantics:
        args.extend(_read_ilasp_args(ilasp_config.get(semantics, {}), semantics))

    if extra_args:
        if any(not isinstance(x, str) for x in extra_args):
            raise ValueError("extra_args must be a sequence of strings.")
        args.extend(extra_args)

    args = dedupe_keep_order(args)

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


def build_ilasp_command(task_file, semantics=None, extra_args=None, debug=False):
    """Full ILASP invocation for a task file — the single choke point shared by
    demo and train_test (also checks the binary is on PATH).

    Version default: --version=4 unless the resolved args already pin a version.
    Needed because ILASP 4.4.1 returns a spurious UNSATISFIABLE on ~1/6
    no-choice GRD tasks (minimal repro:
    analysis/grd_prf_lab/g1_definite_core/tasks/_diag_core.las), which
    ilasp_config.json works around with GRD -> --version=2i.

    Pass extra_args when the args were already resolved (train_test resolves
    once per run); otherwise they are resolved from the configs for
    `semantics`. debug=True appends ILASP's -d flag before the task file."""
    require_ilasp()
    if extra_args is None:
        extra_args = resolve_ilasp_args(semantics=semantics)
    extra_args = list(extra_args)
    if any(a.startswith("--version") for a in extra_args):
        base = ["ILASP"]
    else:
        base = ["ILASP", DEFAULT_ILASP_VERSION_ARG]
    return base + extra_args + (["-d"] if debug else []) + [task_file]
