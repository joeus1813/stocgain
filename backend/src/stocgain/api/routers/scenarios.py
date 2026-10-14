"""Scenario Lab calculation endpoint; no writes or fabricated metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends

from stocgain.api.dependencies import Context, get_context
from stocgain.api.schemas.scenarios import ScenarioRequest, ScenarioResponse
from stocgain.services.scenarios import calculate

router = APIRouter(tags=["Scenarios"])


@router.post("/scenarios/evaluate", response_model=ScenarioResponse)
def evaluate_scenario(
    request: ScenarioRequest, ctx: Annotated[Context, Depends(get_context)]
) -> ScenarioResponse:
    """Recalculate risk and policy under bounded, reproducible assumptions."""
    return ScenarioResponse.model_validate(calculate(ctx, request))
