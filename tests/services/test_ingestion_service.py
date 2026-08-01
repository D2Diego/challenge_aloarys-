from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities import Document, DocumentStatus, DocumentType
from app.services.ingestion_service import IngestionService


class _FakeRepository:
    def create(self, *, name, document_type):
        return Document(
            id=uuid4(),
            name=name,
            document_type=document_type,
            status=DocumentStatus.PROCESSING,
            ingested_at=datetime.now(timezone.utc),
        )


class _FakeTaskQueue:
    def __init__(self):
        self.calls = []

    def enqueue_text_ingestion(self, document_id, raw_text, name):
        self.calls.append(("text", document_id, raw_text, name))

    def enqueue_pdf_ingestion(self, document_id, content, name):
        self.calls.append(("pdf", document_id, content, name))


def test_ingest_text_creates_document_and_enqueues_processing():
    task_queue = _FakeTaskQueue()
    document = IngestionService(_FakeRepository(), task_queue).ingest_text(
        name="contract.txt",
        text="contract content",
    )

    assert document.document_type == DocumentType.TEXT
    assert document.status == DocumentStatus.PROCESSING
    assert task_queue.calls == [
        ("text", str(document.id), "contract content", "contract.txt")
    ]


def test_ingest_pdf_creates_document_and_enqueues_processing():
    task_queue = _FakeTaskQueue()
    document = IngestionService(_FakeRepository(), task_queue).ingest_pdf(
        name="contract.pdf",
        content=b"%PDF-1.4...",
    )

    assert document.document_type == DocumentType.PDF
    assert task_queue.calls == [
        ("pdf", str(document.id), b"%PDF-1.4...", "contract.pdf")
    ]
