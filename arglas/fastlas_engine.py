"""Optional FastLAS learning engine (demo-level toggle).

Builds a FastLAS task from the same labelled examples the ILASP pipeline uses,
via the verifier formulation ported from Real_World_Examples/fastlas_exp
(fl_build.py / fl_discover.py — nothing is imported from there): each labelled
AAF becomes a context in which the labelling is GIVEN as facts, structural
features are derived deterministically (config/bg_fastlas.lp — NO choice
rules, FastLAS learns normal rules only), and the learner searches for a
constraint theory `violated :- body` (config/mode_declarations_fastlas.las)
that excludes oracle positives and covers oracle negatives.

Scope: wired into `arglas demo --engine fastlas` only. The full train/test
harness (arglas learn) evaluates learned choice-rule programs and would need a
generate-and-constrain prediction stage for verifier theories, so it stays
ILASP-only. Engine selection and extra binary flags are config-driven via
config/ilasp_config.json ("engine", "fastlas_args"), per CLAUDE.md rule 2.
"""
import os
import random
import shutil

from arglas.artifact_paths import ensure_parent_dir, resolve_artifact_path, resolve_repo_path
from arglas.ilasp_policy import load_ilasp_config

ENGINE_ILASP = "ILASP"
ENGINE_FASTLAS = "FastLAS"
ENGINES = (ENGINE_ILASP, ENGINE_FASTLAS)

DEFAULT_FASTLAS_MODE_ARG = "--opl"  # the verifier task is observational -> OPL-fast
DEFAULT_BACKGROUND = "bg_fastlas.lp"
DEFAULT_MODE_DECLARATIONS = "mode_declarations_fastlas.las"
DEFAULT_PENALTY = 100  # soft examples, mirroring the ILASP pipeline's noise_factor default


def require_fastlas():
    """Fail fast with an actionable message when the FastLAS binary is missing."""
    if shutil.which("FastLAS") is None:
        raise SystemExit(
            "FastLAS not found on PATH — install FastLAS 2.x "
            "(https://github.com/spike-imperial/FastLAS) or use the default "
            "ILASP engine (drop --engine fastlas)."
        )


def resolve_engine(cli_engine=None, ilasp_config=None):
    """Engine selection: CLI value wins, else config/ilasp_config.json
    global.engine, else ILASP. Returns 'ILASP' or 'FastLAS'."""
    if ilasp_config is None:
        ilasp_config = load_ilasp_config()
    name = cli_engine or ilasp_config.get("global", {}).get("engine", ENGINE_ILASP)
    canonical = {e.lower(): e for e in ENGINES}.get(str(name).lower())
    if canonical is None:
        raise ValueError(f"Unknown engine '{name}': expected one of {ENGINES}.")
    return canonical


def resolve_fastlas_args(semantics=None, ilasp_config=None):
    """Extra FastLAS flags from config/ilasp_config.json: global.fastlas_args
    plus <semantics>.fastlas_args (both optional list[str])."""
    if ilasp_config is None:
        ilasp_config = load_ilasp_config()
    args = []
    for label in ("global", semantics):
        block = ilasp_config.get(label, {}) if label else {}
        extra = block.get("fastlas_args", [])
        if not isinstance(extra, list) or any(not isinstance(x, str) for x in extra):
            raise ValueError(f"Invalid {label}.fastlas_args: expected list[str].")
        args.extend(extra)
    return args


def build_fastlas_command(task_file, semantics=None, extra_args=None):
    """Full FastLAS invocation for a task file (also checks the binary is on
    PATH). Defaults to --opl unless the resolved args already pin a mode."""
    require_fastlas()
    if extra_args is None:
        extra_args = resolve_fastlas_args(semantics=semantics)
    extra_args = list(extra_args)
    if not any(a in ("--opl", "--nopl") for a in extra_args):
        extra_args.insert(0, DEFAULT_FASTLAS_MODE_ARG)
    return ["FastLAS"] + extra_args + [task_file]


def render_verifier_example(example_id, af_facts, labels, is_positive, penalty=DEFAULT_PENALTY):
    """One CDPI-shaped FastLAS example. The labelling goes INTO the context
    (in/out facts; undec args get neither, bg_fastlas.lp derives undec);
    positives exclude `violated`, negatives include it. penalty=None -> hard."""
    ctx = list(af_facts)
    ctx += [f"{status}({arg})." for arg, status in sorted(labels.items())
            if status in ("in", "out")]
    incl, excl = (("", "violated") if is_positive else ("violated", ""))
    idw = f"{example_id}@{penalty}" if penalty else example_id
    return f"#pos({idw}, {{{incl}}}, {{{excl}}}, {{{' '.join(ctx)}}})."


def parse_learned_rules(stdout):
    """Learned `violated` rules from FastLAS stdout (empty list: nothing
    learned or UNSATISFIABLE)."""
    if "UNSATISFIABLE" in stdout:
        return []
    return [ln.strip() for ln in stdout.splitlines()
            if ln.strip().endswith(".") and not ln.strip().startswith("%")
            and (":-" in ln or ln.strip().startswith("violated"))]


def build_fastlas_task(
    input_dir,
    output_file,
    n_pos,
    n_neg=None,
    seed=None,
    penalty=DEFAULT_PENALTY,
    background=DEFAULT_BACKGROUND,
    mode_declarations=DEFAULT_MODE_DECLARATIONS,
    allow_overwrite=False,
):
    """Build a FastLAS verifier task from a labelled-examples directory (the
    same *_POS_*.lp / *_NEG_*.lp files the ILASP task builder samples).
    Negatives are the oracle NEG files taken as-is: under the demo's
    complete-information labelling (p_partial=1.0) they are guaranteed
    non-extensions, so the ILASP builder's oracle re-validation pass is not
    needed here. Returns the output path."""
    from arglas.generate_ilasp_task import parse_lp_instance  # shared .lp parser

    rng = random.Random(seed)
    input_dir = resolve_artifact_path(input_dir)
    output_file = ensure_parent_dir(resolve_artifact_path(output_file))
    if n_neg is None:
        n_neg = n_pos

    if os.path.exists(output_file) and not allow_overwrite:
        raise SystemExit(
            f"Error: Output file already exists: {output_file}. "
            "Pick a new output path or pass allow_overwrite."
        )

    pools = {}
    for tag, wanted in (("_POS_", n_pos), ("_NEG_", n_neg)):
        files = sorted(f for f in os.listdir(input_dir) if tag in f and f.endswith(".lp"))
        if len(files) < wanted:
            raise SystemExit(
                f"Error: Not enough {tag.strip('_')} examples in {input_dir}: "
                f"found {len(files)}, need {wanted}."
            )
        pools[tag] = rng.sample(files, wanted)

    lines = []
    for tag, is_positive in (("_POS_", True), ("_NEG_", False)):
        for fname in pools[tag]:
            af_facts, labels = parse_lp_instance(os.path.join(input_dir, fname))
            lines.append(render_verifier_example(
                example_id=os.path.basename(fname).replace(".lp", ""),
                af_facts=af_facts,
                labels=labels,
                is_positive=is_positive,
                penalty=penalty,
            ))

    with open(resolve_repo_path(background), "r", encoding="utf-8") as f:
        bg_text = f.read()
    with open(resolve_repo_path(mode_declarations), "r", encoding="utf-8") as f:
        modes_text = f.read()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n" + bg_text + "\n" + modes_text)
    return output_file
