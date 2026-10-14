"""Thin supplier/evaluation endpoints for Phase 6 and requested Methodology UI."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path

from stocgain.api.dependencies import Context, Filters, get_context, get_filters
from stocgain.api.schemas import suppliers as schema
from stocgain.services import suppliers as service

router = APIRouter(tags=["suppliers"])
Ctx = Annotated[Context, Depends(get_context)]
Scope = Annotated[Filters, Depends(get_filters)]


@router.get("/suppliers/summary", response_model=schema.SupplierSummary)
def summary(ctx: Ctx, filters: Scope) -> schema.SupplierSummary:
    """Return weighted supplier delivery KPIs."""
    return schema.SupplierSummary.model_validate(service.summary(ctx, filters))


@router.get("/suppliers", response_model=schema.SupplierList)
def listing(
    ctx: Ctx,
    filters: Scope,
    flagged_only: bool = False,
    sort_by: Literal[
        "reliability_rank",
        "on_time_rate",
        "lead_time_cv",
        "margin_at_risk_usd",
        "at_risk_positions",
    ] = "reliability_rank",
    sort_dir: Literal["asc", "desc"] = "asc",
) -> schema.SupplierList:
    """List scope-aware supplier delivery performance."""
    return service.listing(ctx, filters, flagged_only, sort_by, sort_dir)


@router.get("/suppliers/{supplier_id}", response_model=schema.SupplierDetail)
def detail(supplier_id: Annotated[int, Path(ge=1)], ctx: Ctx) -> schema.SupplierDetail:
    """Inspect historical delivery evidence and current exposed positions."""
    return schema.SupplierDetail.model_validate(service.detail(ctx, supplier_id))


@router.get("/forecasts/evaluation", response_model=schema.Evaluation)
def evaluation(
    ctx: Ctx,
    segment_type: Literal[
        "overall", "horizon_bucket", "velocity_class", "demand_pattern"
    ] = "horizon_bucket",
    evaluation_basis: Literal["observed_in_stock", "simulated_latent"] | None = None,
) -> schema.Evaluation:
    """Read stored leakage-free backtest results."""
    return schema.Evaluation.model_validate(
        service.evaluation(ctx, segment_type, evaluation_basis)
    )
