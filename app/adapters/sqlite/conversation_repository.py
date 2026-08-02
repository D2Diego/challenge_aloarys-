"""SQLite-backed conversation repository."""

import json
import sqlite3
from datetime import datetime
from uuid import UUID

from app.domain.conversation import Conversation, ConversationTurn, TokenUsage
from app.domain.entities import FoundChunk

_LIST_CONVERSATIONS_SQL = """
    SELECT c.id, c.created_at, c.updated_at, COUNT(t.id)
    FROM conversations c LEFT JOIN turns t ON t.conversation_id = c.id
"""


def _sources_to_json(sources: list[FoundChunk]) -> str:
    return json.dumps(
        [
            {
                "document_id": str(chunk.document_id),
                "document_name": chunk.document_name,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "score": chunk.score,
            }
            for chunk in sources
        ]
    )


def _sources_from_json(raw_value: str) -> list[FoundChunk]:
    return [
        FoundChunk(
            document_id=UUID(item["document_id"]),
            document_name=item["document_name"],
            page=item["page"],
            chunk_index=item["chunk_index"],
            text=item["text"],
            score=item["score"],
        )
        for item in json.loads(raw_value)
    ]


def _row_to_conversation(row) -> Conversation:
    return Conversation(
        id=UUID(row[0]),
        created_at=datetime.fromisoformat(row[1]),
        updated_at=datetime.fromisoformat(row[2]),
        total_turns=row[3],
    )


class SQLiteConversationRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def save_turn(self, turn: ConversationTurn) -> None:
        timestamp = turn.created_at.isoformat()
        conversation_id = str(turn.conversation_id)
        with self._connection:
            self._connection.execute(
                "INSERT INTO conversations (id, created_at, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at",
                (conversation_id, timestamp, timestamp),
            )
            self._connection.execute(
                "INSERT INTO turns (conversation_id, question, answer, "
                "sources_json, prompt_tokens, completion_tokens, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    turn.question,
                    turn.answer,
                    _sources_to_json(turn.sources),
                    turn.usage.prompt_tokens,
                    turn.usage.completion_tokens,
                    timestamp,
                ),
            )

    def get_history(
        self,
        conversation_id: UUID,
        limit: int,
    ) -> list[ConversationTurn]:
        rows = self._connection.execute(
            "SELECT question, answer, sources_json, prompt_tokens, "
            "completion_tokens, created_at FROM turns WHERE conversation_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (str(conversation_id), limit),
        ).fetchall()
        turns = [
            ConversationTurn(
                conversation_id=conversation_id,
                question=row[0],
                answer=row[1],
                sources=_sources_from_json(row[2]),
                usage=TokenUsage(
                    prompt_tokens=row[3],
                    completion_tokens=row[4],
                ),
                created_at=datetime.fromisoformat(row[5]),
            )
            for row in rows
        ]
        return list(reversed(turns))

    def list_conversations(self) -> list[Conversation]:
        rows = self._connection.execute(
            _LIST_CONVERSATIONS_SQL
            + " GROUP BY c.id ORDER BY c.updated_at DESC, c.rowid DESC"
        ).fetchall()
        return [_row_to_conversation(row) for row in rows]

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        row = self._connection.execute(
            _LIST_CONVERSATIONS_SQL + " WHERE c.id = ? GROUP BY c.id",
            (str(conversation_id),),
        ).fetchone()
        return _row_to_conversation(row) if row else None

    def delete_conversation(self, conversation_id: UUID) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (str(conversation_id),),
            )
