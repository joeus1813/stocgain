"""Generator configuration from the normative presets in docs/06."""

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from stocgain.settings import REPOSITORY_ROOT, Settings


@dataclass(frozen=True)
class GeneratorConfig:
    """Resolved preset and simulation parameters, with inclusive history dates."""

    preset: str
    history_start: date
    history_end: date
    burn_in_days: int
    raw: dict[str, Any]
    selection: dict[str, Any]


def load_config(preset: str, path: Path | None = None) -> GeneratorConfig:
    """Read generator parameters independently of the shell working directory."""
    path = path or Settings().generator_config_path
    if not path.is_absolute():
        path = REPOSITORY_ROOT / path
    with path.open("rb") as f:
        raw = tomllib.load(f)
    selection = raw["presets"][preset]
    return GeneratorConfig(
        preset,
        date.fromisoformat(selection["history_start"]),
        date.fromisoformat(selection["history_end"]),
        raw["burn_in_days"],
        raw,
        selection,
    )
