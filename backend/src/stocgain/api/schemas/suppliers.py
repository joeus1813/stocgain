"""Supplier performance and persisted evaluation contracts, docs/08 §3.18–21."""

from datetime import date

from pydantic import Field

from stocgain.api.schemas.common import USD, Count, LeadDays, Ratio, StrictModel


class SupplierItem(StrictModel):
    supplier_id: Count = Field(description="Supplier id.")
    supplier_code: str = Field(description="Supplier code.")
    supplier_name: str = Field(description="Supplier name.")
    category_name: str = Field(description="Category name.")
    pos_due_90d: Count = Field(description="Pos due 90d.")
    on_time_rate: Ratio | None = Field(
        description="POs first received by the promise divided by all POs due in the trailing 90 days."
    )
    in_full_rate: Ratio | None = Field(
        description="Share of due POs fully received in one receipt per line without cancellations."
    )
    mean_lead_time_days: LeadDays | None = Field(
        description="PO-weighted mean received lead time over the trailing 180 days."
    )
    std_lead_time_days: LeadDays | None = Field(
        description="Sample standard deviation of received lead time in days."
    )
    p90_lead_time_days: LeadDays | None = Field(description="P90 lead time days.")
    lead_time_cv: Ratio | None = Field(description="Lead time cv.")
    overdue_open_pos: Count = Field(description="Overdue open pos.")
    at_risk_positions: Count = Field(description="At risk positions.")
    margin_at_risk_usd: USD = Field(
        description="Estimated gross margin exposure from persisted current-run positions."
    )
    review_flag: bool = Field(
        description="Low on-time rate or high lead-time CV associated with at least one at-risk position."
    )
    reliability_rank: Count = Field(
        description="Rank by on-time rate ascending, null rates last."
    )


class SupplierList(StrictModel):
    items: list[SupplierItem] = Field(description="Items.")
    disclaimer: str = Field(description="Disclaimer.")


class SupplierSummary(StrictModel):
    suppliers: Count = Field(description="Suppliers.")
    flagged_suppliers: Count = Field(description="Flagged suppliers.")
    on_time_rate_90d: Ratio | None = Field(
        description="PO-weighted on-time proportion across suppliers in scope."
    )
    mean_lead_time_days: LeadDays | None = Field(
        description="PO-weighted mean received lead time over the trailing 180 days."
    )
    overdue_open_pos: Count = Field(description="Overdue open pos.")


class SupplierIdentity(StrictModel):
    supplier_id: Count = Field(description="Supplier id.")
    supplier_code: str = Field(description="Supplier code.")
    supplier_name: str = Field(description="Supplier name.")
    category_name: str = Field(description="Category name.")


class SupplierPerformance(StrictModel):
    on_time_rate: Ratio | None = Field(
        description="POs first received by the promise divided by all POs due in the trailing 90 days."
    )
    in_full_rate: Ratio | None = Field(
        description="Share of due POs fully received in one receipt per line without cancellations."
    )
    mean_lead_time_days: LeadDays | None = Field(
        description="PO-weighted mean received lead time over the trailing 180 days."
    )
    std_lead_time_days: LeadDays | None = Field(
        description="Sample standard deviation of received lead time in days."
    )
    review_flag: bool = Field(
        description="Low on-time rate or high lead-time CV associated with at least one at-risk position."
    )


class WeeklyOnTime(StrictModel):
    week_start_date: date = Field(description="Week start date.")
    pos_due: Count = Field(description="Pos due.")
    on_time_rate: Ratio | None = Field(
        description="POs first received by the promise divided by all POs due in the trailing 90 days."
    )


class LeadBin(StrictModel):
    lead_time_days: Count = Field(description="Lead time days.")
    pos: Count = Field(description="Pos.")


class SupplierLane(StrictModel):
    store_id: Count = Field(description="Store id.")
    store_code: str = Field(description="Store code.")
    pos_received_180d: Count = Field(
        description="Purchase orders first received in the trailing 180 days."
    )
    on_time_rate: Ratio | None = Field(
        description="POs first received by the promise divided by all POs due in the trailing 90 days."
    )
    mean_lead_time_days: LeadDays | None = Field(
        description="PO-weighted mean received lead time over the trailing 180 days."
    )
    std_lead_time_days: LeadDays | None = Field(
        description="Sample standard deviation of received lead time in days."
    )
    overdue_open_pos: Count = Field(description="Overdue open pos.")


class ExposedPosition(StrictModel):
    store_id: Count = Field(description="Store id.")
    product_id: Count = Field(description="Product id.")
    sku: str = Field(description="Sku.")
    product_name: str = Field(description="Product name.")
    risk_tier: str = Field(description="Risk tier.")
    stockout_probability: Ratio = Field(
        description="Estimated probability at the binding checkpoint."
    )
    margin_at_risk_usd: USD = Field(
        description="Estimated gross margin exposure from persisted current-run positions."
    )


class SupplierDetail(StrictModel):
    supplier: SupplierIdentity = Field(description="Supplier.")
    performance: SupplierPerformance = Field(description="Performance.")
    weekly_on_time: list[WeeklyOnTime] = Field(description="Weekly on time.")
    lead_time_histogram: list[LeadBin] = Field(description="Lead time histogram.")
    contract_lead_time_days_avg: LeadDays | None = Field(
        description="Contract lead time days avg."
    )
    lanes: list[SupplierLane] = Field(description="Lanes.")
    exposed_positions: list[ExposedPosition] = Field(description="Exposed positions.")
    disclaimer: str = Field(description="Disclaimer.")


class EvaluationRow(StrictModel):
    model_name: str = Field(description="Model name.")
    evaluation_basis: str = Field(
        description="Observed in-stock sales or simulation-only hidden-demand evaluation basis."
    )
    segment_type: str = Field(description="Segment type.")
    segment_value: str = Field(description="Segment value.")
    n_observations: Count = Field(description="N observations.")
    mae: float | None = Field(
        description="Mean absolute error in units.",
        json_schema_extra={"x-unit": "units"},
    )
    wape: Ratio | None = Field(
        description="Sum absolute error divided by total actual units; null at zero denominator."
    )
    bias_rate: Ratio | None = Field(
        description="Sum forecast minus actual units divided by actual units."
    )


class Evaluation(StrictModel):
    run_id: Count = Field(description="Run id.")
    first_origin_date: date | None = Field(description="First origin date.")
    last_origin_date: date | None = Field(description="Last origin date.")
    n_origins: Count = Field(description="N origins.")
    rows: list[EvaluationRow] = Field(description="Rows.")
    notes: dict[str, str] = Field(description="Notes.")


class SensitivityItem(StrictModel):
    key: str = Field(description="Key.")
    label: str = Field(description="Label.")
    stockout_probability: Ratio = Field(
        description="Estimated probability at the binding checkpoint."
    )


class Sensitivity(StrictModel):
    baseline_probability: Ratio = Field(
        description="Baseline estimated probability from the unchanged risk model."
    )
    scenarios: list[SensitivityItem] = Field(description="Scenarios.")
    note: str = Field(description="Note.")
