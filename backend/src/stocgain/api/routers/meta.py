"""Dataset and dimension metadata; available before the first analytics run."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text

from stocgain.api.dependencies import get_connection
from stocgain.api.schemas.meta import FiltersResponse, Meta
from stocgain.db.sql_loader import read_sql
from stocgain.services.meta import metadata

router = APIRouter(tags=["Metadata"])


@router.get("/meta", response_model=Meta)
def get_meta(connection: Annotated[Connection, Depends(get_connection)]) -> Meta:
    """Read provenance and actual persisted model settings."""
    return Meta.model_validate(metadata(connection))


@router.get("/filters", response_model=FiltersResponse)
def get_filters(
    connection: Annotated[Connection, Depends(get_connection)],
) -> FiltersResponse:
    """Read sorted identifiers for filter controls."""
    return FiltersResponse.model_validate(
        dict(connection.execute(text(read_sql("api/filters.sql"))).mappings().one())
    )
