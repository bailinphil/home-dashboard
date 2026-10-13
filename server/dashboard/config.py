from pathlib import Path

import yaml

_SERVER_DIR = Path(__file__).resolve().parent.parent


def load_config(path: Path | str | None = None) -> dict:
    """Load config.local.yaml (falling back to config.example.yaml)."""
    if path is None:
        local = _SERVER_DIR / "config.local.yaml"
        path = local if local.exists() else _SERVER_DIR / "config.example.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
