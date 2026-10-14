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
