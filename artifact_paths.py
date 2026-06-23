import os
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent
_ENV_KEY = "FABIO_ARTIFACTS_ROOT"


def repo_root():
    return _REPO_ROOT


def artifacts_root():
    raw = os.environ.get(_ENV_KEY, "").strip()
    if not raw:
        return _REPO_ROOT
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = _REPO_ROOT / candidate
    return candidate.resolve()


def resolve_repo_path(raw_path, *default_parts):
    if raw_path in (None, ""):
        if not default_parts:
            raise ValueError("default_parts required when raw_path is empty")
        candidate = _REPO_ROOT.joinpath(*default_parts)
    else:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = _REPO_ROOT / candidate
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
