"""Full precision planning exposure, docs/05 §7."""


def compute_exposure(
    shortage: float, lost_sale_rate: float, unit_price: float, unit_cost: float
) -> dict[str, float]:
    """Return estimated lost units and dollars; never multiply by risk twice."""
    lost = shortage * lost_sale_rate
    return {
        "lost_sale_rate": lost_sale_rate,
        "expected_lost_units": lost,
        "revenue_at_risk_usd": lost * unit_price,
        "margin_at_risk_usd": lost * (unit_price - unit_cost),
    }
