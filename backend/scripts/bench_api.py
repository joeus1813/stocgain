"""Measure all required Phase 4 endpoints against a live standard-data API."""

import argparse
import json
from math import ceil
from time import perf_counter

import httpx


def main() -> None:
    """Record first-call and twenty-request warm p95; fail on HTTP/schema errors."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000/api/v1")
    parser.add_argument("--output", default="docs/perf/raw/phase4_api.json")
    args = parser.parse_args()
    from pathlib import Path

    routes = [
        "/health",
        "/meta",
        "/filters",
        "/overview/summary",
        "/overview/risk-distribution",
        "/overview/risk-trend",
        "/overview/store-comparison",
        "/overview/category-heatmap",
        "/overview/top-products",
        "/recommendations",
        "/risk/positions",
        "/positions/1/1",
        "/positions/1/1/history",
        "/positions/1/1/projection",
        "/positions/1/1/purchase-orders",
        "/scenarios/evaluate",
    ]
    results = {}
    with httpx.Client(base_url=args.base, timeout=90) as client:
        for route in routes:
            samples = []
            for _ in range(21):
                started = perf_counter()
                response = (
                    client.post(
                        route,
                        json={
                            "assumptions": {
                                "demand_change_rate": 0.2,
                                "lead_time_change_days": 4,
                            }
                        },
                    )
                    if route == "/scenarios/evaluate"
                    else client.get(route)
                )
                response.raise_for_status()
                response.json()
                samples.append((perf_counter() - started) * 1000)
            results[route] = {
                "first_ms": round(samples[0], 3),
                "warm_p95_ms": round(sorted(samples[1:])[ceil(0.95 * 20) - 1], 3),
                "warm_min_ms": round(min(samples[1:]), 3),
                "requests": 21,
            }
            print(route, results[route], flush=True)
        neutral = client.post("/scenarios/evaluate", json={})
        neutral.raise_for_status()
        body = neutral.json()
        assert body["baseline"] == body["scenario"]
        assert body["positions_in_scope"] == 4800
        assert all(value == 0 for value in body["delta"]["absolute"].values())
        results["verification"] = {
            "neutral_positions": body["positions_in_scope"],
            "run_id": body["run_id"],
            "neutral_delta_zero": True,
        }
    Path(args.output).write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
