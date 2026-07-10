"""Route G2 (GRD via learned weak constraints) shared library.

Faithful mini-harness: imports train_test and reuses its evaluation and
split machinery; overrides ONLY the per-semantics conventions under test:
  * learned-side solving uses clingo --opt-mode=optN and keeps ONLY models
    with optimality_proven=True (deduplicated). If the learned program has
    no optimization statement (cost == []), all models are kept (this is
    the no-WC fallback, identical to solve_models behaviour).
  * GRD ground truth = ASPARTIX/grounded.lp on the BARE AAF (bare-AAF
    convention already in semantics_config for GRD), background=None,
    completion_rules=False, show in/1,out/1, plain clingo args.
"""
import os
import re
import sys
import clingo

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
WORK = os.path.join(REPO, "analysis", "grd_prf_lab", "g2_weak")
AAF_DIR = os.path.join(REPO, "artifacts", "final_synthetic_corrected_20260625", "aafs")
POOL_DIR = os.path.join(WORK, "pools", "labelled_GRD_full")
CORE_FILE = os.path.join(WORK, "core_complete.lp")
GROUNDED_LP = os.path.join(REPO, "ASPARTIX", "grounded.lp")
COMPLETE_LP = os.path.join(REPO, "ASPARTIX", "complete.lp")

sys.path.insert(0, REPO)
os.chdir(REPO)
from arglas import train_test as T  # noqa: E402

SHOW = ["in/1", "out/1"]


def solve_optimal_models(files_to_load, additional_program=None,
                         show_predicates=SHOW, extra_args=()):
    """All OPTIMAL answer sets, projected to show_predicates.

    Convention (documented for the schema): clingo args are
    ["-n","0","--warn=none","--opt-mode=optN"]; keep models whose
    optimality_proven flag is True (the optN re-enumeration pass) and
    deduplicate. If the program contains no optimization statement
    (model.cost == []), keep every model -- matching plain solve_models.
    """
    args = ["-n", "0", "--warn=none", "--opt-mode=optN"] + list(extra_args)
    ctl = clingo.Control(args)
    for path in files_to_load:
        if path:
            ctl.load(path)
    if additional_program:
        ctl.add("base", [], additional_program)
    for predicate in show_predicates:
        ctl.add("base", [], f"#show {predicate}.")
    ctl.ground([("base", [])])
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            if list(model.cost) and not model.optimality_proven:
                continue
            models.append(set(str(sym) for sym in model.symbols(shown=True)))
    # dedup while preserving determinism
    seen, out = set(), []
    for m in models:
        fm = frozenset(m)
        if fm not in seen:
            seen.add(fm)
            out.append(m)
    return out


def parse_instance(path):
    """Split a labelled instance into bare AAF facts and label atoms."""
    bare, labels = [], set()
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if s.startswith(("arg(", "att(")):
                bare.append(s)
            elif s.startswith(("in(", "out(")):
                labels.add(s.rstrip("."))
    return bare, labels


def grounded_gt_models(bare_program):
    """Ground-truth grounded labelling(s) on the bare AAF (pipeline GRD
    convention: grounded.lp, no background, no completion, plain clingo)."""
    ctl = clingo.Control(["-n", "0", "--warn=none"])
    ctl.load(GROUNDED_LP)
    ctl.add("base", [], bare_program)
    for predicate in SHOW:
        ctl.add("base", [], f"#show {predicate}.")
    ctl.ground([("base", [])])
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(set(str(sym) for sym in model.symbols(shown=True)))
    return models


def complete_labellings(bare_program):
    """All complete labellings (3-valued convention) via the fixed core."""
    ctl = clingo.Control(["-n", "0", "--warn=none"])
    ctl.load(CORE_FILE)
    ctl.add("base", [], bare_program)
    for predicate in SHOW:
        ctl.add("base", [], f"#show {predicate}.")
    ctl.ground([("base", [])])
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(set(str(sym) for sym in model.symbols(shown=True)))
    return models


def aspartix_complete_insets(bare_program):
    ctl = clingo.Control(["-n", "0", "--warn=none"])
    ctl.load(COMPLETE_LP)
    ctl.add("base", [], bare_program)
    ctl.add("base", [], "#show in/1.")
    ctl.ground([("base", [])])
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(frozenset(str(sym) for sym in model.symbols(shown=True)))
    return set(models)


def read_bare_aaf(aaf_path):
    with open(aaf_path, "r", encoding="utf-8") as f:
        return "\n".join(
            ln.strip() for ln in f if ln.strip().startswith(("arg(", "att("))
        )


def all_aafs():
    out = []
    for f in sorted(os.listdir(AAF_DIR)):
        m = re.match(r"aaf_(\d+)_(\d+)\.lp$", f)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), os.path.join(AAF_DIR, f)))
    return out


def args_of(bare_program):
    return re.findall(r"arg\(([a-z0-9_]+)\)", bare_program)


def extract_learned_wcs(ilasp_output):
    """train_test.extract_hypothesis_rules DROPS weak constraints (they end
    with ']' not '.'), so extract them here. Accept both ':~ body.[w@p,t]'
    lines and normal rules after 'Final Hypothesis' if present."""
    lines = ilasp_output.splitlines()
    start = 0
    for i, ln in enumerate(lines):
        if "Final Hypothesis" in ln:
            start = i + 1
    rules = []
    for ln in lines[start:]:
        s = ln.strip()
        if not s or s.startswith("%"):
            continue
        if s.startswith(":~") and s.endswith("]"):
            rules.append(s)
        elif T.is_probable_asp_rule(s):
            rules.append(s)
    return rules
