from typing import Protocol


class TaskQueuePort(Protocol):
    def enqueue_text_ingestion(
        self,
        document_id: str,
        raw_text: str,
        name: str,
    ) -> None: ...

    def enqueue_pdf_ingestion(
        self,
        document_id: str,
        content: bytes,
        name: str,
    ) -> None: ...
