"""Storage/response precision boundary, matching docs/03 risk snapshot columns."""

from decimal import ROUND_HALF_UP, Decimal

from stocgain.analytics.types import Record

# Calculations remain full precision; apply only to completed position outputs.
RISK_SCALES = {
    **dict.fromkeys(
        (
            "avg_daily_demand_units",
            "daily_demand_std_units",
            "service_level",
            "stockout_probability",
        ),
        4,
    ),
    "days_of_cover": 1,
    "lost_sale_rate": 3,
    **dict.fromkeys(
        (
            "lead_time_mean_days",
            "lead_time_std_days",
            "protection_window_days",
            "lead_time_demand_mean_units",
            "lead_time_demand_std_units",
            "safety_stock_units",
            "binding_window_days",
            "binding_demand_mean_units",
            "binding_demand_std_units",
            "expected_shortage_units",
            "expected_lost_units",
            "revenue_at_risk_usd",
            "margin_at_risk_usd",
        ),
        2,
    ),
}


def snapshot_precision(row: Record) -> Record:
    """Serialize final risk values with PostgreSQL numeric half-away rounding."""
    return {
        key: float(
            Decimal(str(value)).quantize(
                Decimal(1).scaleb(-RISK_SCALES[key]), rounding=ROUND_HALF_UP
            )
        )
        if key in RISK_SCALES and value is not None
        else value
        for key, value in row.items()
    }
