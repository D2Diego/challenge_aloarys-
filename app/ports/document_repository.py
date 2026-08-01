from typing import Protocol
from uuid import UUID

from app.domain.entities import ChunkToSave, Document, DocumentStatus, DocumentType


class DocumentRepositoryPort(Protocol):
    def create(self, *, name: str, type: DocumentType) -> Document: ...

    def get(self, document_id: UUID) -> Document | None: ...

    def list(
        self,
        *,
        page: int,
        limit: int,
        status: DocumentStatus | None,
    ) -> tuple[list[Document], int]: ...

    def delete(self, document_id: UUID) -> bool: ...

    def update_status(
        self,
        document_id: UUID,
        *,
        status: DocumentStatus,
        total_chunks: int | None = None,
        error: str | None = None,
    ) -> None: ...

    def save_chunks(
        self,
        *,
        document_id: UUID,
        document_name: str,
        chunks: list[ChunkToSave],
    ) -> int: ...

    def reconcile_stuck_processing(self) -> int: ...

    def count(self) -> int: ...
