"""Consistent API errors without internal exception text."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def error_response(status: int, code: str, message: str) -> JSONResponse:
    """Create the documented error envelope."""
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register HTTP and request-validation exception handlers."""

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
        return error_response(422, "VALIDATION_ERROR", "Invalid request parameters.")
