"""Explicit P0 overview, recommendation and risk-list contracts (docs/08 §3)."""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from stocgain.api.schemas.common import (
    USD,
    Count,
    Days,
    Rate,
    Ratio,
    StrictModel,
)

RiskTier = Literal["critical", "high", "moderate", "low"]
ActionType = Literal["expedite_po", "reorder", "monitor", "no_action"]
RecommendedAction = Literal["expedite_po", "reorder", "monitor"]
Urgency = Literal["urgent", "standard"]
WholeUnits = Annotated[int, Field(json_schema_extra={"x-unit": "units"})]


class OverviewSummary(StrictModel):
    as_of_date: date = Field(description="End-of-day model cutoff.")
    run_id: Count = Field(description="Selected successful current run.")
    active_positions: Count = Field(description="Store-product positions in scope.")
    active_skus: Count = Field(description="Distinct products in scope.")
    at_risk_positions: Count = Field(description="Critical or high risk positions.")
    critical_positions: Count = Field(description="Critical risk positions.")
    at_risk_rate: Ratio = Field(
        description="At-risk share of positions; zero for empty scope."
    )
    prior_at_risk_positions: Count | None = Field(
        description="At-risk count seven days earlier; null without prior run."
    )
    at_risk_positions_change: Count | None = Field(
        description="Current minus prior at-risk count; null without prior run."
    )
    gross_margin_at_risk_usd: USD = Field(
        description="Estimated gross margin exposed to stockouts."
    )
    revenue_at_risk_usd: USD = Field(
        description="Estimated revenue exposed to stockouts."
    )
    median_days_of_cover: Days | None = Field(
        description="Median finite demand coverage; null without demand."
    )
    supplier_on_time_rate: Ratio | None = Field(
        description="Due POs first received on time; null if none due."
    )
    supplier_pos_due: Count = Field(
        description="POs due in the supplier measurement window."
    )
    supplier_on_time_window_days: Count = Field(
        description="Supplier measurement window in days.",
        json_schema_extra={"x-unit": "days"},
    )
    in_stock_rate: Ratio | None = Field(
        description="Share of position-days with positive closing stock; null if empty."
    )
    in_stock_rate_prior: Ratio | None = Field(
        description="Prior 28-day in-stock share; null if unavailable."
    )
    in_stock_window_days: Count = Field(
        description="Availability measurement window in days.",
        json_schema_extra={"x-unit": "days"},
    )


class RiskTierCount(StrictModel):
    risk_tier: RiskTier = Field(description="Risk severity tier.")
    positions: Count = Field(description="Positions assigned this tier.")
    share_of_positions: Ratio = Field(description="Tier share of filtered positions.")
    margin_at_risk_usd: USD = Field(
        description="Estimated gross margin exposed in this tier."
    )


class RiskDistribution(StrictModel):
    tiers: list[RiskTierCount] = Field(
        description="All four tiers ordered critical to low, including zeros."
    )
    total_positions: Count = Field(description="Total filtered positions.")


class TrendPoint(StrictModel):
    as_of_date: date = Field(description="Historical model cutoff.")
    run_id: Count = Field(description="Selected successful run for this date.")
    critical: Count = Field(description="Critical positions.")
    high: Count = Field(description="High risk positions.")
    moderate: Count = Field(description="Moderate risk positions.")
    low: Count = Field(description="Low risk positions.")
    margin_at_risk_usd: USD = Field(
        description="Estimated margin at risk across all tiers."
    )


class RiskTrend(StrictModel):
    points: list[TrendPoint] = Field(
        description="One point per available cutoff date, ascending."
    )


