import json
import os


RESERVED_TOP_LEVEL_KEYS = {"global"}
DEFAULT_BACKGROUND_FILE = "background_knowledge.lp"
DEFAULT_SHOW_PREDICATES = {
    "label_generation": ["in/1", "out/1"],
    "train_test_learned": ["in/1", "out/1"],
    "train_test_ground_truth": ["in/1", "out/1"],
}


def dedupe_keep_order(values):
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def load_semantics_config(path="semantics_config.json"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing semantics config: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_semantics_names(config):
    names = []
    for key, value in config.items():
        if key in RESERVED_TOP_LEVEL_KEYS:
            continue
        if isinstance(value, dict) and "file" in value:
            names.append(key)
    return sorted(names)


def get_semantics_entry(config, semantics):
    if semantics not in config or semantics in RESERVED_TOP_LEVEL_KEYS:
        available = ", ".join(get_semantics_names(config))
        raise KeyError(f"Unknown semantics '{semantics}'. Available: {available}")
    entry = config[semantics]
    if not isinstance(entry, dict) or "file" not in entry:
        raise ValueError(f"Invalid semantics entry for '{semantics}' in semantics config.")
    return entry


def _read_stage_args(container, stage):
    if not isinstance(container, dict):
        return []
    value = container.get(stage, [])
    if not isinstance(value, list):
        raise ValueError(f"Invalid stage args for stage '{stage}': expected list.")
    return value


def get_clingo_args(config, semantics, stage):
    sem_entry = get_semantics_entry(config, semantics)
    global_cfg = config.get("global", {})

    args = []
    args.extend(global_cfg.get("clingo_args", []))
    args.extend(_read_stage_args(global_cfg.get("stage_clingo_args", {}), stage))
    args.extend(sem_entry.get("clingo_args", []))
    args.extend(_read_stage_args(sem_entry.get("stage_clingo_args", {}), stage))

    # Backward-compatible support for legacy paper_* flags.
    if sem_entry.get("paper_heuristic_mode", False):
        paper_args = sem_entry.get(
            "paper_clingo_args",
            ["--heuristic=Domain", "--enum=domRec"],
        )
        if not isinstance(paper_args, list):
            raise ValueError(
                f"Invalid paper_clingo_args for '{semantics}': expected list."
            )
        args.extend(paper_args)

    return dedupe_keep_order(args)


def get_background_file(config, stage=None):
    value = config.get("global", {}).get("background_file", DEFAULT_BACKGROUND_FILE)
    if isinstance(value, dict):
        if stage is None:
            stage_value = value.get("train_test_learned", DEFAULT_BACKGROUND_FILE)
        else:
            stage_value = value.get(stage, None)
        if stage_value is None or stage_value == "":
            return None
        if not isinstance(stage_value, str) or not stage_value.strip():
            raise ValueError(
                f"Invalid global.background_file['{stage}'] in semantics config."
            )
        return stage_value
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid global.background_file in semantics config.")
    return value


def get_completion_rules_enabled(config, stage, semantics=None):
    # A per-semantics completion_rules block (bool or {stage: bool}) overrides the
    # global setting for that semantics+stage. Needed because grounded.lp is a sparse
    # least-fixpoint oracle (undecided args unlabelled), so forcing the learned side
    # total via completion would mismatch it -- whereas the total ADM/STB/CMP oracles
    # require completion=true. Default (semantics=None) preserves the global behavior.
    if semantics is not None and semantics not in RESERVED_TOP_LEVEL_KEYS:
        sem_entry = config.get(semantics, {})
        if isinstance(sem_entry, dict) and "completion_rules" in sem_entry:
            sem_cfg = sem_entry["completion_rules"]
            if isinstance(sem_cfg, bool):
                return sem_cfg
            if isinstance(sem_cfg, dict) and stage in sem_cfg:
                value = sem_cfg.get(stage)
                if not isinstance(value, bool):
                    raise ValueError(
                        f"Invalid {semantics}.completion_rules['{stage}']: expected bool."
                    )
                return value

    cfg = config.get("global", {}).get("completion_rules", True)
    if isinstance(cfg, bool):
        return cfg
    if isinstance(cfg, dict):
        value = cfg.get(stage, True)
        if not isinstance(value, bool):
            raise ValueError(
                f"Invalid global.completion_rules['{stage}']: expected bool."
            )
        return value
    raise ValueError("Invalid global.completion_rules in semantics config.")


def get_eval_on_bare_aaf(config, semantics):
    # When true, the learned-vs-oracle comparison for this semantics is done on the
    # BARE AAF (args+atts only), stripping the test file's label atoms. This is the
    # correct evaluation for a UNIQUE-extension semantics whose oracle is a definite
    # program (e.g. grounded.lp, which has no integrity constraints and therefore can
    # never reject an injected non-valid labelling -- making the inject-labelling-as-
    # facts comparison meaningless on negative instances).
    sem_entry = get_semantics_entry(config, semantics)
    value = sem_entry.get("eval_on_bare_aaf", False)
    if not isinstance(value, bool):
        raise ValueError(f"Invalid eval_on_bare_aaf for '{semantics}': expected bool.")
    return value


def get_show_predicates(config, stage):
    defaults = DEFAULT_SHOW_PREDICATES.get(stage, ["in/1"])
    cfg = config.get("global", {}).get("show_predicates", {})
    if not isinstance(cfg, dict):
        return defaults
    value = cfg.get(stage, defaults)
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError(
            f"Invalid global.show_predicates['{stage}']: expected list[str]."
        )
    return value if value else defaults


def semantics_wants_ilasp_heuristics(config, semantics):
    sem_entry = get_semantics_entry(config, semantics)
    value = sem_entry.get("learn_heuristics", False)
    if not isinstance(value, bool):
        raise ValueError(f"Invalid learn_heuristics for '{semantics}': expected bool.")
    return value
