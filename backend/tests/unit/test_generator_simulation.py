"""Generator acceptance invariants from docs/06 §11."""

from pathlib import Path

import numpy as np
import pytest

from stocgain.generator.config import load_config
from stocgain.generator.simulation import simulate
from stocgain.generator.writer import write_dataset

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def small():
    return simulate(load_config("small"), 42)


def test_generator_dense_and_balanced(small):
    for table in ("daily_sales", "inventory_snapshots", "latent_demand"):
        assert len(small.tables[table]) == 21600
    d = small.diagnostics
    assert np.array_equal(
        d["closing"], d["opening"] + d["received"] - d["sold"] + d["adjusted"]
    )
    assert np.array_equal(d["opening"][1:], d["closing"][:-1])
    assert np.min(d["closing"]) >= 0
    assert np.min(d["opening"]) >= 0
    assert np.all(d["sold"] <= d["opening"] + d["received"])
    assert np.all(d["sold"] <= d["latent"])
    assert np.mean(d["sold"] == d["opening"] + d["received"]) >= 0.01


def test_generator_determinism(small, tmp_path: Path):
    first = write_dataset(small, tmp_path / "first")
    second = write_dataset(simulate(load_config("small"), 42), tmp_path / "second")
    other = write_dataset(simulate(load_config("small"), 43), tmp_path / "other")
    assert first["content_checksum"] == second["content_checksum"]
    assert first["content_checksum"] != other["content_checksum"]
    for p in (tmp_path / "first").glob("*.csv"):
        assert p.read_bytes() == (tmp_path / "second" / p.name).read_bytes()


def test_generator_fulfillment_and_events(small):
    receipts = small.tables["inventory_receipts"]
    lines = small.tables["purchase_order_lines"]
    assert max(r[2] for r in receipts) <= small.config.history_end
    received = {}
    shipments = {}
    for _, line, _, qty in receipts:
        received[line] = received.get(line, 0) + qty
        shipments[line] = shipments.get(line, 0) + 1
    assert any(shipments.get(line[0], 0) > 1 for line in lines)
    assert any(line[5] > 0 for line in lines)
    assert any(line[4] - line[5] > received.get(line[0], 0) for line in lines)
    assert all(received.get(line[0], 0) + line[5] <= line[4] for line in lines)
    assert any(p[4] > small.config.history_end for p in small.tables["promotions"])
    assert small.diagnostics["storm_expected_ratio"] > 1.8
    assert small.diagnostics["demo_pl_on_time"] < 0.8


def test_generator_catalog_relationships(small):
    tables = small.tables
    supplier_categories = {s[0]: s[3] for s in tables["suppliers"]}
    products = {p[0]: p for p in tables["products"]}
    sourcing = {(p, s) for p, s, *_ in tables["product_suppliers"]}
    orders = {p[0]: p for p in tables["purchase_orders"]}
    for p in products.values():
        assert p[6] > p[7] > 0
        assert round(p[6] * 100) % 100 in (97, 98, 99)
        assert (
            sum(row[0] == p[0] and row[2] for row in tables["product_suppliers"]) == 1
        )
    for p, s, _, pack, moq in tables["product_suppliers"]:
        assert products[p][3] == supplier_categories[s]
        assert moq % pack == 0
    for line in tables["purchase_order_lines"]:
        assert (line[3], orders[line[1]][2]) in sourcing
    calendar = {r[0] for r in tables["calendar"]}
    assert all(p[4] in calendar and p[5] > p[4] for p in orders.values())
    assert all(r[2] in calendar for r in tables["inventory_receipts"])


def test_generator_promotions_do_not_overlap(small):
    promos = {r[0]: r for r in small.tables["promotions"]}
    memberships = {
        pid: {r[1] for r in small.tables["promotion_products"] if r[0] == pid}
        for pid in promos
    }
    for pid, p in promos.items():
        for qid, q in promos.items():
            if (
                pid < qid
                and p[4] <= q[5]
                and q[4] <= p[5]
                and (p[3] is None or q[3] is None or p[3] == q[3])
            ):
                assert not memberships[pid] & memberships[qid]
    categories = {p[0]: p[3] for p in small.tables["products"]}
    future = {
        categories[product]
        for pid, product in small.tables["promotion_products"]
        if promos[pid][3] is None
        and str(promos[pid][4]) >= "2026-10-01"
        and str(promos[pid][4]) <= "2026-10-14"
    }
    assert {4, 7} <= future


def test_generator_receipts_follow_orders(small):
    orders = {p[0]: p for p in small.tables["purchase_orders"]}
    lines = {p[0]: p for p in small.tables["purchase_order_lines"]}
    for _, line, day, _ in small.tables["inventory_receipts"]:
        assert day > orders[lines[line][1]][4]


def test_generator_manifest_headers_and_money(small, tmp_path):
    import csv

    from stocgain.db.models import Base
    from stocgain.generator.writer import combined_checksum, file_checksums

    manifest = write_dataset(small, tmp_path / "csv")
    assert manifest["data_origin"] == "synthetic"
    assert manifest["content_checksum"] == combined_checksum(
        file_checksums(tmp_path / "csv")
    )
    for name in small.tables:
        table = Base.metadata.tables[
            f"{'sim_truth' if name == 'latent_demand' else 'ops'}.{name}"
        ]
        with (tmp_path / "csv" / f"{name}.csv").open() as f:
            reader = csv.reader(f)
            assert next(reader) == list(table.columns.keys())
    with (tmp_path / "csv/daily_sales.csv").open() as f:
        rows = csv.DictReader(f)
        assert all(
            len(r["net_sales_amount"].split(".")[-1]) == 2
            and len(r["cogs_amount"].split(".")[-1]) == 2
            for r in rows
        )


def test_generator_standard_price_points():
    from stocgain.generator.catalog import build_catalog

    catalog = build_catalog(load_config("standard"), 42)
    for p in catalog.tables["products"]:
        assert round(p[6] * 100) % 100 in (97, 98, 99), p[:2]


def test_generator_reserved_supplier_names_remain_unique():
    from stocgain.generator.catalog import build_catalog

    suppliers = build_catalog(load_config("standard"), 89).tables["suppliers"]
    names = [row[2] for row in suppliers]
    assert len(names) == len(set(names))
