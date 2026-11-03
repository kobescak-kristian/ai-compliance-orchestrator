"""Reader for the gitignored per-machine file config.local.yaml (the
gate's designated mechanism for machine-specific values;
evals/eval_config.yaml datasets.holdout.location). Keys used:
holdout_root (the private folder that holds the holdouts and their run
output) and verifier_repo_path (a dedicated pinned verifier clone).
Paths here never enter a tracked file.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG_PATH = REPO_ROOT / "config.local.yaml"
KNOWN_KEYS = {"holdout_root", "verifier_repo_path"}


def load_local_config(path: Path = LOCAL_CONFIG_PATH) -> dict:
    """The local settings, or {} when the file does not exist. Unknown
    keys are an error, so a typo cannot silently fall back to a default."""
    path = Path(path)
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a mapping")
    unknown = set(data) - KNOWN_KEYS
    if unknown:
        raise ValueError(f"{path.name}: unknown keys {sorted(unknown)}")
    return data
