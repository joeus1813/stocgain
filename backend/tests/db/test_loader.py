"""Transactional loading, checksum verification and refusal to overwrite data."""

import csv
import json

import pytest
from sqlalchemy import text

from stocgain.generator.config import load_config
from stocgain.generator.simulation import simulate
from stocgain.generator.writer import combined_checksum, file_checksums, write_dataset
from stocgain.loader.copy_loader import inspect_dataset, load_dataset

pytestmark = pytest.mark.db


@pytest.fixture
def generated(tmp_path):
    path = tmp_path / "data"
    write_dataset(simulate(load_config("small"), 42), path)
    return path


def test_loader_checksum_and_header_verification(generated):
    path = generated / "daily_sales.csv"
    path.write_text(path.read_text() + "bad,row\n")
    with pytest.raises(ValueError, match="checksum"):
        inspect_dataset(generated)


def test_loader_refuses_unapproved_replacement(loaded_small_db, tmp_path):
    path = tmp_path / "other"
    write_dataset(simulate(load_config("small"), 43), path)
    with pytest.raises(ValueError, match="contains data"):
        load_dataset(loaded_small_db, path)


def test_loader_rolls_back_quality_failure(loaded_small_db, generated):
    path = generated / "inventory_snapshots.csv"
    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    rows[1][-1] = str(int(rows[1][-1]) + 1)
    with path.open("w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)
    manifest = json.loads((generated / "manifest.json").read_text())
    manifest["file_checksums"] = file_checksums(generated)
    manifest["content_checksum"] = combined_checksum(manifest["file_checksums"])
    (generated / "manifest.json").write_text(json.dumps(manifest))
    with loaded_small_db.connect() as connection:
        before = connection.execute(
            text("SELECT content_checksum,loaded_at FROM ops.dataset_manifest")
        ).one()
    with pytest.raises(ValueError, match="Data quality failed"):
        load_dataset(loaded_small_db, generated, replace=True)
    with loaded_small_db.connect() as connection:
        after = connection.execute(
            text("SELECT content_checksum,loaded_at FROM ops.dataset_manifest")
        ).one()
        assert after == before
        assert connection.scalar(text("SELECT count(*) FROM ops.daily_sales")) == 21600


def test_loader_identical_dataset_is_idempotent(loaded_small_db, generated):
    with loaded_small_db.connect() as connection:
        before = connection.scalar(text("SELECT loaded_at FROM ops.dataset_manifest"))
    results = load_dataset(loaded_small_db, generated)
    assert not any(r.violations for r in results)
    with loaded_small_db.connect() as connection:
        assert (
            connection.scalar(text("SELECT loaded_at FROM ops.dataset_manifest"))
            == before
        )
