"""Repeatable views are applied in filename order in one transaction."""

from sqlalchemy import Connection, Engine, text

from stocgain.db.sql_loader import SQL_ROOT, read_sql


def apply_views_connection(connection: Connection) -> None:
    """Apply the views currently delivered by the active implementation phase."""
    for path in sorted((SQL_ROOT / "views").glob("*.sql")):
        connection.exec_driver_sql(read_sql(path))


def apply_views(engine: Engine) -> None:
    """Commit all view definitions together or roll back every definition."""
    with engine.begin() as connection:
        apply_views_connection(connection)


def refresh_views(engine: Engine) -> int:
    """Refresh installed analytics materialized views after operational data changes."""
    with engine.begin() as connection:
        names = (
            connection.execute(text(read_sql("quality_support/materialized_views.sql")))
            .scalars()
            .all()
        )
        for name in names:
            quoted = connection.dialect.identifier_preparer.quote(name)
            connection.exec_driver_sql(f"REFRESH MATERIALIZED VIEW analytics.{quoted}")
        return len(names)
