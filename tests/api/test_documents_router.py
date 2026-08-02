from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.api.dependencies import (
    enforce_document_upload_rate_limit,
    get_current_user,
    get_ingestion_service,
)
from app.api.middleware import UploadSizeLimitMiddleware
from app.api.routers import documents
from app.api.routers.documents import ingest_document
from app.bootstrap.settings import settings
from app.domain.entities import Document, DocumentStatus, DocumentType
from app.main import app


async def _accept_upload(request: Request):
    await request.body()
    return JSONResponse({"accepted": True})


def _limited_app(max_body_size_bytes: int) -> Starlette:
    application = Starlette(
        routes=[Route("/documents", _accept_upload, methods=["POST"])]
    )
    application.add_middleware(
        UploadSizeLimitMiddleware,
        max_body_size_bytes=max_body_size_bytes,
        paths={"/documents"},
    )
    return application


class _FakeIngestionService:
    def __init__(self):
        self.pdf_calls = []

    def ingest_pdf(self, *, name, content):
        self.pdf_calls.append((name, content))
        return Document(
            id=uuid4(),
            name=name,
            document_type=DocumentType.PDF,
            status=DocumentStatus.PROCESSING,
            ingested_at=datetime.now(UTC),
        )


class _RecordingUpload:
    filename = "report.pdf"
    content_type = "application/pdf"

    def __init__(self):
        self.read_size = None

    async def read(self, size=-1):
        self.read_size = size
        return b"%PDF-1.7\n"


async def _test_user():
    return "test-user"


async def _allow_upload():
    return None


async def _post_pdf(*, content: bytes, content_type: str):
    service = _FakeIngestionService()

    async def fake_ingestion_service():
        return service

    application = FastAPI()
    application.include_router(documents.router)
    application.dependency_overrides[get_current_user] = _test_user
    application.dependency_overrides[
        enforce_document_upload_rate_limit
    ] = _allow_upload
    application.dependency_overrides[
        get_ingestion_service
    ] = fake_ingestion_service
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/documents",
            files={"file": ("report.pdf", content, content_type)},
        )
    return response, service


async def test_rejects_oversized_request_from_content_length():
    async with AsyncClient(
        transport=ASGITransport(app=_limited_app(10)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/documents",
            content=b"small",
            headers={"Content-Length": "11"},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "PAYLOAD_TOO_LARGE"


async def test_rejects_oversized_stream_when_content_length_is_missing():
    async def body_chunks():
        yield b"123456"
        yield b"78901"

    async with AsyncClient(
        transport=ASGITransport(app=_limited_app(10)),
        base_url="http://test",
    ) as client:
        response = await client.post("/documents", content=body_chunks())

    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "PAYLOAD_TOO_LARGE"


async def test_application_rejects_oversized_document_request_before_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/documents",
            content=b"",
            headers={
                "Content-Length": str(
                    settings.max_upload_request_size_bytes + 1
                )
            },
        )

    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "PAYLOAD_TOO_LARGE"


async def test_rejects_pdf_with_wrong_content_type_before_enqueueing():
    response, service = await _post_pdf(
        content=b"%PDF-1.7\n",
        content_type="text/plain",
    )

    assert response.status_code == 415
    assert response.json()["detail"]["error_code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert service.pdf_calls == []


async def test_rejects_pdf_when_magic_bytes_are_missing():
    response, service = await _post_pdf(
        content=b"this is not a PDF",
        content_type="application/pdf",
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "INVALID_PDF"
    assert service.pdf_calls == []


async def test_reads_at_most_one_byte_beyond_the_file_limit():
    upload = _RecordingUpload()
    service = _FakeIngestionService()

    await ingest_document(file=upload, text=None, name=None, service=service)

    assert upload.read_size == settings.max_upload_size_bytes + 1
    assert service.pdf_calls == [("report.pdf", b"%PDF-1.7\n")]
