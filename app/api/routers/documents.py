"""Document ingestion and metadata endpoints."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.dependencies import (
    enforce_document_upload_rate_limit,
    get_current_user,
    get_document_repository,
    get_ingestion_service,
)
from app.api.errors import http_error
from app.api.mapping import to_document_response
from app.api.schemas import DocumentListResponse, DocumentResponse
from app.bootstrap.settings import settings
from app.domain.entities import DocumentStatus
from app.ports.document_repository import DocumentRepositoryPort
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["documents"], dependencies=[Depends(get_current_user)])


@router.post(
    "/documents",
    status_code=202,
    response_model=DocumentResponse,
    dependencies=[Depends(enforce_document_upload_rate_limit)],
)
async def ingest_document(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    name: str | None = Form(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    has_file = file is not None and bool(file.filename)
    has_text = text is not None and bool(text.strip())
    if has_file == has_text:
        raise http_error(
            422,
            "VALIDATION_ERROR",
            "Provide exactly one of 'file' or 'text'.",
        )

    if has_file:
        if file.content_type != "application/pdf":
            raise http_error(
                415,
                "UNSUPPORTED_MEDIA_TYPE",
                "Only PDF files with content type 'application/pdf' are accepted.",
            )
        content = await file.read(settings.max_upload_size_bytes + 1)
        if len(content) > settings.max_upload_size_bytes:
            raise http_error(
                413,
                "PAYLOAD_TOO_LARGE",
                f"File exceeds the {settings.max_upload_size_mb}MB limit.",
            )
        if not content.startswith(b"%PDF-"):
            raise http_error(
                422,
                "INVALID_PDF",
                "File content does not have a valid PDF signature.",
            )
        final_name = name or file.filename or "document.pdf"
        document = service.ingest_pdf(name=final_name, content=content)
    else:
        if not name:
            raise http_error(
                422,
                "VALIDATION_ERROR",
                "The 'name' field is required when sending text.",
            )
        document = service.ingest_text(name=name, text=text)
    return to_document_response(document)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_endpoint(
    document_id: uuid.UUID,
    repository: DocumentRepositoryPort = Depends(get_document_repository),
):
    document = repository.get(document_id)
    if document is None:
        raise http_error(
            404,
            "DOCUMENT_NOT_FOUND",
            f"Document {document_id} was not found.",
        )
    return to_document_response(document)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: DocumentStatus | None = None,
    repository: DocumentRepositoryPort = Depends(get_document_repository),
):
    documents, total = repository.list_documents(
        page=page,
        limit=limit,
        status=status,
    )
    return DocumentListResponse(
        documents=[to_document_response(document) for document in documents],
        total=total,
        page=page,
        limit=limit,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document_endpoint(
    document_id: uuid.UUID,
    repository: DocumentRepositoryPort = Depends(get_document_repository),
):
    if not repository.delete(document_id):
        raise http_error(
            404,
            "DOCUMENT_NOT_FOUND",
            f"Document {document_id} was not found.",
        )
