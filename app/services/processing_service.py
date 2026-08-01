"""Document normalization, chunking, embedding, and persistence use cases."""

import logging
import uuid

from app.domain.chunking import semantic_chunk
from app.domain.entities import ChunkToSave, DocumentStatus
from app.domain.normalization import normalize_text
from app.ports.document_repository import DocumentRepositoryPort
from app.ports.embeddings import EmbeddingPort
from app.ports.pdf_parser import PDFParserPort

logger = logging.getLogger("worker")


class ProcessingService:
    def __init__(
        self,
        repository: DocumentRepositoryPort,
        embeddings: EmbeddingPort,
        pdf_parser: PDFParserPort,
    ):
        self._repository = repository
        self._embeddings = embeddings
        self._pdf_parser = pdf_parser

    def _prepare_chunks(self, raw_text: str) -> list[str]:
        text = normalize_text(raw_text)
        return semantic_chunk(
            text,
            self._embeddings.embed_sentences,
            self._embeddings.count_tokens,
        )

    def process_text(self, document_id: str, raw_text: str, name: str) -> None:
        parsed_document_id = uuid.UUID(document_id)
        logger.info(
            "ingestion_started",
            extra={"document_id": document_id, "type": "text"},
        )
        try:
            chunks = [
                ChunkToSave(
                    text=text,
                    embedding=self._embeddings.embed_passage(text),
                    page=None,
                )
                for text in self._prepare_chunks(raw_text)
            ]
            total = self._repository.save_chunks(
                document_id=parsed_document_id,
                document_name=name,
                chunks=chunks,
            )
            self._repository.update_status(
                parsed_document_id,
                status=DocumentStatus.READY,
                total_chunks=total,
            )
            logger.info(
                "ingestion_completed",
                extra={"document_id": document_id, "total_chunks": total},
            )
        except Exception as error:
            self._repository.update_status(
                parsed_document_id,
                status=DocumentStatus.FAILED,
                error=str(error),
            )
            logger.exception(
                "ingestion_failed",
                extra={"document_id": document_id},
            )

    def process_pdf(self, document_id: str, content: bytes, name: str) -> None:
        parsed_document_id = uuid.UUID(document_id)
        logger.info(
            "ingestion_started",
            extra={"document_id": document_id, "type": "pdf"},
        )
        try:
            chunks: list[ChunkToSave] = []
            pages = self._pdf_parser.extract_pages(content)
            for page_number, page_text in enumerate(pages, start=1):
                if not page_text.strip():
                    continue
                for chunk_text in self._prepare_chunks(page_text):
                    chunks.append(
                        ChunkToSave(
                            text=chunk_text,
                            embedding=self._embeddings.embed_passage(chunk_text),
                            page=page_number,
                        )
                    )

            if not chunks:
                raise ValueError(
                    "No text could be extracted from the PDF. "
                    "The file may be empty, scanned, or corrupted."
                )

            total = self._repository.save_chunks(
                document_id=parsed_document_id,
                document_name=name,
                chunks=chunks,
            )
            self._repository.update_status(
                parsed_document_id,
                status=DocumentStatus.READY,
                total_chunks=total,
            )
            logger.info(
                "ingestion_completed",
                extra={"document_id": document_id, "total_chunks": total},
            )
        except Exception as error:
            self._repository.update_status(
                parsed_document_id,
                status=DocumentStatus.FAILED,
                error=str(error),
            )
            logger.exception(
                "ingestion_failed",
                extra={"document_id": document_id},
            )
