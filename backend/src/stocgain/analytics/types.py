"""Plain records exchanged by the analytics pipeline; units follow docs/03."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from stocgain.analytics.config import AnalyticsConfig

type Record = dict[str, Any]


@dataclass
class ModelInputs:
    """Point-in-time operational inputs, never simulation truth."""

    as_of: date
    config: AnalyticsConfig
    positions: list[Record]
    history: list[Record]
    dow: list[Record]
    chain: list[Record]
    scales: list[Record]
    promotions: list[Record]
    lanes: list[Record]
    suppliers: list[Record]
    open_pos: list[Record]


@dataclass
class ModelOutputs:
    """Full precision results; database storage is the rounding boundary."""

    forecasts: list[Record]
    daily: list[Record]
    lanes: list[Record]
    risks: list[Record]
    checkpoints: list[Record]
    recommendations: list[Record]
    evaluations: list[Record] = field(default_factory=list)
