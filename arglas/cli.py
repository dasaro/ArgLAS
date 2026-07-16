import argparse
import sys
from pathlib import Path
from typing import Iterable

from arglas import __version__
from arglas import cleanup
from arglas import generate_aafs
from arglas import generate_extensions
from arglas import generate_ilasp_task
from arglas import train_test
from arglas import validate_config
from arglas import demo as demo_module
from arglas.artifact_paths import repo_root, resolve_repo_path
from arglas.validate_config import load_batch_config

# Single dispatch table for the core commands: both the argparse subcommands
# and the fast-path in main() are generated from it.
CORE_COMMANDS = {
    "generate-aafs": (generate_aafs.main, "Generate random AAF instances."),
    "label": (generate_extensions.main, "Label generated AAFs under a selected semantics."),
    "build-task": (generate_ilasp_task.main, "Build an ILASP learning task from labelled examples."),
    "learn": (train_test.main, "Run the synthetic ILASP train/test pipeline."),
    "demo": (demo_module.main,
             "End-to-end mini pipeline: generate AAFs, label, build task, learn (about a minute)."),
}

# Benchmark subcommands -> experiments/ module names (lazily imported).
BENCHMARK_COMMANDS = {
    "run": ("run_experiment_grid", "Run a benchmark grid from a JSON config."),
    "watch": ("watch_experiment_grid", "Watch and restart a benchmark grid from a JSON config."),
    "replay": ("replay_archived_evaluation", "Replay archived learned models through the current evaluator."),
    "progress": ("campaign_progress", "Show a progress bar for a benchmark grid (add --watch N for a live bar)."),
}


def _experiments(module_name):
    """Lazy-import an orchestration module from experiments/ (kept outside the
    core package; used only by the `benchmark` command group)."""
    import importlib
    exp_dir = str(repo_root() / "experiments")
    if exp_dir not in sys.path:
        sys.path.insert(0, exp_dir)
    return importlib.import_module(module_name)


def sanitize_decimal(value) -> str:
    return str(value).replace(".", "_")


def run_wrapped(main_func, forwarded_args: Iterable[str], prog: str = None) -> int:
    original_argv0 = sys.argv[0]
    try:
        if prog:
            sys.argv[0] = prog
        return int(main_func(list(forwarded_args)) or 0)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        # Mirror the interpreter's default for SystemExit("message").
        print(code, file=sys.stderr)
        return 1
    finally:
        sys.argv[0] = original_argv0


def batch_validate(args) -> int:
    return validate_config.main(
        config_path=resolve_repo_path(args.config, "batch_config.json"),
        semantics_config_path=resolve_repo_path(args.semantics_config, "semantics_config.json"),
        ilasp_config_path=resolve_repo_path(getattr(args, "ilasp_config", "ilasp_config.json"), "ilasp_config.json"),
    )


def batch_cleanup(args) -> int:
    return cleanup.main(config_path=resolve_repo_path(args.config, "batch_config.json"))


def batch_label(args) -> int:
    cfg = load_batch_config(args.config)
    for semantics in cfg["semantics"]:
        for partial in cfg["partials"]:
            argv = [
                "--semantics",
                str(semantics),
                "--p_partial",
                str(partial),
                "--input_dir",
                str(cfg["input_dir"]),
                "--base_output_dir",
                str(cfg["base_output_dir"]),
            ]
            if cfg.get("allow_empty"):
                argv.append("--allow_empty")
            rc = generate_extensions.main(argv)
            if rc != 0:
                return rc
    return 0


def batch_learn(args) -> int:
    cfg = load_batch_config(args.config)
    f_neg_values = cfg.get("f_neg_values", cfg["f_values"])
    for semantics in cfg["semantics"]:
        for partial in cfg["partials"]:
            for noise in cfg["noise_values"]:
                results_subdir = (
                    Path(str(cfg["results_dir"]))
                    / f"{semantics}_partial_{sanitize_decimal(partial)}_noise_{sanitize_decimal(noise)}"
                )
                argv = [
                    "--semantics",
                    str(semantics),
                    "--partial",
                    str(partial),
                    "--f_values",
                    *[str(x) for x in cfg["f_values"]],
                    "--f_neg_values",
                    *[str(x) for x in f_neg_values],
                    "--n_values",
                    str(noise),
                    "--iterations",
                    str(cfg["iterations"]),
                    "--base_output_dir",
                    str(cfg["base_output_dir"]),
                    "--train_dir",
                    str(cfg["train_dir"]),
                    "--train_output_dir",
                    str(cfg["train_output_dir"]),
                    "--results_dir",
                    str(results_subdir),
                    "--no_prefix",
                ]
                rc = train_test.main(argv)
                if rc != 0:
                    return rc
    return 0


