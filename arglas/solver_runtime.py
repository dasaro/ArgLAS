from dataclasses import dataclass
from typing import Optional

import clingo

from arglas.artifact_paths import resolve_repo_path
from arglas.solver_policy import (
    get_background_file,
    get_clingo_args,
    get_completion_rules_enabled,
    get_semantics_entry,
    get_show_predicates,
)


@dataclass(frozen=True)
class SemanticsRuntime:
    semantics_file: str
    background_file: Optional[str]
    clingo_args: tuple[str, ...]
    completion_rules: bool
    show_predicates: tuple[str, ...]


_completion_rules_program_cache = None


def _completion_rules_program():
    global _completion_rules_program_cache
    if _completion_rules_program_cache is None:
        with open(resolve_repo_path("completion_rules.lp"), "r", encoding="utf-8") as f:
            _completion_rules_program_cache = f.read()
    return _completion_rules_program_cache


def solve_models(
    files_to_load,
    clingo_args=None,
    completion_rules=False,
    additional_program=None,
    show_predicates=None,
):
    args = ["-n", "0", "--warn=none"] + list(clingo_args or [])
    ctl = clingo.Control(args)

    for path in files_to_load:
        if not path:
            continue
        ctl.load(path)

    if completion_rules:
        ctl.add("base", [], _completion_rules_program())

    if additional_program:
        ctl.add("base", [], additional_program)

    for predicate in (show_predicates or ["in/1"]):
        ctl.add("base", [], f"#show {predicate}.")
    ctl.ground([("base", [])])

    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(set(str(sym) for sym in model.symbols(shown=True)))
    return models


def build_semantics_runtime(semantics_config, semantics, stage="train_test_ground_truth"):
    semantics_entry = get_semantics_entry(semantics_config, semantics)
    background_file = get_background_file(semantics_config, stage=stage, semantics=semantics)
    return SemanticsRuntime(
        semantics_file=resolve_repo_path(semantics_entry["file"]),
        background_file=resolve_repo_path(background_file) if background_file else None,
        clingo_args=tuple(get_clingo_args(semantics_config, semantics, stage=stage)),
        completion_rules=get_completion_rules_enabled(semantics_config, stage=stage, semantics=semantics),
        show_predicates=tuple(get_show_predicates(semantics_config, stage=stage, semantics=semantics)),
    )


def solve_semantics_instance(runtime, instance_file, additional_program=None, extra_files=None):
    files_to_load = [runtime.background_file, runtime.semantics_file]
    if extra_files:
        files_to_load.extend(extra_files)
    files_to_load.append(instance_file)
    return solve_models(
        files_to_load=files_to_load,
        clingo_args=list(runtime.clingo_args),
        completion_rules=runtime.completion_rules,
        additional_program=additional_program,
        show_predicates=list(runtime.show_predicates),
    )
