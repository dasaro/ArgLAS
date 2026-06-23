import json
import os
import sys
from solver_policy import get_semantics_names

CONFIG_PATH = "batch_config.json"
SEMANTICS_CONFIG_PATH = "semantics_config.json"
ILASP_CONFIG_PATH = "ilasp_config.json"

def load_semantics_config(path=SEMANTICS_CONFIG_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing semantics config: {path}")
    with open(path, "r") as f:
        return json.load(f)


def load_batch_config(path=CONFIG_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing batch config: {path}")
    with open(path, "r") as f:
        return json.load(f)


def load_ilasp_config(path=ILASP_CONFIG_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing ILASP config: {path}")
    with open(path, "r") as f:
        return json.load(f)


def validate_ilasp_config(ilasp_cfg, semantics_cfg):
    if not isinstance(ilasp_cfg, dict):
        raise ValueError("Invalid ILASP config: expected dict")

    global_cfg = ilasp_cfg.get("global", {})
    if global_cfg:
        if not isinstance(global_cfg, dict):
            raise ValueError("Invalid ILASP global config: expected dict")
        if "ilasp_args" in global_cfg:
            if not isinstance(global_cfg["ilasp_args"], list) or not all(isinstance(x, str) for x in global_cfg["ilasp_args"]):
                raise ValueError("Invalid global.ilasp_args in ILASP config: expected list[str]")

    valid_semantics = set(get_semantics_names(semantics_cfg))
    for sem, sem_entry in ilasp_cfg.items():
        if sem == "global":
            continue
        if sem not in valid_semantics:
            raise ValueError(f"ILASP config contains unknown semantics key '{sem}'")
        if not isinstance(sem_entry, dict):
            raise ValueError(f"Invalid ILASP config block for '{sem}': expected dict")
        ilasp_args = sem_entry.get("ilasp_args", [])
        if not isinstance(ilasp_args, list) or not all(isinstance(x, str) for x in ilasp_args):
            raise ValueError(f"Invalid ILASP config for '{sem}': ilasp_args must be list[str]")
        if "--learn-heuristics" in ilasp_args:
            raise ValueError(
                f"Semantic '{sem}' sets --learn-heuristics in {ILASP_CONFIG_PATH}. "
                "Use semantics_config.json learn_heuristics as the single source of truth."
            )

def validate_config(cfg, semantics_cfg):
    required_keys = [
        "semantics", "partials", "noise_values", "iterations",
        "f_values", "input_dir", "base_output_dir",
        "train_dir", "train_output_dir", "results_dir", "asp_dir"
    ]

    # Check required keys
    for key in required_keys:
        if key not in cfg:
            raise ValueError(f"Missing required key in config: '{key}'")

    # Check numeric list types
    for key in ["partials", "noise_values", "f_values"]:
        if not isinstance(cfg[key], list) or not all(isinstance(x, (int, float)) for x in cfg[key]):
            raise ValueError(f"Invalid format for '{key}' — must be list of numbers")

    if "f_neg_values" in cfg:
        if not isinstance(cfg["f_neg_values"], list) or not all(isinstance(x, (int, float)) for x in cfg["f_neg_values"]):
            raise ValueError("Invalid format for 'f_neg_values' — must be list of numbers")
        if len(cfg["f_neg_values"]) != len(cfg["f_values"]):
            raise ValueError("'f_neg_values' must have the same length as 'f_values'")

    if not isinstance(cfg["iterations"], int) or cfg["iterations"] < 1:
        raise ValueError("Invalid value for 'iterations' — must be positive integer")

    # Check directory existence
    for d in [cfg["input_dir"], cfg["asp_dir"]]:
        if not os.path.isdir(d):
            raise FileNotFoundError(f"Directory does not exist: {d}")

    # Check semantics names and mapped ASP files
    valid_semantics = set(get_semantics_names(semantics_cfg))
    for sem in cfg["semantics"]:
        if sem not in valid_semantics:
            raise ValueError(f"Semantic '{sem}' missing from {SEMANTICS_CONFIG_PATH}")

        sem_entry = semantics_cfg[sem]
        asp_file = sem_entry.get("file")
        if not asp_file:
            raise ValueError(f"Semantic '{sem}' has no 'file' entry in {SEMANTICS_CONFIG_PATH}")

        if not os.path.isfile(asp_file):
            raise FileNotFoundError(f"Missing ASP file for semantic '{sem}': {asp_file}")

        if "clingo_args" in sem_entry and not isinstance(sem_entry["clingo_args"], list):
            raise ValueError(
                f"Semantic '{sem}' has invalid 'clingo_args': expected list"
            )
        if "stage_clingo_args" in sem_entry:
            if not isinstance(sem_entry["stage_clingo_args"], dict):
                raise ValueError(
                    f"Semantic '{sem}' has invalid 'stage_clingo_args': expected dict"
                )
            for stage_name, stage_args in sem_entry["stage_clingo_args"].items():
                if not isinstance(stage_args, list):
                    raise ValueError(
                        f"Semantic '{sem}' stage '{stage_name}' has invalid clingo args: expected list"
                    )
        if "learn_heuristics" in sem_entry and not isinstance(sem_entry["learn_heuristics"], bool):
            raise ValueError(
                f"Semantic '{sem}' has invalid 'learn_heuristics': expected bool"
            )

    global_cfg = semantics_cfg.get("global", {})
    if global_cfg:
        if not isinstance(global_cfg, dict):
            raise ValueError("Invalid 'global' block in semantics config: expected dict")
        if "background_file" in global_cfg:
            background_file = global_cfg["background_file"]
            if not isinstance(background_file, (str, dict)) and background_file is not None:
                raise ValueError("Invalid global.background_file: expected string, dict, or null")
            if isinstance(background_file, dict):
                for stage_name, bg_path in background_file.items():
                    if bg_path is not None and not isinstance(bg_path, str):
                        raise ValueError(
                            f"Invalid global.background_file['{stage_name}']: expected string or null"
                        )
        if "clingo_args" in global_cfg and not isinstance(global_cfg["clingo_args"], list):
            raise ValueError("Invalid global.clingo_args: expected list")
        if "stage_clingo_args" in global_cfg:
            if not isinstance(global_cfg["stage_clingo_args"], dict):
                raise ValueError("Invalid global.stage_clingo_args: expected dict")
            for stage_name, stage_args in global_cfg["stage_clingo_args"].items():
                if not isinstance(stage_args, list):
                    raise ValueError(
                        f"Invalid global.stage_clingo_args['{stage_name}']: expected list"
                    )
        if "completion_rules" in global_cfg:
            completion_rules = global_cfg["completion_rules"]
            if not isinstance(completion_rules, (bool, dict)):
                raise ValueError("Invalid global.completion_rules: expected bool or dict")
            if isinstance(completion_rules, dict):
                for stage_name, enabled in completion_rules.items():
                    if not isinstance(enabled, bool):
                        raise ValueError(
                            f"Invalid global.completion_rules['{stage_name}']: expected bool"
                        )
        if "show_predicates" in global_cfg:
            show_predicates = global_cfg["show_predicates"]
            if not isinstance(show_predicates, dict):
                raise ValueError("Invalid global.show_predicates: expected dict")
            for stage_name, preds in show_predicates.items():
                if not isinstance(preds, list):
                    raise ValueError(
                        f"Invalid global.show_predicates['{stage_name}']: expected list"
                    )

    print("✅ Configuration is valid.")
    return 0


def main(config_path=CONFIG_PATH, semantics_config_path=SEMANTICS_CONFIG_PATH, ilasp_config_path=ILASP_CONFIG_PATH):
    try:
        config = load_batch_config(config_path)
        semantics_config = load_semantics_config(semantics_config_path)
        ilasp_config = load_ilasp_config(ilasp_config_path)
        validate_config(config, semantics_config)
        validate_ilasp_config(ilasp_config, semantics_config)
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
