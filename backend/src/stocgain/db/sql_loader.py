"""Load repository-owned SQL files with stable paths and bound values."""

from pathlib import Path

from stocgain.settings import REPOSITORY_ROOT

SQL_ROOT = REPOSITORY_ROOT / "sql"


def read_sql(path: str | Path) -> str:
    """Read a SQL file beneath the repository SQL directory."""
    resolved = (SQL_ROOT / path).resolve()
    if not resolved.is_relative_to(SQL_ROOT):
        raise ValueError("SQL path outside repository")
    return resolved.read_text(encoding="utf-8")
