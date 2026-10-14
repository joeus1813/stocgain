"""Alembic environment; table revisions are introduced in Phase 1."""

from alembic import context

from stocgain.db.engine import create_db_engine
from stocgain.db.models import Base
from stocgain.settings import get_settings


def run_migrations_offline() -> None:
    """Render PostgreSQL migration SQL without opening a connection."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run versioned migrations inside a PostgreSQL transaction."""
    engine = create_db_engine(get_settings())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                include_schemas=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
