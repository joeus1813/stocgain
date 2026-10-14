"""Process liveness and actual PostgreSQL/model readiness (docs/08 §3.1)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from stocgain import __version__
from stocgain.api.deps import get_engine
from stocgain.api.schemas.common import Count, StrictModel
from stocgain.db.engine import check_database
from stocgain.db.sql_loader import read_sql

router = APIRouter()


class HealthResponse(StrictModel):
    """Process, database and current successful analytics availability."""

    status: Literal["ok"] = Field(default="ok", description="API process liveness.")
    database: Literal["ok", "unavailable"] = Field(
        description="Actual PostgreSQL connectivity."
    )
    analytics_ready: bool = Field(
        default=False, description="Whether a succeeded current analytics run exists."
    )
    current_run_id: Count | None = Field(
        default=None, description="Current successful run ID, null if not ready."
    )
    version: str = Field(default=__version__, description="Application version.")


@router.get("/health", response_model=HealthResponse)
def health(engine: Annotated[Engine, Depends(get_engine)]) -> HealthResponse:
    """Always return HTTP 200; expose dependencies as explicit status fields."""
    if not check_database(engine):
        return HealthResponse(database="unavailable")
    try:
        with engine.connect() as connection:
            run = (
                connection.execute(text(read_sql("api/current_run.sql")))
                .mappings()
                .first()
            )
        return HealthResponse(
            database="ok",
            analytics_ready=run is not None,
            current_run_id=run["run_id"] if run else None,
        )
    except SQLAlchemyError:
        return HealthResponse(database="unavailable")
