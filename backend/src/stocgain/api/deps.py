"""Request-scoped access to lifecycle-owned infrastructure."""

from fastapi import Request
from sqlalchemy import Engine


def get_engine(request: Request) -> Engine:
    """Return the application's database engine."""
    engine: Engine = request.app.state.engine
    return engine
