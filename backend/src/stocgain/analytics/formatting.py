"""Shared explanation/presentation number rules, docs/07 §4.6."""

from decimal import ROUND_HALF_UP, Decimal


def format_number(kind: str, value: float | None) -> str:
    """Format counts, days, USD or 0–1 ratios for human-readable explanations."""
    if value is None:
        return "—"
    if kind == "probability":
        if 0 < value < 0.001:
            return "<0.1%"
        if 0.999 < value < 1:
            return ">99.9%"
        kind = "rate"
    digits = 0 if kind in ("count", "money") else 2 if kind == "price" else 1
    scaled = Decimal(str(value)) * (100 if kind == "rate" else 1)
    rounded = scaled.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    rendered = f"{rounded:,.{digits}f}"
    if kind in ("money", "price"):
        return "$" + rendered
    if kind == "rate":
        return rendered + "%"
    if kind == "days":
        return rendered + " days"
    return rendered
