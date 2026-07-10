import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from arglas import cleanup
from arglas import generate_aafs
from arglas import generate_extensions
from arglas import generate_ilasp_task
from arglas import train_test
from arglas import validate_config
from arglas import demo as demo_module
from arglas.artifact_paths import repo_root, resolve_repo_path


def _experiments(module_name):
    """Lazy-import an orchestration module from experiments/ (kept outside the
    core package; used only by the `benchmark` command group)."""
    import importlib
    exp_dir = str(repo_root() / "experiments")
    if exp_dir not in sys.path:
        sys.path.insert(0, exp_dir)
    return importlib.import_module(module_name)
from arglas import __version__


def sanitize_decimal(value) -> str:
    return str(value).replace(".", "_")


def load_batch_config(path: str) -> dict:
    config_path = resolve_repo_path(path, "batch_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


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

    generate_aafs_parser = subparsers.add_parser(
        "generate-aafs",
        help="Generate random AAF instances.",
        add_help=False,
    )
    generate_aafs_parser.add_argument("args", nargs=argparse.REMAINDER)
    generate_aafs_parser.set_defaults(handler=lambda ns: run_wrapped(generate_aafs.main, ns.args, "arglas generate-aafs"))

    label_parser = subparsers.add_parser(
        "label",
        help="Label generated AAFs under a selected semantics.",
        add_help=False,
    )
    label_parser.add_argument("args", nargs=argparse.REMAINDER)
    label_parser.set_defaults(handler=lambda ns: run_wrapped(generate_extensions.main, ns.args, "arglas label"))

    task_parser = subparsers.add_parser(
        "build-task",
        help="Build an ILASP learning task from labelled examples.",
        add_help=False,
    )
    task_parser.add_argument("args", nargs=argparse.REMAINDER)
    task_parser.set_defaults(handler=lambda ns: run_wrapped(generate_ilasp_task.main, ns.args, "arglas build-task"))

    learn_parser = subparsers.add_parser(
        "learn",
        help="Run the synthetic ILASP train/test pipeline.",
        add_help=False,
    )
    learn_parser.add_argument("args", nargs=argparse.REMAINDER)
    learn_parser.set_defaults(handler=lambda ns: run_wrapped(train_test.main, ns.args, "arglas learn"))

    demo_parser = subparsers.add_parser(
        "demo",
        help="End-to-end mini pipeline: generate AAFs, label, build task, learn (about a minute).",
        add_help=False,
    )
    demo_parser.add_argument("args", nargs=argparse.REMAINDER)
    demo_parser.set_defaults(handler=lambda ns: run_wrapped(demo_module.main, ns.args, "arglas demo"))

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run, watch, or replay benchmark grids.",
    )
    benchmark_subparsers = benchmark_parser.add_subparsers(dest="benchmark_command")
    benchmark_subparsers.required = True

    benchmark_run_parser = benchmark_subparsers.add_parser(
        "run",
        help="Run a benchmark grid from a JSON config.",
        add_help=False,
    )
    benchmark_run_parser.add_argument("args", nargs=argparse.REMAINDER)
    benchmark_run_parser.set_defaults(handler=lambda ns: run_wrapped(_experiments("run_experiment_grid").main, ns.args, "arglas benchmark run"))

    benchmark_watch_parser = benchmark_subparsers.add_parser(
        "watch",
        help="Watch and restart a benchmark grid from a JSON config.",
        add_help=False,
    )
    benchmark_watch_parser.add_argument("args", nargs=argparse.REMAINDER)
    benchmark_watch_parser.set_defaults(handler=lambda ns: run_wrapped(_experiments("watch_experiment_grid").main, ns.args, "arglas benchmark watch"))

    benchmark_replay_parser = benchmark_subparsers.add_parser(
        "replay",
        help="Replay archived learned models through the current evaluator.",
        add_help=False,
    )
    benchmark_replay_parser.add_argument("args", nargs=argparse.REMAINDER)
    benchmark_replay_parser.set_defaults(handler=lambda ns: run_wrapped(_experiments("replay_archived_evaluation").main, ns.args, "arglas benchmark replay"))

    benchmark_progress_parser = benchmark_subparsers.add_parser(
        "progress",
        help="Show a progress bar for a benchmark grid (add --watch N for a live bar).",
        add_help=False,
    )
    benchmark_progress_parser.add_argument("args", nargs=argparse.REMAINDER)
    benchmark_progress_parser.set_defaults(handler=lambda ns: run_wrapped(_experiments("campaign_progress").main, ns.args, "arglas benchmark progress"))

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
        direct_commands = {
            "generate-aafs": generate_aafs.main,
            "label": generate_extensions.main,
            "build-task": generate_ilasp_task.main,
            "learn": train_test.main,
        }
        if argv[0] in direct_commands:
            return run_wrapped(direct_commands[argv[0]], argv[1:], f"arglas {argv[0]}")
        if argv[0] == "demo":
            return run_wrapped(demo_module.main, argv[1:], "arglas demo")
        if len(argv) >= 2 and argv[0] == "benchmark":
            benchmark_modules = {
                "run": "run_experiment_grid",
                "watch": "watch_experiment_grid",
                "replay": "replay_archived_evaluation",
                "progress": "campaign_progress",
            }
            if argv[1] in benchmark_modules:
                return run_wrapped(_experiments(benchmark_modules[argv[1]]).main, argv[2:],
                                   f"arglas benchmark {argv[1]}")

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args) or 0)
