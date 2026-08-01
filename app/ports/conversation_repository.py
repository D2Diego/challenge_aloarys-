from typing import Protocol
from uuid import UUID

from app.domain.conversation import Conversation, ConversationTurn


class ConversationRepositoryPort(Protocol):
    def save_turn(self, turn: ConversationTurn) -> None: ...

    def get_history(
        self,
        conversation_id: UUID,
        limit: int,
    ) -> list[ConversationTurn]: ...

    def list_conversations(self) -> list[Conversation]: ...

    def get_conversation(self, conversation_id: UUID) -> Conversation | None: ...

    def delete_conversation(self, conversation_id: UUID) -> None: ...
