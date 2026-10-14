"""Data-generation, SQL analysis and PostgreSQL maintenance commands."""

import json
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from sqlalchemy import text

from stocgain.db.engine import create_db_engine
from stocgain.db.sql_loader import read_sql
from stocgain.db.views import apply_views, refresh_views
from stocgain.generator.config import load_config
from stocgain.generator.simulation import simulate
from stocgain.generator.writer import write_dataset
from stocgain.loader.copy_loader import load_dataset
from stocgain.quality.checks import CheckResult, validate
from stocgain.settings import REPOSITORY_ROOT, get_settings

app = typer.Typer(
    no_args_is_help=True,
    help="stocgain batch and database commands.",
    pretty_exceptions_show_locals=False,
)
data = typer.Typer(no_args_is_help=True)
db = typer.Typer(no_args_is_help=True)
app.add_typer(data, name="data")
app.add_typer(db, name="db")


def not_implemented() -> None:
    """Keep later-phase commands explicit until their implementation gate."""
    typer.echo(
        "Not implemented: this command requires a later implementation phase.", err=True
    )
    raise typer.Exit(2)


for name in ("analytics", "pipeline"):
    app.add_typer(
        typer.Typer(invoke_without_command=True, callback=not_implemented), name=name
    )


def report(results: list[CheckResult]) -> None:
    """Print every observed check and fail on any error-severity violation."""
    typer.echo("check\tseverity\tviolations")
    for r in results:
        typer.echo(f"{r.check}\t{r.severity}\t{r.violations}")
    if any(r.severity == "error" and r.violations for r in results):
        raise typer.Exit(1)


@data.command("generate")
def generate(
    preset: str = "standard", seed: int = 42, output: Path | None = None
) -> None:
    """Generate deterministic CSV files and a provenance manifest."""
    start = perf_counter()
    result = write_dataset(
        simulate(load_config(preset), seed),
        output or REPOSITORY_ROOT / "data/generated" / preset,
    )
    typer.echo(
        json.dumps(
            {
                "preset": preset,
                "seed": seed,
                "content_checksum": result["content_checksum"],
                "row_counts": result["row_counts"],
                "elapsed_seconds": round(perf_counter() - start, 3),
            }
        )
    )


@data.command("load")
def load(path: Annotated[Path, typer.Option()], replace: bool = False) -> None:
    """COPY a validated directory; --replace explicitly permits table replacement."""
    engine = create_db_engine(get_settings())
    start = perf_counter()
    try:
        report(load_dataset(engine, path, replace=replace))
        typer.echo(f"load_and_validate_seconds={perf_counter() - start:.3f}")
    finally:
        engine.dispose()


@data.command("validate")
def validate_command() -> None:
    """Run all 18 quality checks against the actual PostgreSQL dataset."""
    engine = create_db_engine(get_settings())
    start = perf_counter()
    try:
        report(validate(engine))
        typer.echo(f"validation_seconds={perf_counter() - start:.3f}")
    finally:
        engine.dispose()


@data.command("profile")
def profile() -> None:
    """Print Phase 1 calibration metrics calculated from loaded records."""
    engine = create_db_engine(get_settings())
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
            result = (
                connection.execute(text(read_sql("quality_support/profile.sql")))
                .mappings()
                .one()
            )
            typer.echo(json.dumps(dict(result), default=str, indent=2))
    finally:
        engine.dispose()


@db.command("apply-views")
def apply_views_command() -> None:
    """Apply delivered repeatable views in one transaction."""
    engine = create_db_engine(get_settings())
    try:
        apply_views(engine)
    finally:
        engine.dispose()


@db.command("refresh")
def refresh_command() -> None:
    """Refresh installed materialized views, if any are delivered."""
    engine = create_db_engine(get_settings())
    try:
        typer.echo(f"Refreshed {refresh_views(engine)} materialized views.")
    finally:
        engine.dispose()


@db.command("run-analysis")
def run_analysis(number: str) -> None:
    """Execute one of the fifteen repository-owned SQL analyses by number."""
    from stocgain.db.sql_loader import SQL_ROOT

    if not number.isascii() or not number.isdigit() or not 1 <= int(number) <= 15:
        raise typer.BadParameter("Choose an analysis number from 01 to 15")
    path = next((SQL_ROOT / "analyses").glob(f"{int(number):02}_*.sql"))
    engine = create_db_engine(get_settings())
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
            rows = connection.execute(text(read_sql(path))).mappings().all()
            typer.echo(json.dumps([dict(row) for row in rows], default=str, indent=2))
    finally:
        engine.dispose()
