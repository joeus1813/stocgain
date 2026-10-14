"""Process liveness with a real database connectivity check (docs/08 §3.1)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Engine

from stocgain import __version__
from stocgain.api.deps import get_engine
from stocgain.db.engine import check_database

router = APIRouter()


class HealthResponse(BaseModel):
    """Connectivity state; analytics are not implemented in Phase 0."""

    status: Literal["ok"] = "ok"
    database: Literal["ok", "unavailable"]
    analytics_ready: bool = False
    current_run_id: int | None = None
    version: str = __version__


@router.get("/health", response_model=HealthResponse)
def health(engine: Annotated[Engine, Depends(get_engine)]) -> HealthResponse:
    """Return process status and database availability; always HTTP 200."""
    return HealthResponse(database="ok" if check_database(engine) else "unavailable")
