"""Dataset provenance, configuration and filter contracts (docs/08 §§3.2–3.3)."""

from datetime import date, datetime

from pydantic import Field

from stocgain.api.schemas.common import USD, Count, Days, Ratio, StrictModel


class Region(StrictModel):
    region_id: Count = Field(description="Region identifier.")
    region_code: str = Field(description="Fictional region code.")
    region_name: str = Field(description="Region name.")


class Store(StrictModel):
    store_id: Count = Field(description="Store identifier.")
    store_code: str = Field(description="Fictional store code.")
    store_name: str = Field(description="Fictional store name.")
    region_id: Count = Field(description="Region identifier.")


class Category(StrictModel):
    category_id: Count = Field(description="Category identifier.")
    category_code: str = Field(description="Category code.")
    category_name: str = Field(description="Category name.")


class Supplier(StrictModel):
    supplier_id: Count = Field(description="Supplier identifier.")
    supplier_code: str = Field(description="Fictional supplier code.")
    supplier_name: str = Field(description="Fictional supplier name.")
    category_id: Count = Field(description="Primary category identifier.")


class FiltersResponse(StrictModel):
    regions: list[Region] = Field(description="Regions sorted by code.")
    stores: list[Store] = Field(description="Stores sorted by code.")
    categories: list[Category] = Field(description="Categories sorted by code.")
    suppliers: list[Supplier] = Field(description="Suppliers sorted by code.")


class DatasetCounts(StrictModel):
    stores: Count = Field(description="Loaded stores.")
    regions: Count = Field(description="Loaded regions.")
    products: Count = Field(description="Loaded products.")
    suppliers: Count = Field(description="Loaded suppliers.")
    categories: Count = Field(description="Loaded categories.")


class Event(StrictModel):
    id: str = Field(description="Configured simulation event identifier.")
    name: str = Field(description="Simulation event name.")
    description: str = Field(description="Simulation event description.")


class Dataset(StrictModel):
    data_origin: str = Field(description="Synthetic or public provenance.")
    label: str = Field(description="Required visible provenance label.")
    provenance_statement: str = Field(
        description="Simulation provenance and limitations."
    )
    generator_version: str = Field(description="Stored generator version.")
    preset: str = Field(description="Loaded generator preset.")
    seed: Count = Field(description="Deterministic generation seed.")
    history_start_date: date = Field(description="First retained history date.")
    history_end_date: date = Field(description="Final retained history date.")
    row_counts: dict[str, Count] = Field(description="Manifest row counts by table.")
    counts: DatasetCounts = Field(description="Actual database dimension counts.")
    events: list[Event] = Field(description="Configured synthetic events.")


class Run(StrictModel):
    run_id: Count = Field(description="Immutable analytics run identifier.")
    run_type: str = Field(description="Current or historical backfill.")
    as_of_date: date = Field(description="End-of-day observation cutoff.")
    model_version: str = Field(description="Version of model configuration.")
    completed_at: datetime = Field(description="Successful completion time UTC.")
    backfill_runs_available: Count = Field(description="Succeeded historical runs.")


class ScenarioLimits(StrictModel):
    lead_time_change_days: list[Days] = Field(
        description="Inclusive lead-time shift limits."
    )
    demand_change_rate: list[Ratio] = Field(
        description="Inclusive relative demand limits."
    )
    service_level: list[Ratio] = Field(description="Inclusive cycle service limits.")
    safety_stock_buffer_rate: list[Ratio] = Field(
        description="Inclusive buffer change limits."
    )


class Parameters(StrictModel):
    service_level: Ratio = Field(description="Cycle service level.")
    review_period_days: Days = Field(description="Review cadence.")
    lookback_days: Days = Field(description="Forecast lookback.")
    half_life_days: Days = Field(description="EWMA half life.")
    min_clean_days_full: Days = Field(
        description="Minimum clean days for local estimate."
    )
    min_clean_days_blend: Days = Field(
        description="Minimum clean days for blended estimate."
    )
    normal_min_mean_units: Count = Field(
        description="Window demand threshold for Normal family."
    )
    tier_thresholds: dict[str, Ratio] = Field(
        description="Probability tier thresholds."
    )
    exposure_escalation_usd: USD = Field(
        description="Margin exposure escalation threshold."
    )
    carrying_cost_rate_annual: Ratio = Field(
        description="Assumed annual carrying rate."
    )
    lost_sale_rates: dict[str, Ratio] = Field(
        description="Assumed category lost-sale shares."
    )
    scenario_limits: ScenarioLimits = Field(description="Permitted scenario controls.")


class Meta(StrictModel):
    dataset: Dataset | None = Field(
        description="Loaded provenance, null before loading."
    )
    run: Run | None = Field(description="Current succeeded run, null before analytics.")
    parameters: Parameters = Field(
        description="Run model settings or documented defaults."
    )
