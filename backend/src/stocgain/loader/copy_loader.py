"""Checksum-verified, transactional COPY loading (docs/03 §12)."""

import csv
import json
from pathlib import Path
from typing import Any, cast

import psycopg
from sqlalchemy import Engine, select, text

from stocgain.db.models import Base
from stocgain.db.views import apply_views_connection
from stocgain.generator.writer import combined_checksum, file_checksums
from stocgain.quality.checks import CheckResult, check_connection

LOAD_ORDER = (
    "regions",
    "product_categories",
    "stores",
    "suppliers",
    "products",
    "product_suppliers",
    "supplier_store_lanes",
    "calendar",
    "promotions",
    "promotion_products",
    "purchase_orders",
    "purchase_order_lines",
    "inventory_receipts",
    "inventory_adjustments",
    "daily_sales",
    "inventory_snapshots",
    "latent_demand",
)


def inspect_dataset(path: Path) -> dict[str, Any]:
    """Verify every file and column before opening a database transaction."""
    manifest: dict[str, Any] = json.loads((path / "manifest.json").read_text())
    hashes = file_checksums(path)
    if set(hashes) != {f"{name}.csv" for name in LOAD_ORDER}:
        raise ValueError("Unexpected or missing dataset CSV files")
    if (
        hashes != manifest["file_checksums"]
        or combined_checksum(hashes) != manifest["content_checksum"]
    ):
        raise ValueError("Dataset checksum mismatch")
    if manifest["data_origin"] != "synthetic":
        raise ValueError("Expected synthetic dataset provenance")
    for name in LOAD_ORDER:
        table = Base.metadata.tables[
            f"{'sim_truth' if name == 'latent_demand' else 'ops'}.{name}"
        ]
        with (path / f"{name}.csv").open(newline="") as f:
            reader = csv.reader(f)
            if next(reader) != list(table.columns.keys()):
                raise ValueError(f"CSV header mismatch: {name}")
            if sum(1 for _ in reader) != manifest["row_counts"][name]:
                raise ValueError(f"CSV row count mismatch: {name}")
    return manifest


def load_dataset(
    engine: Engine, path: Path, *, replace: bool = False
) -> list[CheckResult]:
    """Load and validate atomically; refuse to replace existing data by default."""
    manifest = inspect_dataset(path)
    with engine.begin() as connection:
        # Serialize cooperating loaders, so emptiness checks and COPY cannot race.
        connection.execute(text("SELECT pg_advisory_xact_lock(7319051)"))
        existing = connection.scalar(
            select(Base.metadata.tables["ops.dataset_manifest"].c.content_checksum)
        )
        if existing == manifest["content_checksum"]:
            return check_connection(connection)
        populated = any(
            connection.scalar(select(table).limit(1)) is not None
            for table in Base.metadata.sorted_tables
        )
        if populated and not replace:
            raise ValueError(
                "Database contains data; use --replace only with explicit approval"
            )
        if populated:
            tables = ", ".join(
                f"{t.schema}.{t.name}" for t in Base.metadata.sorted_tables
            )
            connection.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY")
        raw = cast(psycopg.Connection[Any], connection.connection.driver_connection)
        with raw.cursor() as cursor:
            for name in LOAD_ORDER:
                table = Base.metadata.tables[
                    f"{'sim_truth' if name == 'latent_demand' else 'ops'}.{name}"
                ]
                columns = ",".join(table.columns.keys())
                with (
                    cursor.copy(
                        f"COPY {table.schema}.{name} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                    ) as copy,
                    (path / f"{name}.csv").open("rb") as f,
                ):
                    while chunk := f.read(1024 * 1024):
                        copy.write(chunk)
        table = Base.metadata.tables["ops.dataset_manifest"]
        values = {
            column.name: manifest[column.name]
            for column in table.columns
            if column.name not in ("dataset_id", "loaded_at")
        }
        connection.execute(table.insert().values(dataset_id=1, **values))
        apply_views_connection(connection)
        for table in Base.metadata.sorted_tables:
            connection.exec_driver_sql(f"ANALYZE {table.schema}.{table.name}")
        results = check_connection(connection)
        errors = [r for r in results if r.severity == "error" and r.violations]
        if errors:
            raise ValueError(f"Data quality failed; transaction rolled back: {errors}")
        return results
