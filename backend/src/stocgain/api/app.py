"""FastAPI skeleton; no business endpoints are implemented in Stage 1."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from stocgain import __version__
from stocgain.api.errors import error_response, register_error_handlers
from stocgain.api.routers.health import router
from stocgain.db.engine import create_db_engine
from stocgain.logging_config import configure_logging
from stocgain.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application with a lazy, lifecycle-owned PostgreSQL engine."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.engine = create_db_engine(settings)
        try:
            yield
        finally:
            application.state.engine.dispose()

    application = FastAPI(title="stocgain.", version=__version__, lifespan=lifespan)
    register_error_handlers(application)
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s unhandled_error", request_id)
            response = error_response(
                500, "INTERNAL_ERROR", "An unexpected error occurred."
            )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s elapsed_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Stocgain-Run-Id", "X-Stocgain-As-Of"],
    )
    return application


app = create_app()
