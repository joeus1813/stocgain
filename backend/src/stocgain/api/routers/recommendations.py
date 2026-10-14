"""Stored, read-only replenishment suggestions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from stocgain.api.dependencies import Context, Filters, get_context, get_filters
from stocgain.api.schemas.overview import Recommendations, RecommendedAction
from stocgain.services import overview as service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=Recommendations)
def recommendations(
    ctx: Annotated[Context, Depends(get_context)],
    filters: Annotated[Filters, Depends(get_filters)],
    action_type: Annotated[
        list[RecommendedAction] | None,
        Query(description="Repeated actionable recommendation types."),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum recommendations.")
    ] = 10,
) -> Recommendations:
    """Preserve global priority rank while filtering stored suggestions."""
    return service.recommendations(ctx, filters, action_type, limit)
