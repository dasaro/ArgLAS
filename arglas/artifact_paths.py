import os
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _REPO_ROOT / "config"
_ENV_KEY = "FABIO_ARTIFACTS_ROOT"


def repo_root():
    return _REPO_ROOT


def config_dir():
    return _CONFIG_DIR


def artifacts_root():
    raw = os.environ.get(_ENV_KEY, "").strip()
    if not raw:
        return _REPO_ROOT
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = _REPO_ROOT / candidate
    return candidate.resolve()


def resolve_repo_path(raw_path, *default_parts):
    """Resolve a config/encoding path. Relative names are looked up at the repo
    root first and then under config/ (where the .lp/.las/.json assets live), so
    both "config/background_knowledge.lp" and the short "background_knowledge.lp"
    work."""
    if raw_path in (None, ""):
        if not default_parts:
            raise ValueError("default_parts required when raw_path is empty")
        rel = Path(*default_parts)
    else:
        rel = Path(raw_path).expanduser()
    if rel.is_absolute():
        return str(rel.resolve())
    candidate = _REPO_ROOT / rel
    if not candidate.exists():
        in_config = _CONFIG_DIR / rel
        if in_config.exists():
            candidate = in_config
    return str(candidate.resolve())


def resolve_artifact_path(raw_path, *default_parts):
    root = artifacts_root()
    if raw_path in (None, ""):
        if not default_parts:
            raise ValueError("default_parts required when raw_path is empty")
        candidate = root.joinpath(*default_parts)
    else:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
    return str(candidate.resolve())


def ensure_parent_dir(path):
    resolved = Path(path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved)


def ensure_dir(path):
    resolved = Path(path).expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return str(resolved)
