from __future__ import annotations

from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "defaults.toml"


def load_config(path: str | Path | None = None) -> dict:
    """Load a TOML config file as a plain dictionary."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        return tomllib.load(handle)
