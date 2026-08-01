"""Consistent HTTP error responses."""

from fastapi import HTTPException

from app.api.schemas import ErrorResponse


def http_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(error_code=error_code, message=message).model_dump(),
    )
