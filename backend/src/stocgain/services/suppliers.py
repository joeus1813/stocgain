"""Read-only supplier evidence and backtest presentation, docs/08 §3.18–21."""

from collections import Counter
from datetime import timedelta
from statistics import mean, stdev
from typing import Any

from stocgain.api.dependencies import Context, Filters
from stocgain.api.errors import ApiError
from stocgain.api.schemas import suppliers as schema

DISCLAIMER = "Flags indicate association between supplier delivery performance and at-risk positions; they do not establish causation."


def supplier_rows(ctx: Context, filters: Filters) -> list[dict[str, Any]]:
    """Return scoped, point-in-time supplier performance with aggregation evidence."""
    return ctx.rows("supplier_list", filters.params)


def listing(
    ctx: Context, filters: Filters, flagged: bool, sort: str, direction: str
) -> schema.SupplierList:
    """Sort the small supplier set using a router-validated column."""
    rows = supplier_rows(ctx, filters)
    items = [
        schema.SupplierItem.model_validate(
            {
                k: (bool(r[k]) if k == "review_flag" else r[k])
                for k in schema.SupplierItem.model_fields
            }
        )
        for r in rows
        if not flagged or r["review_flag"]
    ]
    present = [r for r in items if getattr(r, sort) is not None]
    absent = [r for r in items if getattr(r, sort) is None]
    present.sort(
        key=lambda r: (getattr(r, sort), r.supplier_id), reverse=direction == "desc"
    )
    return schema.SupplierList(items=present + absent, disclaimer=DISCLAIMER)


def summary(ctx: Context, filters: Filters) -> dict[str, Any]:
    """Use PO-weighted rates and means, never an average of supplier rates."""
    rows = supplier_rows(ctx, filters)
    due = sum(r["pos_due_90d"] for r in rows)
    received = sum(r["received_180d"] or 0 for r in rows)
    return dict(
        suppliers=len(rows),
        flagged_suppliers=sum(bool(r["review_flag"]) for r in rows),
        on_time_rate_90d=sum(r["on_time_pos_90d"] for r in rows) / due if due else None,
        mean_lead_time_days=sum(r["lead_days_sum"] or 0 for r in rows) / received
        if received
        else None,
        overdue_open_pos=sum(r["overdue_open_pos"] for r in rows),
    )


def detail(ctx: Context, supplier_id: int) -> dict[str, Any]:
    """Group cutoff-bounded delivery evidence into weeks, bins and lanes."""
    rows = supplier_rows(ctx, Filters(supplier_ids=[supplier_id]))
    if not rows:
        raise ApiError(404, "SUPPLIER_NOT_FOUND", "Supplier not found.")
    row = rows[0]
    row["review_flag"] = bool(row["review_flag"])
    params = {**Filters().params, "supplier_id": supplier_id}
    orders = ctx.rows("supplier_orders", params)
    lanes = ctx.rows("supplier_lanes", params)
    cutoff = ctx.run["as_of_date"]
    recent = [
        p
        for p in orders
        if p["first_receipt_date"]
        and p["first_receipt_date"] > cutoff - timedelta(days=180)
    ]

    def rate(po: list[dict[str, Any]]) -> float | None:
        return (
            sum(
                p["first_receipt_date"] is not None
                and p["first_receipt_date"] <= p["promised_delivery_date"]
                for p in po
            )
            / len(po)
            if po
            else None
        )

    weeks = []
    start = cutoff - timedelta(days=cutoff.weekday(), weeks=25)
    for i in range(26):
        day = start + timedelta(weeks=i)
        due = [
            p
            for p in orders
            if day
            <= p["promised_delivery_date"]
            <= min(day + timedelta(days=6), cutoff)
        ]
        weeks.append(
            dict(week_start_date=day, pos_due=len(due), on_time_rate=rate(due))
        )
    lane_rows = []
    for lane in lanes:
        po = [p for p in orders if p["store_id"] == lane["store_id"]]
        leads = [
            p["lead_time_days"] for p in recent if p["store_id"] == lane["store_id"]
        ]
        due = [
            p
            for p in po
            if cutoff - timedelta(days=89) <= p["promised_delivery_date"] <= cutoff
        ]
        lane_rows.append(
            dict(
                store_id=lane["store_id"],
                store_code=lane["store_code"],
                pos_received_180d=len(leads),
                on_time_rate=rate(due),
                mean_lead_time_days=mean(leads) if leads else None,
                std_lead_time_days=stdev(leads) if len(leads) > 1 else None,
                overdue_open_pos=sum(
                    p["first_receipt_date"] is None
                    and p["promised_delivery_date"] <= cutoff
                    for p in po
                ),
            )
        )
    return dict(
        supplier={k: row[k] for k in schema.SupplierIdentity.model_fields},
        performance={k: row[k] for k in schema.SupplierPerformance.model_fields},
        weekly_on_time=weeks,
        lead_time_histogram=[
            dict(lead_time_days=k, pos=v)
            for k, v in sorted(Counter(p["lead_time_days"] for p in recent).items())
        ],
        contract_lead_time_days_avg=mean(
            lane["contract_lead_time_days"] for lane in lanes
        )
        if lanes
        else None,
        lanes=lane_rows,
        exposed_positions=ctx.rows("supplier_exposure", params),
        disclaimer=DISCLAIMER,
    )


def evaluation(
    ctx: Context, segment_type: str, evaluation_basis: str | None
) -> dict[str, Any]:
    """Expose only persisted evaluation outputs; no access to simulation truth."""
    rows = ctx.rows(
        "forecast_evaluation",
        dict(segment_type=segment_type, evaluation_basis=evaluation_basis),
    )
    return dict(
        run_id=ctx.run["run_id"],
        first_origin_date=min((r["first_origin_date"] for r in rows), default=None),
        last_origin_date=max((r["last_origin_date"] for r in rows), default=None),
        n_origins=max((r["n_origins"] for r in rows), default=0),
        rows=[{k: r[k] for k in schema.EvaluationRow.model_fields} for r in rows],
        notes={
            "observed_in_stock": "Compares forecasts with observed sales on in-stock days. Censored days are excluded because true demand is unknown.",
            "simulated_latent": "Simulation-only check against hidden true demand. A real retailer cannot observe this basis.",
        },
    )