class StoreComparisonItem(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Store display code.")
    store_name: str = Field(description="Fictional store name.")
    region_name: str = Field(description="Store region.")
    positions: Count = Field(description="Positions in scope at this store.")
    at_risk_positions: Count = Field(description="Critical or high positions.")
    critical_positions: Count = Field(description="Critical positions.")
    margin_at_risk_usd: USD = Field(description="Estimated gross margin at risk.")
    in_stock_rate: Ratio | None = Field(
        description="Trailing 28-day in-stock share; null if no observations."
    )


class StoreComparison(StrictModel):
    stores: list[StoreComparisonItem] = Field(
        description="Stores sorted by margin at risk, ignoring selected store filters."
    )


class HeatmapStore(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Store display code.")


class HeatmapCategory(StrictModel):
    category_id: Count = Field(description="Category identifier.")
    category_name: str = Field(description="Category name.")


class HeatmapCell(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    category_id: Count = Field(description="Category identifier.")
    positions: Count = Field(description="Store-category positions.")
    at_risk_positions: Count = Field(description="Critical or high positions.")
    at_risk_rate: Ratio = Field(description="At-risk share; zero if no positions.")
    margin_at_risk_usd: USD = Field(description="Estimated margin at risk.")


class CategoryHeatmap(StrictModel):
    stores: list[HeatmapStore] = Field(description="Stores defining the heatmap rows.")
    categories: list[HeatmapCategory] = Field(
        description="Categories defining the heatmap columns."
    )
    cells: list[HeatmapCell] = Field(description="Dense store-category grid.")


class TopProduct(StrictModel):
    product_id: Count = Field(description="Product identifier.")
    sku: str = Field(description="Product SKU.")
    product_name: str = Field(description="Fictional product name.")
    category_name: str = Field(description="Product category.")
    at_risk_stores: Count = Field(description="Stores with critical or high risk.")
    critical_stores: Count = Field(description="Stores with critical risk.")
    margin_at_risk_usd: USD = Field(
        description="Estimated margin at risk across stores."
    )


class TopProducts(StrictModel):
    items: list[TopProduct] = Field(
        description="Products with at least one at-risk store, by exposure."
    )


class RelatedPurchaseOrder(StrictModel):
    purchase_order_id: Count = Field(description="Existing purchase order identifier.")
    po_number: str = Field(description="Existing purchase order display number.")


class RecommendationItem(StrictModel):
    priority_rank: Count = Field(
        description="Original global priority rank, preserved under filtering."
    )
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Store display code.")
    product_id: Count = Field(description="Product identifier.")
    sku: str = Field(description="Product SKU.")
    product_name: str = Field(description="Fictional product name.")
    category_name: str = Field(description="Product category.")
    risk_tier: RiskTier = Field(description="Stored risk tier.")
    stockout_probability: Ratio = Field(
        description="Estimated probability at the binding checkpoint."
    )
    margin_at_risk_usd: USD = Field(description="Estimated gross margin at risk.")
    action_type: RecommendedAction = Field(
        description="Suggested decision-support action."
    )
    urgency: Urgency = Field(description="Suggested urgency.")
    recommended_order_units: WholeUnits | None = Field(
        description="Suggested whole-unit order quantity; null when no order is recommended."
    )
    recommended_order_cost_usd: USD | None = Field(
        description="Estimated purchase cost; null when no order is recommended."
    )
    related_purchase_order: RelatedPurchaseOrder | None = Field(
        description="Existing PO associated with action, or null."
    )
    rationale: str = Field(
        description="Stored deterministic explanation of the action."
    )
    days_until_projected_stockout: Count | None = Field(
        description="Days until projected stockout, or null if none in horizon.",
        json_schema_extra={"x-unit": "days"},
    )


class Recommendations(StrictModel):
    items: list[RecommendationItem] = Field(
        description="Stored actionable recommendations in global rank order."
    )


class RiskPosition(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Store display code.")
    store_name: str = Field(description="Fictional store name.")
    region_name: str = Field(description="Store region.")
    product_id: Count = Field(description="Product identifier.")
    sku: str = Field(description="Product SKU.")
    product_name: str = Field(description="Fictional product name.")
    category_id: Count = Field(description="Category identifier.")
    category_name: str = Field(description="Product category.")
    supplier_id: Count = Field(description="Primary supplier identifier.")
    supplier_name: str = Field(description="Fictional primary supplier name.")
    on_hand_units: WholeUnits = Field(description="Closing inventory at cutoff.")
    on_order_units: WholeUnits = Field(
        description="Outstanding quantity on existing POs."
    )
    avg_daily_demand_units: Rate = Field(
        description="Mean forecast daily demand over 28 days."
    )
    days_of_cover: Days | None = Field(
        description="On-hand divided by daily demand; null at zero demand."
    )
    next_receipt_date: date | None = Field(
        description="Expected next receipt date; null without inbound."
    )
    next_receipt_units: WholeUnits | None = Field(
        description="Expected next receipt quantity; null without inbound."
    )
    next_receipt_po_number: str | None = Field(
        description="Representative next PO number; null without inbound."
    )
    next_receipt_overdue: bool = Field(
        description="Whether the next PO is past its promise."
    )
    stockout_probability: Ratio = Field(
        description="Estimated stockout probability before replenishment."
    )
    risk_tier: RiskTier = Field(description="Stored severity tier.")
    margin_at_risk_usd: USD = Field(description="Estimated gross margin exposed.")
    revenue_at_risk_usd: USD = Field(description="Estimated revenue exposed.")
    below_reorder_point: bool = Field(
        description="Whether inventory position is at or below reorder point."
    )
    action_type: ActionType = Field(description="Stored suggested action.")
    urgency: Urgency | None = Field(
        description="Stored action urgency; null for no action."
    )
    priority_rank: Count | None = Field(
        description="Global action rank; null for no action."
    )
    recommended_order_units: WholeUnits | None = Field(
        description="Suggested whole-unit order quantity; null when no order is recommended."
    )


class RiskListSummary(StrictModel):
    positions: Count = Field(
        description="Positions matching every filter, across all pages."
    )
    critical: Count = Field(description="Filtered critical positions.")
    high: Count = Field(description="Filtered high positions.")
    moderate: Count = Field(description="Filtered moderate positions.")
    low: Count = Field(description="Filtered low positions.")
    margin_at_risk_usd: USD = Field(
        description="Estimated exposure across the complete filtered set."
    )


class RiskPositions(StrictModel):
    items: list[RiskPosition] = Field(description="Stable page of filtered positions.")
    page: Count = Field(description="Requested one-based page.")
    page_size: Count = Field(description="Maximum positions per page.")
    total_items: Count = Field(description="Total filtered positions.")
    total_pages: Count = Field(description="Number of pages; zero for empty scope.")
    summary: RiskListSummary = Field(
        description="Aggregates over the complete filtered set."
    )


SortBy = Literal[
    "priority",
    "product_name",
    "store_code",
    "category_name",
    "on_hand_units",
    "avg_daily_demand_units",
    "days_of_cover",
    "next_receipt_date",
    "stockout_probability",
    "risk_tier",
    "margin_at_risk_usd",
]
SortDirection = Literal["asc", "desc"]
