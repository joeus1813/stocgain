"""One repeatable-read connection and one immutable run identity per request."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query, Request, Response
from sqlalchemy import Connection, text

from stocgain.api.errors import ApiError
from stocgain.db.sql_loader import read_sql


@dataclass
class Context:
    """Run-bound SQL repository context shared by request services."""

    connection: Connection
    run: dict[str, Any]

    @property
    def params(self) -> dict[str, Any]:
        """Common bound SQL values; current/prior IDs resolved once per request."""
        return {
            "run_id": self.run["run_id"],
            "as_of_date": self.run["as_of_date"],
            "prior_run_id": self.run.get("prior_run_id"),
        }

    def rows(
        self, name: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute named repository SQL with bound values."""
        path = name if name.endswith(".sql") else f"{name}.sql"
        return [
            dict(row)
            for row in self.connection.execute(
                text(read_sql(f"api/{path}")), {**self.params, **(params or {})}
            ).mappings()
        ]


def get_connection(request: Request) -> Iterator[Connection]:
    """Keep every statement in the request on one PostgreSQL snapshot."""
    with request.app.state.engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
            yield connection


def get_context(
    response: Response, connection: Annotated[Connection, Depends(get_connection)]
) -> Context:
    """Resolve latest successful current run or return explicit not-ready error."""
    run = connection.execute(text(read_sql("api/current_run.sql"))).mappings().first()
    if run is None:
        raise ApiError(
            503,
            "ANALYTICS_NOT_READY",
            "Analytics are not ready.",
            {"hint": "Run: make analytics"},
        )
    response.headers["X-stocgain-Run-Id"] = str(run["run_id"])
    response.headers["X-stocgain-As-Of"] = str(run["as_of_date"])
    return Context(connection, dict(run))


@dataclass(frozen=True)
class Filters:
    """Validated dimensional scope; None means unrestricted."""

    region_ids: list[int] | None = None
    store_ids: list[int] | None = None
    category_ids: list[int] | None = None
    supplier_ids: list[int] | None = None

    @property
    def params(self) -> dict[str, Any]:
        """Translate public singular query names to bound SQL arrays."""
        return {
            "region_ids": self.region_ids,
            "store_ids": self.store_ids,
            "category_ids": self.category_ids,
            "supplier_ids": self.supplier_ids,
        }


def validate_ids(connection: Connection, param: str, values: list[int] | None) -> None:
    """Validate IDs against an explicit table/column whitelist."""
    if values is None:
        return
    names = {
        "store_id": "stores",
        "region_id": "regions",
        "category_id": "product_categories",
        "supplier_id": "suppliers",
    }
    if param not in names:
        raise ValueError("Unsupported filter")
    found = set(connection.scalars(text(f"SELECT {param} FROM ops.{names[param]}")))
    unknown = sorted(set(values) - found)
    if unknown:
        raise ApiError(
            422,
            "UNKNOWN_FILTER_VALUE",
            "Unknown filter IDs.",
            {"param": param, "values": unknown},
        )


def get_filters(
    ctx: Annotated[Context, Depends(get_context)],
    region_id: Annotated[list[int] | None, Query()] = None,
    store_id: Annotated[list[int] | None, Query()] = None,
    category_id: Annotated[list[int] | None, Query()] = None,
    supplier_id: Annotated[list[int] | None, Query()] = None,
) -> Filters:
    """Read repeated query filters and reject unknown dimension values."""
    for name, values in (
        ("region_id", region_id),
        ("store_id", store_id),
        ("category_id", category_id),
        ("supplier_id", supplier_id),
    ):
        validate_ids(ctx.connection, name, values)
    return Filters(region_id, store_id, category_id, supplier_id)
