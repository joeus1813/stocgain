"""Consistent API errors without internal exception text."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    """Create the documented error envelope."""
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


class ApiError(Exception):
    """Expected application failure with safe public details."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.status, self.code, self.message, self.details = (
            status,
            code,
            message,
            details,
        )
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    """Register HTTP and request-validation exception handlers."""

    @app.exception_handler(ApiError)
    async def application_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(OperationalError)
    async def database_error(request: Request, exc: OperationalError) -> JSONResponse:
        return error_response(503, "DATABASE_UNAVAILABLE", "Database is unavailable.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Invalid request parameters.",
            {
                "errors": [
                    {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                    for e in exc.errors()
                ]
            },
        )
