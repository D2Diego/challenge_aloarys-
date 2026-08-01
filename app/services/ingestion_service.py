"""Document registration and ingestion queue use cases."""

from app.domain.entities import Document, DocumentType
from app.ports.document_repository import DocumentRepositoryPort
from app.ports.task_queue import TaskQueuePort


class IngestionService:
    def __init__(
        self,
        repository: DocumentRepositoryPort,
        task_queue: TaskQueuePort,
    ):
        self._repository = repository
        self._task_queue = task_queue

    def ingest_text(self, *, name: str, text: str) -> Document:
        document = self._repository.create(
            name=name,
            document_type=DocumentType.TEXT,
        )
        self._task_queue.enqueue_text_ingestion(str(document.id), text, name)
        return document

    def ingest_pdf(self, *, name: str, content: bytes) -> Document:
        document = self._repository.create(
            name=name,
            document_type=DocumentType.PDF,
        )
        self._task_queue.enqueue_pdf_ingestion(str(document.id), content, name)
        return document
