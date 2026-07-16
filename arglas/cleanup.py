import os
import shutil

from arglas.artifact_paths import resolve_artifact_path
from arglas.validate_config import load_batch_config

CONFIG_PATH = "batch_config.json"


def remove_dir(path):
    if os.path.exists(path):
        print(f"🧹 Removing: {path}")
        shutil.rmtree(path)
    else:
        print(f"✓ Skipping (not found): {path}")


def cleanup_from_config(cfg):
    # Every directory is resolved against the artifacts root, so with
    # FABIO_ARTIFACTS_ROOT set the cleanup targets the campaign's outputs and
    # never CWD-relative directories.
    base_output_dir = resolve_artifact_path(cfg["base_output_dir"], "labelled")
    train_dir = resolve_artifact_path(cfg["train_dir"], "train")
    train_output_dir = resolve_artifact_path(cfg["train_output_dir"], "train_output")
    results_dir = resolve_artifact_path(cfg["results_dir"], "results")

    for sem in cfg["semantics"]:
        for p in cfg["partials"]:
            pstr = "full" if p == 1.0 else f"partial_{p}"
            prefix = f"{sem}_{pstr}"

            remove_dir(os.path.join(base_output_dir, f"labelled_{prefix}"))
            remove_dir(os.path.join(train_dir, prefix))
            remove_dir(os.path.join(train_output_dir, prefix))
            remove_dir(os.path.join(results_dir, prefix))

    print("\n✅ Cleanup complete.")
    return 0


def main(config_path=CONFIG_PATH):
    return cleanup_from_config(load_batch_config(config_path))


if __name__ == "__main__":
    raise SystemExit(main())
