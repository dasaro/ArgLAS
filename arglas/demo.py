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
from arglas.ilasp_policy import resolve_ilasp_args


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arglas demo",
                                     description="End-to-end mini pipeline: generate, label, build task, learn.")
    parser.add_argument("--semantics", default="STB", choices=["STB", "ADM", "CMP", "PRF"],
                        help="Target semantics to learn (default: STB).")
    parser.add_argument("--n_aafs", type=int, default=30, help="AAFs per size (sizes 4..6).")
    parser.add_argument("--examples", type=int, default=20, help="Examples per class in the ILASP task.")
    parser.add_argument("--seed", type=int, default=20260710, help="Generation seed.")
    parser.add_argument("--workdir", default=None, help="Working directory (default: <artifacts>/demo_run).")
    args = parser.parse_args(argv)

    work = args.workdir or resolve_artifact_path("demo_run")
    aafs = os.path.join(work, "aafs")
    labelled = os.path.join(work, "labelled")
    task = os.path.join(work, f"task_{args.semantics}.las")
    os.makedirs(aafs, exist_ok=True)

    print(f"[1/4] generating {3 * args.n_aafs} random AAFs (sizes 4-6) -> {aafs}")
    generate_aafs.main(["4", "6", str(args.n_aafs), "--output_dir", aafs,
                        "--seed", str(args.seed), "--quiet"])

    print(f"[2/4] labelling with the {args.semantics} reference semantics -> {labelled}")
    generate_extensions.main(["--input_dir", aafs, "--base_output_dir", labelled,
                              "--semantics", args.semantics, "--p_partial", "1.0",
                              "--allow_empty"])

    print(f"[3/4] building the ILASP task ({args.examples} pos / {args.examples} neg) -> {task}")
    generate_ilasp_task.main([os.path.join(labelled, f"labelled_{args.semantics}_full"),
                              task, str(args.examples), "0.0",
                              "--n_neg", str(args.examples),
                              "--semantics", args.semantics])

    ilasp_args = resolve_ilasp_args(semantics=args.semantics)
    cmd = ["ILASP"] + ([] if any(a.startswith("--version") for a in ilasp_args) else ["--version=4"]) \
        + ilasp_args + [task]
    print(f"[4/4] learning: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
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
