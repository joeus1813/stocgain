"""Stateless Scenario Lab request and response contracts (docs/08 §3.22)."""

from datetime import date
from typing import Annotated

from pydantic import Field, StrictInt

from stocgain.api.schemas.common import USD, Count, Days, Ratio, StrictModel, Units


class Scope(StrictModel):
    store_ids: list[Count] | None = Field(
        default=None, max_length=100, description="Optional stores; null means all."
    )
    category_ids: list[Count] | None = Field(
        default=None, max_length=100, description="Optional categories; null means all."
    )
    supplier_ids: list[Count] | None = Field(
        default=None,
        max_length=100,
        description="Optional primary suppliers; null means all.",
    )


class Assumptions(StrictModel):
    lead_time_change_days: Annotated[
        StrictInt, Field(json_schema_extra={"x-unit": "days"})
    ] = Field(
        default=0,
        ge=-7,
        le=14,
        description="Shift in lane mean and expected inbound arrival dates.",
    )
    demand_change_rate: Ratio = Field(
        default=0,
        ge=-0.5,
        le=1,
        description="Relative change in demand mean and standard deviation.",
    )
    service_level: Ratio | None = Field(
        default=None,
        ge=0.8,
        le=0.995,
        description="Cycle service level; omitted uses persisted run setting.",
    )
    safety_stock_buffer_rate: Ratio = Field(
        default=0, ge=-0.5, le=1, description="Relative safety stock buffer adjustment."
    )


class ScenarioRequest(StrictModel):
    scope: Scope = Field(
        default_factory=Scope, description="Intersecting position scope."
    )
    assumptions: Assumptions = Field(
        default_factory=Assumptions,
        description="Scenario model controls; defaults are neutral.",
    )


class TierCounts(StrictModel):
    critical: Count = Field(description="Critical positions.")
    high: Count = Field(description="High positions.")
    moderate: Count = Field(description="Moderate positions.")
    low: Count = Field(description="Low positions.")


class ScenarioMetrics(StrictModel):
    at_risk_positions: Count = Field(description="Critical plus high positions.")
    mean_stockout_probability: Ratio = Field(
        description="Mean modeled stockout probability."
    )
    expected_shortage_units: Units = Field(
        description="Sum of modeled expected shortages."
    )
    revenue_at_risk_usd: USD = Field(description="Estimated revenue exposure.")
    margin_at_risk_usd: USD = Field(description="Estimated gross margin exposure.")
    lead_time_demand_units: Units = Field(
        description="Sum of expected lead-time demand."
    )
    safety_stock_units: Units = Field(description="Sum of policy safety stock.")
    safety_stock_value_usd: USD = Field(description="Safety stock valued at unit cost.")
    positions_below_reorder_point: Count = Field(
        description="Positions triggering reorder policy."
    )
    recommended_order_units: Units = Field(
        description="Sum of recommended order units."
    )
    recommended_order_value_usd: USD = Field(
        description="Recommended units valued at unit cost."
    )
    annual_carrying_cost_usd: USD = Field(
        description="Safety stock value times assumed annual carrying rate."
    )
    annual_expected_shortfall_margin_usd: USD = Field(
        description="Annualized expected policy shortfall margin; model estimate."
    )
    avg_lead_time_days: Days = Field(description="Average estimated lane lead time.")


class ScenarioSummary(ScenarioMetrics):
    positions_by_tier: TierCounts = Field(
        description="Counts under each probability tier."
    )


class Delta(StrictModel):
    absolute: ScenarioMetrics = Field(
        description="Scenario minus baseline in each metric unit."
    )
    relative: dict[str, Ratio | None] = Field(
        description="Relative difference; null for zero baseline or probability metrics."
    )


class Transitions(StrictModel):
    order: list[str] = Field(description="Tier row and column order.")
    matrix: list[list[Count]] = Field(
        description="Counts from baseline row tier to scenario column tier."
    )


class CategoryChange(StrictModel):
    category_id: Count = Field(description="Category identifier.")
    category_name: str = Field(description="Category name.")
    baseline_margin_at_risk_usd: USD = Field(
        description="Baseline modeled margin exposure."
    )
    scenario_margin_at_risk_usd: USD = Field(
        description="Scenario modeled margin exposure."
    )
    baseline_at_risk_positions: Count = Field(
        description="Baseline critical/high count."
    )
    scenario_at_risk_positions: Count = Field(
        description="Scenario critical/high count."
    )


class PositionChange(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    product_id: Count = Field(description="Product identifier.")
    sku: str = Field(description="Fictional SKU.")
    product_name: str = Field(description="Fictional product name.")
    store_code: str = Field(description="Fictional store code.")
    baseline_tier: str = Field(description="Baseline risk tier.")
    scenario_tier: str = Field(description="Scenario risk tier.")
    baseline_stockout_probability: Ratio = Field(
        description="Baseline estimated probability."
    )
    scenario_stockout_probability: Ratio = Field(
        description="Scenario estimated probability."
    )
    baseline_margin_at_risk_usd: USD = Field(
        description="Baseline estimated margin exposure."
    )
    scenario_margin_at_risk_usd: USD = Field(
        description="Scenario estimated margin exposure."
    )
    baseline_recommended_order_units: Units | None = Field(
        description="Baseline order recommendation; null if unnecessary."
    )
    scenario_recommended_order_units: Units | None = Field(
        description="Scenario order recommendation; null if unnecessary."
    )


class ScenarioResponse(StrictModel):
    run_id: Count = Field(description="Immutable baseline run identifier.")
    as_of_date: date = Field(description="Baseline end-of-day observation cutoff.")
    assumptions_applied: Assumptions = Field(
        description="Resolved assumptions, including run default service level."
    )
    positions_in_scope: Count = Field(
        description="Positions in the scope intersection."
    )
    baseline: ScenarioSummary = Field(
        description="Neutral baseline computed with run settings."
    )
    scenario: ScenarioSummary = Field(description="Recalculated scenario metrics.")
    delta: Delta = Field(description="Absolute and relative changes.")
    tier_transitions: Transitions = Field(
        description="Complete baseline-to-scenario tier matrix."
    )
    by_category: list[CategoryChange] = Field(
        description="Category exposure and risk comparisons."
    )
    top_changes: list[PositionChange] = Field(
        description="Twenty greatest increases in margin exposure, then probability."
    )
    warnings: list[str] = Field(
        description="Floored lead time or model assumption warnings."
    )
    computation_ms: Annotated[
        float, Field(json_schema_extra={"x-unit": "milliseconds"})
    ] = Field(description="Measured server calculation time, milliseconds.")
