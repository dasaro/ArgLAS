"""arglas demo — learn an argumentation semantics end-to-end in about a minute.

Generates a small pool of random AAFs, labels it with the chosen reference
semantics (ASPARTIX oracle), builds an ILASP task, runs ILASP, and prints the
learned program. Everything happens under --workdir (default: a fresh
demo_run/ inside the artifacts root), leaving the repo untouched.
"""
import argparse
import os
import subprocess
import time

from arglas import generate_aafs, generate_extensions, generate_ilasp_task
from arglas.artifact_paths import resolve_artifact_path
from arglas.fastlas_engine import (
    ENGINE_FASTLAS,
    build_fastlas_command,
    build_fastlas_task,
    parse_learned_rules,
    require_fastlas,
    resolve_engine,
)
from arglas.ilasp_policy import build_ilasp_command, require_ilasp
from arglas.solver_policy import available_semantics_names

# GRD is out of the demo's scope (dense random pools starve its learning
# signal) and BAF_* semantics need bipolar (support/2) pools the demo
# generator does not produce.
DEMO_EXCLUDED_SEMANTICS = ("GRD",)


def demo_semantics_choices():
    names = [
        s for s in available_semantics_names()
        if s not in DEMO_EXCLUDED_SEMANTICS and not s.startswith("BAF_")
    ]
    return names or ["ADM", "CMP", "PRF", "STB"]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arglas demo",
                                     description="End-to-end mini pipeline: generate, label, build task, learn.")
    parser.add_argument("--semantics", default="STB", choices=demo_semantics_choices(),
                        help="Target semantics to learn (default: STB).")
    parser.add_argument("--n_aafs", type=int, default=30, help="AAFs per size (sizes 4..6).")
    parser.add_argument("--examples", type=int, default=20, help="Examples per class in the ILASP task.")
    parser.add_argument("--seed", type=int, default=20260710, help="Generation seed.")
    parser.add_argument("--workdir", default=None, help="Working directory (default: <artifacts>/demo_run).")
    parser.add_argument("--engine", choices=("ilasp", "fastlas"), default=None,
                        help="Learning engine (default: 'engine' in config/ilasp_config.json, i.e. ILASP).")
    args = parser.parse_args(argv)
    engine = resolve_engine(args.engine)
    use_fastlas = engine == ENGINE_FASTLAS
    require_fastlas() if use_fastlas else require_ilasp()

    work = args.workdir or resolve_artifact_path("demo_run")
    aafs = os.path.join(work, "aafs")
    labelled = os.path.join(work, "labelled")
    task = os.path.join(work, f"task_{args.semantics}{'_fastlas' if use_fastlas else ''}.las")
    os.makedirs(aafs, exist_ok=True)

    print(f"[1/4] generating {3 * args.n_aafs} random AAFs (sizes 4-6) -> {aafs}")
    generate_aafs.main(["4", "6", str(args.n_aafs), "--output_dir", aafs,
                        "--seed", str(args.seed), "--quiet"])

    print(f"[2/4] labelling with the {args.semantics} reference semantics -> {labelled}")
    generate_extensions.main(["--input_dir", aafs, "--base_output_dir", labelled,
                              "--semantics", args.semantics, "--p_partial", "1.0",
                              "--allow_empty"])

    labelled_dir = os.path.join(labelled, f"labelled_{args.semantics}_full")
    print(f"[3/4] building the {engine} task ({args.examples} pos / {args.examples} neg) -> {task}")
    if use_fastlas:
        build_fastlas_task(labelled_dir, task, n_pos=args.examples,
                           n_neg=args.examples, seed=args.seed, allow_overwrite=True)
        cmd = build_fastlas_command(task, semantics=args.semantics)
    else:
        generate_ilasp_task.main([labelled_dir, task, str(args.examples), "0.0",
                                  "--n_neg", str(args.examples),
                                  "--semantics", args.semantics])
        cmd = build_ilasp_command(task, semantics=args.semantics)

    print(f"[4/4] learning: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if use_fastlas:
        # FastLAS learns a verifier theory: `violated :- ...` constraints that
        # legal labellings must avoid (see arglas/fastlas_engine.py).
        hypothesis = parse_learned_rules(proc.stdout)
    else:
        hypothesis = [ln for ln in proc.stdout.splitlines()
                      if ln.strip() and not ln.startswith("%") and "Pre-processing" not in ln
                      and "solve time" not in ln.lower()]
    print(f"\nlearned {args.semantics} program ({dt:.1f}s):\n" + "-" * 40)
    print("\n".join(hypothesis) or proc.stdout[-500:])
    print("-" * 40)
    print(f"artifacts in {work}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
