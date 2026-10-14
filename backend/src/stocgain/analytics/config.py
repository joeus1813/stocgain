"""Immutable analytics parameters from the canonical TOML (docs/00 §4)."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any

from stocgain.settings import REPOSITORY_ROOT

DEFAULT_PATH = REPOSITORY_ROOT / "backend/config/analytics.toml"
_DEFAULTS = tomllib.loads(DEFAULT_PATH.read_text())


@dataclass(frozen=True)
class AnalyticsConfig:
    """Frozen, serializable model settings; defaults have one source of truth."""

    model_version: str = _DEFAULTS["model_version"]
    lookback_days: int = _DEFAULTS["lookback_days"]
    half_life_days: int = _DEFAULTS["half_life_days"]
    min_clean_days_full: int = _DEFAULTS["min_clean_days_full"]
    min_clean_days_blend: int = _DEFAULTS["min_clean_days_blend"]
    forecast_horizon_days: int = _DEFAULTS["forecast_horizon_days"]
    service_level: float = _DEFAULTS["service_level"]
    review_period_days: int = _DEFAULTS["review_period_days"]
    normal_min_mean_units: int = _DEFAULTS["normal_min_mean_units"]
    tier_critical_probability: float = _DEFAULTS["tier_critical_probability"]
    tier_high_probability: float = _DEFAULTS["tier_high_probability"]
    tier_moderate_probability: float = _DEFAULTS["tier_moderate_probability"]
    exposure_escalation_usd: float = _DEFAULTS["exposure_escalation_usd"]
    expedite_probability: float = _DEFAULTS["expedite_probability"]
    lane_min_observations: int = _DEFAULTS["lane_min_observations"]
    contract_lead_time_cv: float = _DEFAULTS["contract_lead_time_cv"]
    default_delay_when_late_days: int = _DEFAULTS["default_delay_when_late_days"]
    carrying_cost_rate_annual: float = _DEFAULTS["carrying_cost_rate_annual"]
    backfill_weeks: int = _DEFAULTS["backfill_weeks"]
    backtest_origins: int = _DEFAULTS["backtest_origins"]
    on_time_window_days: int = _DEFAULTS["on_time_window_days"]
    dow_min_observations: int = _DEFAULTS["dow_min_observations"]
    lost_sale_rates: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(_DEFAULTS["lost_sale_rates"])
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible snapshot to persist with every analytics run."""
        return {
            f.name: dict(value) if isinstance(value, Mapping) else value
            for f in fields(self)
            for value in [getattr(self, f.name)]
        }


def load_config(path: Path = DEFAULT_PATH) -> AnalyticsConfig:
    """Read model settings; reject unknown keys rather than silently ignoring them."""
    values = tomllib.loads(path.read_text())
    if "lost_sale_rates" in values:
        values["lost_sale_rates"] = MappingProxyType(values["lost_sale_rates"])
    return AnalyticsConfig(**values)
