"""Importable callbacks executed by RQ workers."""

from app.adapters.e5_embeddings import E5Embeddings
from app.adapters.pypdf_parser import PyPDFParser
from app.adapters.qdrant.client import get_qdrant_client
from app.adapters.qdrant.document_repository import QdrantDocumentRepository
from app.bootstrap.settings import settings
from app.services.processing_service import ProcessingService

_processing_service: ProcessingService | None = None


def _get_processing_service() -> ProcessingService:
    global _processing_service
    if _processing_service is None:
        repository = QdrantDocumentRepository(
            get_qdrant_client(settings.qdrant_url)
        )
        _processing_service = ProcessingService(
            repository,
            E5Embeddings(),
            PyPDFParser(),
        )
    return _processing_service


def process_text_ingestion_job(
    document_id: str,
    raw_text: str,
    name: str,
) -> None:
    _get_processing_service().process_text(document_id, raw_text, name)


def process_pdf_ingestion_job(
    document_id: str,
    content: bytes,
    name: str,
) -> None:
    _get_processing_service().process_pdf(document_id, content, name)
