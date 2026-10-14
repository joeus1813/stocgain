"""Execute every DQ SQL file and count actual violations (docs/03 §10)."""

from dataclasses import dataclass

from sqlalchemy import Connection, Engine, text

from stocgain.db.sql_loader import SQL_ROOT


@dataclass(frozen=True)
class CheckResult:
    """Observed violation count; warnings are reported without hiding errors."""

    check: str
    severity: str
    violations: int


def check_connection(connection: Connection) -> list[CheckResult]:
    """Run checks within the caller's transaction, including uncommitted loads."""
    connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
    results = []
    for path in sorted((SQL_ROOT / "quality").glob("DQ*.sql")):
        sql = path.read_text().strip().rstrip(";")
        severity = "warning" if "-- Severity: warning" in sql else "error"
        count = connection.scalar(
            text("SELECT count(*) FROM (\n" + sql + "\n) AS violations")
        )
        results.append(CheckResult(path.stem, severity, int(count or 0)))
    return results


def validate(engine: Engine) -> list[CheckResult]:
    """Read all quality checks in a single database snapshot."""
    with engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    ) as connection:
        return check_connection(connection)
