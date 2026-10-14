"""Filtered and paginated risk monitor endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from stocgain.api.dependencies import Context, Filters, get_context, get_filters
from stocgain.api.errors import ApiError
from stocgain.api.schemas.overview import (
    ActionType,
    RiskPosition,
    RiskPositions,
    RiskTier,
    SortBy,
    SortDirection,
)
from stocgain.services import overview as service

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/positions", response_model=RiskPositions)
def positions(
    ctx: Annotated[Context, Depends(get_context)],
    filters: Annotated[Filters, Depends(get_filters)],
    risk_tier: Annotated[
        list[RiskTier] | None, Query(description="Repeated risk tiers.")
    ] = None,
    action_type: Annotated[
        list[ActionType] | None, Query(description="Repeated action types.")
    ] = None,
    below_reorder_point: Annotated[
        bool | None, Query(description="Restrict by reorder-point status.")
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=64,
            description="SKU prefix or product name substring.",
        ),
    ] = None,
    sort_by: Annotated[
        SortBy, Query(description="Whitelisted sort column.")
    ] = "priority",
    sort_dir: Annotated[
        SortDirection | None, Query(description="Sort direction; defaults by column.")
    ] = None,
    page: Annotated[int, Query(ge=1, description="One-based page.")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=200, description="Positions per page.")
    ] = 50,
) -> RiskPositions:
    """Return stable risk pages with a summary of the whole filtered set."""
    return service.risk_positions(
        ctx,
        filters,
        risk_tier,
        action_type,
        below_reorder_point,
        q,
        sort_by,
        sort_dir,
        page,
        page_size,
    )


@router.get(
    "/positions/export.csv",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string"}}},
            "description": "Scoped simulated-data export with estimated column labels.",
        }
    },
)
def export_positions(
    ctx: Annotated[Context, Depends(get_context)],
    filters: Annotated[Filters, Depends(get_filters)],
    risk_tier: Annotated[list[RiskTier] | None, Query()] = None,
    action_type: Annotated[list[ActionType] | None, Query()] = None,
    below_reorder_point: bool | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    sort_by: SortBy = "priority",
    sort_dir: SortDirection | None = None,
) -> Response:
    """Export the complete scoped result, with simulation and estimate labels."""
    import csv
    import io

    result = service.risk_positions(
        ctx,
        filters,
        risk_tier,
        action_type,
        below_reorder_point,
        q,
        sort_by,
        sort_dir,
        1,
        10001,
    )
    if result.total_items > 10000:
        raise ApiError(
            400, "EXPORT_TOO_LARGE", "Narrow the filters to at most 10,000 positions."
        )
    estimate = {
        "avg_daily_demand_units",
        "days_of_cover",
        "next_receipt_date",
        "stockout_probability",
        "margin_at_risk_usd",
        "revenue_at_risk_usd",
        "recommended_order_units",
    }
    fields = list(RiskPosition.model_fields)
    output = io.StringIO()
    output.write(
        f"# stocgain simulated dataset · run {ctx.run['run_id']} · as of {ctx.run['as_of_date']} · values marked est_ are model estimates\n"
    )
    writer = csv.writer(output)
    writer.writerow([f"est_{f}" if f in estimate else f for f in fields])
    for item in result.items:
        values = item.model_dump(mode="json")
        # Prevent spreadsheet formula execution for arbitrary catalog strings.
        writer.writerow(
            [
                (
                    "'" + v
                    if isinstance(v, str) and v.startswith(("=", "+", "-", "@"))
                    else v
                )
                for v in (values[f] for f in fields)
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="stocgain_risk_positions_{ctx.run["as_of_date"]}_run{ctx.run["run_id"]}.csv"'
        },
    )
