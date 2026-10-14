"""Explicit read-only acceptance checks for the loaded standard dataset."""

import json

import pytest
from sqlalchemy import create_engine, func, select, text

from stocgain.db.models import Base
from stocgain.quality.checks import validate
from stocgain.settings import REPOSITORY_ROOT, Settings

pytestmark = [pytest.mark.db, pytest.mark.slow]


def test_standard_dataset_acceptance():
    manifest = json.loads(
        (REPOSITORY_ROOT / "data/generated/standard/manifest.json").read_text()
    )
    engine = create_engine(Settings().database_url)
    try:
        with engine.connect() as connection:
            stored = (
                connection.execute(select(Base.metadata.tables["ops.dataset_manifest"]))
                .mappings()
                .one()
            )
            assert stored["preset"] == "standard"
            assert stored["content_checksum"] == manifest["content_checksum"]
            for name, expected in manifest["row_counts"].items():
                schema = "sim_truth" if name == "latent_demand" else "ops"
                table = Base.metadata.tables[f"{schema}.{name}"]
                assert (
                    connection.scalar(select(func.count()).select_from(table))
                    == expected
                )
            assert manifest["row_counts"]["stores"] == 12
            assert manifest["row_counts"]["products"] == 400
            assert all(
                manifest["row_counts"][n] == 864000
                for n in ("daily_sales", "inventory_snapshots", "latent_demand")
            )
            assert (
                connection.scalar(
                    text("SELECT count(DISTINCT sales_date) FROM ops.daily_sales")
                )
                == 180
            )
        results = validate(engine)
        assert len(results) == 18
        assert all(result.violations == 0 for result in results)
    finally:
        engine.dispose()


def test_standard_sql_layer():
    from datetime import timedelta

    from stocgain.db.sql_loader import SQL_ROOT, read_sql

    engine = create_engine(Settings().database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM analytics.mv_daily_position")
                )
                == 864000
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM analytics.v_inventory_reconciliation WHERE discrepancy<>0"
                    )
                )
                == 0
            )
            names = (
                connection.execute(
                    text(
                        "SELECT viewname FROM pg_views WHERE schemaname='analytics' UNION ALL SELECT matviewname FROM pg_matviews WHERE schemaname='analytics'"
                    )
                )
                .scalars()
                .all()
            )
            assert len(names) == 12
            for name in names:
                connection.exec_driver_sql(
                    f"SELECT * FROM analytics.{connection.dialect.identifier_preparer.quote(name)} LIMIT 1"
                ).all()
            for path in sorted((SQL_ROOT / "analyses").glob("*.sql")):
                connection.execute(text(read_sql(path))).all()
            as_of = connection.scalar(
                text("SELECT history_end_date FROM ops.dataset_manifest")
            ) - timedelta(days=30)
            for path in sorted((SQL_ROOT / "pipeline").glob("*.sql")):
                rows = (
                    connection.execute(
                        text(read_sql(path)), dict(as_of=as_of, history_days=56)
                    )
                    .mappings()
                    .all()
                )
                assert rows, path.name
                if path.name == "extract_daily_history.sql":
                    assert len(rows) == 56 * 4800
                    assert max(r["position_date"] for r in rows) == as_of
                if path.name == "extract_planned_promotions.sql":
                    assert all(
                        as_of < r["target_date"] <= as_of + timedelta(days=42)
                        for r in rows
                    )
    finally:
        engine.dispose()
