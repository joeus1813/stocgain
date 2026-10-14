"""Thin position routes; all calculation and SQL assembly live in services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from stocgain.api.dependencies import Context, get_context
from stocgain.api.schemas.positions import (
    PositionDetail,
    PositionHistory,
    PositionOrders,
    PositionProjection,
)
from stocgain.services import positions

router = APIRouter(prefix="/positions", tags=["positions"])
ContextDependency = Annotated[Context, Depends(get_context)]
Identifier = Annotated[int, Path(ge=1, description="Positive database identifier.")]


@router.get("/{store_id}/{product_id}", response_model=PositionDetail)
def detail(
    store_id: Identifier, product_id: Identifier, ctx: ContextDependency
) -> PositionDetail:
    """Inspect the stored forecast, risk, policy and recommendation for a position."""
    return PositionDetail.model_validate(positions.detail(ctx, store_id, product_id))


@router.get("/{store_id}/{product_id}/history", response_model=PositionHistory)
def history(
    store_id: Identifier,
    product_id: Identifier,
    ctx: ContextDependency,
    days: Annotated[
        int,
        Query(ge=7, le=180, description="Historical days ending at the model cutoff."),
    ] = 56,
) -> PositionHistory:
    """Read observed inventory/sales history and the next 28 forecast days."""
    return PositionHistory.model_validate(
        positions.history(ctx, store_id, product_id, days)
    )


@router.get("/{store_id}/{product_id}/projection", response_model=PositionProjection)
def projection(
    store_id: Identifier,
    product_id: Identifier,
    ctx: ContextDependency,
    history_days: Annotated[
        int, Query(ge=7, le=56, description="Observed inventory days to include.")
    ] = 28,
    horizon_days: Annotated[
        int, Query(ge=7, le=42, description="Future inventory days to include.")
    ] = 28,
) -> PositionProjection:
    """Project inventory from full-precision model inputs with an approximate band."""
    return PositionProjection.model_validate(
        positions.projection(ctx, store_id, product_id, history_days, horizon_days)
    )


@router.get("/{store_id}/{product_id}/purchase-orders", response_model=PositionOrders)
def purchase_orders(
    store_id: Identifier,
    product_id: Identifier,
    ctx: ContextDependency,
    recent_received_limit: Annotated[
        int,
        Query(
            ge=0,
            le=20,
            description="Maximum completed purchase-order lines to include.",
        ),
    ] = 5,
) -> PositionOrders:
    """Read open and recently completed purchase-order lines as of the run cutoff."""
    return PositionOrders.model_validate(
        positions.purchase_orders(ctx, store_id, product_id, recent_received_limit)
    )
