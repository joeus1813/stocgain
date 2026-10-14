"""Filtered and paginated risk monitor endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from stocgain.api.dependencies import Context, Filters, get_context, get_filters
from stocgain.api.schemas.overview import (
    ActionType,
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
