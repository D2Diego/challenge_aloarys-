"""ASGI middleware for rejecting oversized upload requests."""

from collections.abc import Collection

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _RequestBodyTooLarge(Exception):
    pass


class UploadSizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_size_bytes: int,
        paths: Collection[str],
    ):
        self._app = app
        self._max_body_size_bytes = max_body_size_bytes
        self._paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] not in self._paths
        ):
            await self._app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if (
            content_length is not None
            and content_length > self._max_body_size_bytes
        ):
            await self._send_too_large(scope, receive, send)
            return

        received_bytes = 0

        async def receive_limited() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._max_body_size_bytes:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self._app(scope, receive_limited, send)
        except _RequestBodyTooLarge:
            await self._send_too_large(scope, receive, send)

    async def _send_too_large(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "error_code": "PAYLOAD_TOO_LARGE",
                    "message": "Upload request exceeds the configured size limit.",
                }
            },
        )
        await response(scope, receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope["headers"]:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
