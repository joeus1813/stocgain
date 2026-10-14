"""Measure Phase 2 SQL on the existing standard database, without model writes."""

import json
from time import perf_counter

from sqlalchemy import text

from stocgain.db.engine import create_db_engine
from stocgain.db.sql_loader import SQL_ROOT, read_sql
from stocgain.settings import REPOSITORY_ROOT, Settings


def main() -> None:
    """Run each workload three times and retain actual warm plan evidence."""
    engine = create_db_engine(Settings())
    output = REPOSITORY_ROOT / "docs/perf/raw"
    output.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {}
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
            preset = connection.scalar(text("SELECT preset FROM ops.dataset_manifest"))
            if preset != "standard":
                raise ValueError("Standard dataset required; no data will be replaced")
            start = perf_counter()
            connection.execute(
                text("REFRESH MATERIALIZED VIEW analytics.mv_daily_position")
            )
            evidence["refresh_seconds"] = perf_counter() - start
            connection.execute(text("ANALYZE analytics.mv_daily_position"))
            evidence["model_runs"] = connection.scalar(
                text("SELECT count(*) FROM analytics.analytics_runs")
            )
            for path in sorted((SQL_ROOT / "analyses").glob("*.sql")):
                start = perf_counter()
                result = connection.execute(text(read_sql(path)))
                columns = list(result.keys())
                rows = result.mappings().all()
                evidence[path.stem] = dict(
                    rows=len(rows),
                    seconds=perf_counter() - start,
                    columns=columns,
                    examples=[dict(r) for r in rows[:2]],
                )
            for path in sorted((SQL_ROOT / "explain").glob("*.sql")):
                for _ in range(3):
                    plan = connection.execute(text(read_sql(path))).scalars().all()
                (output / f"{path.stem}.txt").write_text("\n".join(plan) + "\n")
                evidence[path.stem] = [
                    line for line in plan if "Time:" in line or "Buffers:" in line
                ][:4]
                print(path.stem, plan[-1], flush=True)
    finally:
        engine.dispose()
    (output / "phase2_results.json").write_text(
        json.dumps(evidence, default=str, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
