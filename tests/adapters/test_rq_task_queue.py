from unittest.mock import MagicMock

from app.adapters.rq.task_queue import RQTaskQueue


def test_enqueues_text_ingestion_job():
    queue = MagicMock()

    RQTaskQueue(queue, job_timeout_seconds=300).enqueue_text_ingestion(
        "document-1",
        "raw text",
        "document.txt",
    )

    arguments = queue.enqueue.call_args.args
    assert arguments[0].__name__ == "process_text_ingestion_job"
    assert arguments[1:] == ("document-1", "raw text", "document.txt")


def test_enqueues_pdf_ingestion_job():
    queue = MagicMock()

    RQTaskQueue(queue, job_timeout_seconds=300).enqueue_pdf_ingestion(
        "document-2",
        b"content",
        "document.pdf",
    )

    arguments = queue.enqueue.call_args.args
    assert arguments[0].__name__ == "process_pdf_ingestion_job"
    assert arguments[1:] == ("document-2", b"content", "document.pdf")


def test_applies_configured_timeout_to_ingestion_jobs():
    queue = MagicMock()
    task_queue = RQTaskQueue(queue, job_timeout_seconds=120)

    task_queue.enqueue_pdf_ingestion(
        "document-2",
        b"content",
        "document.pdf",
    )

    assert queue.enqueue.call_args.kwargs["job_timeout"] == 120
