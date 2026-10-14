"""Real PostgreSQL fixtures; production database is never used for mutations."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from stocgain.generator.config import load_config
from stocgain.generator.simulation import simulate
from stocgain.generator.writer import write_dataset
from stocgain.loader.copy_loader import load_dataset
from stocgain.settings import REPOSITORY_ROOT, Settings


@pytest.fixture(scope="session")
def loaded_small_db(tmp_path_factory):
    settings = Settings()
    assert settings.test_database_url != settings.database_url
    engine = create_engine(settings.test_database_url)
    cfg = Config(str(REPOSITORY_ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    path = tmp_path_factory.mktemp("small") / "dataset"
    write_dataset(simulate(load_config("small"), 42), path)
    load_dataset(engine, path)
    yield engine
    engine.dispose()


@pytest.fixture
def db_tx(loaded_small_db):
    with loaded_small_db.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