def batch_pipeline(args) -> int:
    rc = batch_validate(args)
    if rc != 0:
        return rc
    rc = batch_cleanup(args)
    if rc != 0:
        return rc
    rc = batch_label(args)
    if rc != 0:
        return rc
    return batch_learn(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arglas",
        description="ArgLAS CLI for synthetic learning tasks and benchmark orchestration.",
    )
    parser.add_argument("--version", action="version", version=f"arglas {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    for name, (main_func, help_text) in CORE_COMMANDS.items():
        sub = subparsers.add_parser(name, help=help_text, add_help=False)
        sub.add_argument("args", nargs=argparse.REMAINDER)
        sub.set_defaults(
            handler=lambda ns, f=main_func, n=name: run_wrapped(f, ns.args, f"arglas {n}")
        )

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run, watch, or replay benchmark grids.",
    )
    benchmark_subparsers = benchmark_parser.add_subparsers(dest="benchmark_command")
    benchmark_subparsers.required = True

    for name, (module_name, help_text) in BENCHMARK_COMMANDS.items():
        sub = benchmark_subparsers.add_parser(name, help=help_text, add_help=False)
        sub.add_argument("args", nargs=argparse.REMAINDER)
        sub.set_defaults(
            handler=lambda ns, m=module_name, n=name: run_wrapped(
                _experiments(m).main, ns.args, f"arglas benchmark {n}"
            )
        )

    batch_parser = subparsers.add_parser(
        "batch",
        help="Run the legacy batch-config pipeline through the CLI.",
    )
    batch_subparsers = batch_parser.add_subparsers(dest="batch_command")
    batch_subparsers.required = True

    batch_validate_parser = batch_subparsers.add_parser(
        "validate",
        help="Validate batch_config.json against semantics_config.json.",
    )
    batch_validate_parser.add_argument("--config", default="batch_config.json")
    batch_validate_parser.add_argument("--semantics_config", default="semantics_config.json")
    batch_validate_parser.add_argument("--ilasp_config", default="ilasp_config.json")
    batch_validate_parser.set_defaults(handler=batch_validate)

    batch_cleanup_parser = batch_subparsers.add_parser(
        "cleanup",
        help="Clean outputs referenced by batch_config.json.",
    )
    batch_cleanup_parser.add_argument("--config", default="batch_config.json")
    batch_cleanup_parser.add_argument("--semantics_config", default="semantics_config.json")
    batch_cleanup_parser.set_defaults(handler=batch_cleanup)

    batch_label_parser = batch_subparsers.add_parser(
        "label",
        help="Generate all labelled datasets declared in batch_config.json.",
    )
    batch_label_parser.add_argument("--config", default="batch_config.json")
    batch_label_parser.add_argument("--semantics_config", default="semantics_config.json")
    batch_label_parser.set_defaults(handler=batch_label)

    batch_learn_parser = batch_subparsers.add_parser(
        "learn",
        help="Run all train/test benchmark combinations declared in batch_config.json.",
    )
    batch_learn_parser.add_argument("--config", default="batch_config.json")
    batch_learn_parser.add_argument("--semantics_config", default="semantics_config.json")
    batch_learn_parser.set_defaults(handler=batch_learn)

    batch_pipeline_parser = batch_subparsers.add_parser(
        "pipeline",
        help="Validate, clean, label, and run the batch pipeline from batch_config.json.",
    )
    batch_pipeline_parser.add_argument("--config", default="batch_config.json")
    batch_pipeline_parser.add_argument("--semantics_config", default="semantics_config.json")
    batch_pipeline_parser.add_argument("--ilasp_config", default="ilasp_config.json")
    batch_pipeline_parser.set_defaults(handler=batch_pipeline)

    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        # Fast path: forward directly without building the full parser.
        if argv[0] in CORE_COMMANDS:
            return run_wrapped(CORE_COMMANDS[argv[0]][0], argv[1:], f"arglas {argv[0]}")
        if len(argv) >= 2 and argv[0] == "benchmark" and argv[1] in BENCHMARK_COMMANDS:
            return run_wrapped(_experiments(BENCHMARK_COMMANDS[argv[1]][0]).main, argv[2:],
                               f"arglas benchmark {argv[1]}")

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args) or 0)
