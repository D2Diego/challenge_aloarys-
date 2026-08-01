"""Tests for the embedded Qdrant document repository."""

import uuid

from app.adapters.qdrant.document_repository import QdrantDocumentRepository
from app.domain.entities import ChunkToSave, DocumentStatus, DocumentType


def test_creates_and_gets_document(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)

    document = repository.create(
        name="contract.pdf",
        document_type=DocumentType.PDF,
    )

    assert document.status == DocumentStatus.PROCESSING
    stored_document = repository.get(document.id)
    assert stored_document is not None
    assert stored_document.name == "contract.pdf"


def test_returns_none_for_missing_document(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)

    assert repository.get(uuid.uuid4()) is None


def test_updates_status_and_filters_document_list(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)
    document = repository.create(
        name="document.txt",
        document_type=DocumentType.TEXT,
    )

    repository.update_status(
        document.id,
        status=DocumentStatus.READY,
        total_chunks=3,
    )

    documents, total = repository.list_documents(
        page=1,
        limit=10,
        status=DocumentStatus.READY,
    )
    assert total == 1
    assert documents[0].total_chunks == 3


def test_saves_chunks_and_counts_only_documents(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)
    document = repository.create(
        name="document.txt",
        document_type=DocumentType.TEXT,
    )

    total = repository.save_chunks(
        document_id=document.id,
        document_name="document.txt",
        chunks=[
            ChunkToSave(text="part 1", embedding=[0.0] * 768, page=None),
            ChunkToSave(text="part 2", embedding=[0.0] * 768, page=None),
        ],
    )

    assert total == 2
    assert repository.count() == 1


def test_deletes_document_and_its_chunks(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)
    document = repository.create(
        name="document.txt",
        document_type=DocumentType.TEXT,
    )
    repository.save_chunks(
        document_id=document.id,
        document_name="document.txt",
        chunks=[ChunkToSave(text="x", embedding=[0.0] * 768, page=None)],
    )

    assert repository.delete(document.id) is True
    assert repository.get(document.id) is None
    assert repository.delete(document.id) is False


def test_reconciles_stuck_processing_documents(qdrant_memory):
    repository = QdrantDocumentRepository(qdrant_memory)
    document = repository.create(
        name="document.txt",
        document_type=DocumentType.TEXT,
    )

    total = repository.reconcile_stuck_processing()

    assert total == 1
    stored_document = repository.get(document.id)
    assert stored_document.status == DocumentStatus.FAILED
    assert stored_document.error
