"""Declarative metadata; Phase 1 adds the specified tables via migrations."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy 2 declarative metadata."""
