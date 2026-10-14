"""Database connections owned by the application lifecycle."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from stocksense.settings import Settings


def create_db_engine(settings: Settings) -> Engine:
    """Create a lazy PostgreSQL engine with a three-second connection timeout."""
    return create_engine(
        settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
    )


def check_database(engine: Engine) -> bool:
    """Check actual connectivity using SELECT 1, without exposing credentials."""
    try:
        with engine.connect() as connection:
            return bool(connection.scalar(text("SELECT 1")) == 1)
    except SQLAlchemyError:
        return False
