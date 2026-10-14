"""Environment settings; model parameters belong in config TOML files."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Load local environment from the repository root, independent of cwd."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: str = (
        "postgresql+psycopg://stocksense:stocksense@localhost:5433/stocksense"
    )
    test_database_url: str = (
        "postgresql+psycopg://stocksense:stocksense@localhost:5433/stocksense_test"
    )
    stocksense_env: Literal["local", "test", "docker"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_cors_origins: str = "http://localhost:3000"
    analytics_config_path: Path = REPOSITORY_ROOT / "backend/config/analytics.toml"
    generator_config_path: Path = REPOSITORY_ROOT / "backend/config/generator.toml"

    @property
    def cors_origins(self) -> list[str]:
        """Return the comma-separated browser origin allowlist."""
        return [
            origin.strip()
            for origin in self.api_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached environment settings."""
    return Settings()
