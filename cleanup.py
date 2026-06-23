import shutil
import os
import json

CONFIG_PATH = "batch_config.json"

def load_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        return json.load(f)

def remove_dir(path):
    if os.path.exists(path):
        print(f"🧹 Removing: {path}")
        shutil.rmtree(path)
    else:
        print(f"✓ Skipping (not found): {path}")

def cleanup_from_config(cfg):

    # Remove all per-prefix outputs
    for sem in cfg["semantics"]:
        for p in cfg["partials"]:
            pstr = "full" if p == 1.0 else f"partial_{p}"
            prefix = f"{sem}_{pstr}"

            remove_dir(os.path.join(cfg["base_output_dir"], f"labelled_{prefix}"))
            remove_dir(os.path.join(cfg["train_dir"], prefix))
            remove_dir(os.path.join(cfg["train_output_dir"], prefix))
            remove_dir(os.path.join(cfg["results_dir"], prefix))

    # Global batch summary
    if os.path.exists("batch_summary.csv"):
        os.remove("batch_summary.csv")
        print("🧹 Removed batch_summary.csv")

    print("\n✅ Cleanup complete.")
    return 0


def main(config_path=CONFIG_PATH):
    cfg = load_config(config_path)
    return cleanup_from_config(cfg)

if __name__ == "__main__":
    raise SystemExit(main())
