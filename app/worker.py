"""RQ worker process entrypoint."""

from rq import Worker

from app.adapters.rq.connection import ingestion_queue, redis_connection
from app.adapters.rq.jobs import process_pdf_ingestion_job, process_text_ingestion_job
from app.bootstrap.logging import configure_logging
from app.bootstrap.settings import settings

__all__ = ["main", "process_pdf_ingestion_job", "process_text_ingestion_job"]


def main() -> None:
    configure_logging(level=settings.log_level)
    Worker([ingestion_queue], connection=redis_connection).work()


if __name__ == "__main__":
    main()
