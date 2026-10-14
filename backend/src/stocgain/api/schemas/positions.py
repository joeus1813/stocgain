"""Explicit position-detail contracts from docs/08 §3.13–3.16."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import Field

from stocgain.api.schemas.common import (
    USD,
    Count,
    Days,
    LeadDays,
    Rate,
    Ratio,
    StrictModel,
    Units,
)


class RunInfo(StrictModel):
    run_id: Count = Field(description="Successful analytics run identifier.")
    as_of_date: Date = Field(description="End-of-day model cutoff.")
    model_version: str = Field(description="Version of the analytical model.")


class StoreInfo(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Stable store code.")
    store_name: str = Field(description="Fictional store display name.")
    region_name: str = Field(description="Region display name.")


class ProductInfo(StrictModel):
    product_id: Count = Field(description="Product identifier.")
    sku: str = Field(description="Stock keeping unit code.")
    product_name: str = Field(description="Fictional product display name.")
    category_name: str = Field(description="Category display name.")
    brand_name: str = Field(description="Fictional product brand.")
    unit_of_measure: str = Field(description="Unit in which stock is counted.")
    unit_price_usd: USD = Field(description="Regular selling price per unit.")
    unit_cost_usd: USD = Field(description="Acquisition cost per unit.")


class SupplierInfo(StrictModel):
    supplier_id: Count = Field(description="Primary supplier identifier.")
    supplier_code: str = Field(description="Stable supplier code.")
    supplier_name: str = Field(description="Fictional supplier display name.")
    case_pack_qty: Count = Field(description="Units in one orderable case.")
    min_order_qty: Count = Field(description="Minimum orderable units.")


class Driver(StrictModel):
    code: str = Field(description="Deterministic risk driver code.")
    label: str = Field(description="Human readable driver label.")
    description: str = Field(description="Explanation from stored model inputs.")


class RiskInfo(StrictModel):
    risk_tier: Literal["critical", "high", "moderate", "low"] = Field(
        description="Model risk tier."
    )
    stockout_probability: Ratio = Field(
        description="Estimated probability at the riskiest checkpoint."
    )
    currently_out_of_stock: bool = Field(
        description="No stock on hand with positive forecast demand."
    )
    binding_checkpoint_type: Literal["receipt", "window_end"] = Field(
        description="Type of the riskiest checkpoint."
    )
    projected_stockout_date: Date | None = Field(
        description="First expected-value stockout date within 42 days."
    )
    days_until_projected_stockout: Count | None = Field(
        description="Days from cutoff to projected stockout."
    )
    drivers: list[Driver] = Field(
        description="Descriptive associations explaining this risk."
    )
    explanation: str = Field(description="Deterministic model explanation.")


class NextReceipt(StrictModel):
    date: Date = Field(description="Expected receipt date.")
    units: Count = Field(description="Open units arriving on this date.")
    purchase_order_id: Count = Field(
        description="Lowest purchase-order identifier at this arrival."
    )
    po_number: str = Field(description="Purchase-order display number.")
    overdue: bool = Field(description="Promised date is at or before the cutoff.")


class InventoryInfo(StrictModel):
    on_hand_units: Count = Field(description="Closing stock at the cutoff.")
    on_order_units: Count = Field(description="Total outstanding purchase-order units.")
    inventory_position_units: Count = Field(
        description="On-hand plus all on-order units."
    )
    open_po_count: Count = Field(description="Number of distinct open purchase orders.")
    days_of_cover: Days | None = Field(
        description="On-hand coverage, capped at 365 days; null for zero demand."
    )
    next_receipt: NextReceipt | None = Field(
        description="Earliest expected inbound shipment, if any."
    )


class DemandInfo(StrictModel):
    forecast_method: Literal[
        "store_sku", "blended", "chain_fallback", "insufficient_data"
    ] = Field(description="Censoring-aware forecast method.")
    demand_pattern: Literal[
        "smooth", "erratic", "intermittent", "lumpy", "no_demand"
    ] = Field(description="Clean-day demand pattern classification.")
    base_daily_demand_units: Rate = Field(
        description="Deseasonalized daily demand level."
    )
    avg_daily_demand_units: Rate = Field(
        description="Average forecast demand over the next 28 days."
    )
    daily_demand_std_units: Rate = Field(
        description="Daily demand standard deviation after Poisson floor."
    )
    observed_demand_cv: Ratio | None = Field(
        description="Observed daily demand coefficient of variation."
    )
    demand_trend_ratio: Ratio | None = Field(
        description="Recent clean demand relative to the preceding six weeks."
    )
    lookback_days: Count = Field(description="Historical forecast lookback length.")
    clean_days: Count = Field(
        description="Uncensored nonpromotion days used to estimate demand."
    )
    censored_days: Count = Field(
        description="Stockout days excluded from the demand estimate."
    )
    promo_days: Count = Field(description="Promotion days in the historical window.")
    recent_censored_days: Count = Field(
        description="Censored days in the last 28 days."
    )
    forecast_7d_units: Units = Field(description="Expected demand over seven days.")
    forecast_14d_units: Units = Field(description="Expected demand over fourteen days.")
    forecast_28d_units: Units = Field(
        description="Expected demand over twenty-eight days."
    )
    forecast_7d_std_units: Units = Field(
        description="Seven-day demand standard deviation."
    )
    forecast_14d_std_units: Units = Field(
        description="Fourteen-day demand standard deviation."
    )
    forecast_28d_std_units: Units = Field(
        description="Twenty-eight-day demand standard deviation."
    )


class SupplyInfo(StrictModel):
    lead_time_source: Literal["lane", "supplier", "contract"] = Field(
        description="Source selected for lead-time estimates."
    )
    n_received_pos: Count = Field(
        description="Observed received purchase orders on the lane."
    )
    lead_time_mean_days: LeadDays = Field(
        description="Estimated mean replenishment lead time."
    )
    lead_time_std_days: LeadDays = Field(
        description="Estimated lead-time standard deviation."
    )
    mean_delay_days: float = Field(
        description="Mean receipt delay relative to the promised date; negative means early.",
        json_schema_extra={"x-unit": "days"},
    )
    on_time_rate: Ratio | None = Field(
        description="Lane on-time proportion over 90 days; null if no orders were due."
    )
    protection_window_days: LeadDays = Field(
        description="Demand window before a new order could arrive."
    )


class PolicyInfo(StrictModel):
    service_level: Ratio = Field(
        description="Cycle service level used for stock policy."
    )
    review_period_days: Count = Field(description="Review cadence in days.")
    distribution_family: Literal[
        "normal", "poisson", "negative_binomial", "degenerate"
    ] = Field(description="Demand family at the binding checkpoint.")
    lead_time_demand_mean_units: Units = Field(
        description="Expected demand across lead time."
    )
    lead_time_demand_std_units: Units = Field(
        description="Standard deviation of lead-time demand."
    )
    safety_stock_units: Units = Field(
        description="Safety stock at the selected service level."
    )
    reorder_point_units: Count = Field(
        description="Inventory-position reorder trigger."
    )
    order_up_to_units: Count = Field(
        description="Target inventory position after ordering."
    )
    below_reorder_point: bool = Field(
        description="Reorder trigger met with positive required quantity."
    )


class ExposureInfo(StrictModel):
    expected_shortage_units: Units = Field(
        description="Expected shortage at the binding checkpoint."
    )
    lost_sale_rate: Ratio = Field(
        description="Category planning assumption for the share of shortage lost."
    )
    expected_lost_units: Units = Field(
        description="Model estimate of shortage multiplied by lost-sale rate."
    )
    revenue_at_risk_usd: USD = Field(
        description="Model estimate of regular-price revenue at risk."
    )
    margin_at_risk_usd: USD = Field(
        description="Model estimate of gross margin at risk."
    )


class Checkpoint(StrictModel):
    checkpoint_seq: Count = Field(description="Ordered checkpoint sequence.")
    checkpoint_type: Literal["receipt", "window_end"] = Field(
        description="Receipt boundary or protection-window end."
    )
    purchase_order_id: Count | None = Field(
        description="Representative PO at a receipt checkpoint."
    )
    po_number: str | None = Field(description="Representative PO display number.")
    arrival_date: Date | None = Field(
        description="Expected receipt date for receipt checkpoints."
    )
    window_days: LeadDays = Field(description="Demand days preceding this checkpoint.")
    window_std_days: LeadDays = Field(description="Uncertainty of checkpoint timing.")
    supply_units: Count = Field(
        description="Stock plus shipments arriving strictly before this checkpoint."
    )
    demand_mean_units: Units = Field(
        description="Expected demand before the checkpoint."
    )
    demand_std_units: Units = Field(
        description="Demand standard deviation before the checkpoint."
    )
    distribution_family: Literal[
        "normal", "poisson", "negative_binomial", "degenerate"
    ] = Field(description="Distribution used for this checkpoint.")
    stockout_probability: Ratio = Field(
        description="Estimated probability demand exceeds supply."
    )
    expected_shortage_units: Units = Field(
        description="Expected positive demand shortfall."
    )
    is_binding: bool = Field(
        description="Whether this checkpoint determines the snapshot risk."
    )


class RelatedOrder(StrictModel):
    purchase_order_id: Count = Field(description="Purchase-order identifier.")
    po_number: str = Field(description="Purchase-order display number.")


class RecommendationInfo(StrictModel):
    action_type: Literal["expedite_po", "reorder", "monitor", "no_action"] = Field(
        description="Primary decision-support action."
    )
    urgency: Literal["urgent", "standard"] | None = Field(
        description="Action urgency; null for no action."
    )
    priority_rank: Count | None = Field(
        description="Run-wide lexicographic action rank."
    )
    recommended_order_units: Count | None = Field(
        description="Orderable quantity when the reorder trigger is met."
    )
    recommended_order_cases: Count | None = Field(
        description="Orderable quantity expressed in whole cases."
    )
    recommended_order_cost_usd: USD | None = Field(
        description="Estimated acquisition cost of the recommended order."
    )
    related_purchase_order: RelatedOrder | None = Field(
        description="Existing purchase order to expedite."
    )
    rationale: str = Field(
        description="Deterministic explanation of the recommendation."
    )


class PositionDetail(StrictModel):
    run: RunInfo = Field(description="Analytics run provenance.")
    store: StoreInfo = Field(description="Store context.")
    product: ProductInfo = Field(description="Product context.")
    supplier: SupplierInfo = Field(description="Primary sourcing context.")
    risk: RiskInfo = Field(description="Estimated near-term stockout risk.")
    inventory: InventoryInfo = Field(
        description="As-of inventory quantities and next inbound shipment."
    )
    demand: DemandInfo = Field(description="Stored demand forecast and diagnostics.")
    supply: SupplyInfo = Field(description="Stored lane lead-time estimates.")
    policy: PolicyInfo = Field(description="Inventory replenishment policy.")
    exposure: ExposureInfo = Field(description="Estimated financial exposure.")
    checkpoints: list[Checkpoint] = Field(
        description="Ordered supply-demand checkpoints."
    )
    recommendation: RecommendationInfo = Field(
        description="Decision support; never an order write-back."
    )


class HistoryDay(StrictModel):
    date: Date = Field(description="Historical business date.")
    units_sold: Count = Field(description="Observed units sold.")
    opening_on_hand_units: Count = Field(
        description="Start-of-day stock before receipts."
    )
    units_received: Count = Field(description="Units received at the start of the day.")
    net_adjustment_units: int = Field(
        description="Signed inventory adjustment posted at day end.",
        json_schema_extra={"x-unit": "units"},
    )
    closing_on_hand_units: Count = Field(description="End-of-day stock.")
    availability_status: Literal["in_stock", "sold_out", "out_all_day"] = Field(
        description="Observed daily availability classification."
    )
    is_censored: bool = Field(
        description="Observed sales may be lower than demand because stock ran out."
    )
    promotion_id: Count | None = Field(
        description="Active promotion identifier, if any."
    )
    promotion_name: str | None = Field(description="Active promotion display name.")


class ForecastDay(StrictModel):
    date: Date = Field(description="Future demand date.")
    horizon_day: Count = Field(description="Day index following the cutoff.")
    forecast_units: Units = Field(description="Estimated demand units.")
    promo_multiplier: Ratio = Field(description="Planned promotion demand multiplier.")


class PositionHistory(StrictModel):
    days: list[HistoryDay] = Field(
        description="Historical observations in ascending date order."
    )
    forecast: list[ForecastDay] = Field(description="Next 28 stored forecast days.")


class ActualPoint(StrictModel):
    date: Date = Field(description="Observed inventory date.")
    kind: Literal["actual"] = Field(description="Identifies an observed stock balance.")
    on_hand_units: Count = Field(description="Observed closing on-hand inventory.")


class ProjectedPoint(StrictModel):
    date: Date = Field(description="Projection date.")
    kind: Literal["projected"] = Field(
        description="Identifies an expected-value projection."
    )
    expected_on_hand_units: Units = Field(
        description="Expected closing stock under lost-sales dynamics."
    )
    band_low_units: Units = Field(
        description="Approximate lower inventory bound from demand uncertainty."
    )
    band_high_units: Units = Field(
        description="Approximate upper inventory bound from demand uncertainty."
    )
    forecast_units: Units = Field(description="Expected demand during this day.")
    receipts_units: Count = Field(
        description="Expected receipts at the start of this day."
    )


class ProjectionReceipt(StrictModel):
    date: Date = Field(description="Expected arrival date.")
    purchase_order_id: Count = Field(description="Purchase-order identifier.")
    po_number: str = Field(description="Purchase-order display number.")
    units: Count = Field(description="Open units expected to arrive.")
    overdue: bool = Field(description="Promised delivery date is at or before cutoff.")


class PositionProjection(StrictModel):
    as_of_date: Date = Field(description="End-of-day model cutoff.")
    reorder_point_units: Count = Field(description="Stored reorder trigger.")
    safety_stock_units: Units = Field(description="Stored safety-stock level.")
    projected_stockout_date: Date | None = Field(
        description="First expected stockout within the full 42-day horizon."
    )
    points: list[
        Annotated[ActualPoint | ProjectedPoint, Field(discriminator="kind")]
    ] = Field(description="Chronological observed and projected inventory.")
    receipts: list[ProjectionReceipt] = Field(
        description="Expected inbound deliveries in the requested horizon."
    )
    notes: str = Field(description="Projection assumptions and uncertainty caveat.")


class OpenOrder(StrictModel):
    purchase_order_id: Count = Field(description="Purchase-order identifier.")
    po_number: str = Field(description="Purchase-order display number.")
    order_date: Date = Field(description="Order placement date.")
    promised_delivery_date: Date = Field(description="Supplier promised delivery date.")
    expected_arrival_date: Date = Field(description="Model estimated receipt date.")
    quantity_ordered: Count = Field(description="Units originally ordered.")
    quantity_received: Count = Field(description="Units received by the cutoff.")
    quantity_cancelled: Count = Field(
        description="Cancelled units known by the cutoff."
    )
    open_quantity: Count = Field(description="Outstanding units as of cutoff.")
    status: Literal["open", "partially_received"] = Field(
        description="Line-level as-of fulfillment status."
    )
    overdue: bool = Field(description="Promised date is at or before the cutoff.")


class ReceivedOrder(StrictModel):
    purchase_order_id: Count = Field(description="Purchase-order identifier.")
    po_number: str = Field(description="Purchase-order display number.")
    order_date: Date = Field(description="Order placement date.")
    promised_delivery_date: Date = Field(description="Supplier promised delivery date.")
    first_receipt_date: Date = Field(description="First receipt date known by cutoff.")
    quantity_ordered: Count = Field(description="Units originally ordered.")
    quantity_received: Count = Field(description="Units received by cutoff.")
    quantity_cancelled: Count = Field(description="Cancelled units known by cutoff.")
    status: Literal["received", "closed_short"] = Field(
        description="Completed line status as of cutoff."
    )
    delay_days: int = Field(
        description="Signed days from promised date to first receipt.",
        json_schema_extra={"x-unit": "days"},
    )


class PositionOrders(StrictModel):
    open: list[OpenOrder] = Field(
        description="Outstanding purchase-order lines for this product."
    )
    recent_received: list[ReceivedOrder] = Field(
        description="Most recently received completed lines, newest first."
    )
