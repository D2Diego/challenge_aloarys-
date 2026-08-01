"""Redis Queue implementation of the task queue port."""

from rq import Queue


class RQTaskQueue:
    def __init__(self, queue: Queue):
        self._queue = queue

    def enqueue_text_ingestion(
        self,
        document_id: str,
        raw_text: str,
        name: str,
    ) -> None:
        from app.adapters.rq.jobs import process_text_ingestion_job

        self._queue.enqueue(
            process_text_ingestion_job,
            document_id,
            raw_text,
            name,
        )

    def enqueue_pdf_ingestion(
        self,
        document_id: str,
        content: bytes,
        name: str,
    ) -> None:
        from app.adapters.rq.jobs import process_pdf_ingestion_job

        self._queue.enqueue(
            process_pdf_ingestion_job,
            document_id,
            content,
            name,
        )
