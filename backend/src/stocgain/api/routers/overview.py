"""P0 overview endpoints backed by run-scoped PostgreSQL results."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from stocgain.api.dependencies import Context, Filters, get_context, get_filters
from stocgain.api.schemas.overview import (
    CategoryHeatmap,
    OverviewSummary,
    RiskDistribution,
    RiskTrend,
    StoreComparison,
    TopProducts,
)
from stocgain.services import overview as service

router = APIRouter(prefix="/overview", tags=["overview"])
Ctx = Annotated[Context, Depends(get_context)]
Scope = Annotated[Filters, Depends(get_filters)]


@router.get("/summary", response_model=OverviewSummary)
def summary(ctx: Ctx, filters: Scope) -> OverviewSummary:
    """Summarize inventory risk and observed operational KPIs."""
    return service.summary(ctx, filters)


@router.get("/risk-distribution", response_model=RiskDistribution)
def risk_distribution(ctx: Ctx, filters: Scope) -> RiskDistribution:
    """Count all four risk tiers, including empty tiers."""
    return service.distribution(ctx, filters)


@router.get("/risk-trend", response_model=RiskTrend)
def risk_trend(
    ctx: Ctx,
    filters: Scope,
    weeks: Annotated[int, Query(ge=1, le=26, description="Weeks to include.")] = 13,
) -> RiskTrend:
    """Return filtered risk across available historical run dates."""
    return service.trend(ctx, filters, weeks)


@router.get("/store-comparison", response_model=StoreComparison)
def store_comparison(ctx: Ctx, filters: Scope) -> StoreComparison:
    """Compare stores, ignoring the selected store filter."""
    return service.stores(ctx, filters)


@router.get("/category-heatmap", response_model=CategoryHeatmap)
def category_heatmap(ctx: Ctx, filters: Scope) -> CategoryHeatmap:
    """Return a dense store-category risk matrix."""
    return service.heatmap(ctx, filters)


@router.get("/top-products", response_model=TopProducts)
def top_products(
    ctx: Ctx,
    filters: Scope,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum products.")] = 8,
) -> TopProducts:
    """Return products with the highest estimated margin at risk."""
    return service.top_products(ctx, filters, limit)
