"""Redis Queue implementation of the task queue port."""

from rq import Queue


class RQTaskQueue:
    def __init__(self, queue: Queue, *, job_timeout_seconds: int):
        self._queue = queue
        self._job_timeout_seconds = job_timeout_seconds

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
            job_timeout=self._job_timeout_seconds,
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
            job_timeout=self._job_timeout_seconds,
        )
