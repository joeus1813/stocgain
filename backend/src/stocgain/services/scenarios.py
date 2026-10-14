"""Validated scenario orchestration with a run-scoped full-precision cache."""

from time import perf_counter
from typing import Any

from stocgain.analytics.scenario import ScenarioParameters, evaluate
from stocgain.api.dependencies import Context, validate_ids
from stocgain.api.schemas.scenarios import ScenarioRequest
from stocgain.services.model_cache import get_baseline


def calculate(ctx: Context, request: ScenarioRequest) -> dict[str, Any]:
    """Compute actual baseline/scenario results without writing database rows."""
    started = perf_counter()
    scope = request.scope.model_dump()
    for field, values in scope.items():
        validate_ids(ctx.connection, field[:-1], values)
    controls: dict[str, Any] = {
        **request.assumptions.model_dump(),
        **{
            key: tuple(value) if value is not None else None
            for key, value in scope.items()
        },
    }
    parameters = ScenarioParameters(**controls)
    result = evaluate(*get_baseline(ctx), parameters)
    result.pop("position_results")
    for name in ("baseline", "scenario"):
        result[name].pop("positions_in_scope", None)
    for name in ("absolute", "relative"):
        result["delta"][name].pop("positions_in_scope", None)
    result.update(
        run_id=ctx.run["run_id"], computation_ms=(perf_counter() - started) * 1000
    )
    return result
