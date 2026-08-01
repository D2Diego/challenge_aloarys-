"""Conversation listing, history, and deletion endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_conversation_repository, get_current_user
from app.api.schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationTurnResponse,
    Source,
)
from app.domain.conversation import Conversation, ConversationTurn
from app.ports.conversation_repository import ConversationRepositoryPort

router = APIRouter(
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)

_FULL_HISTORY_LIMIT = 10_000


def _to_conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        total_turns=conversation.total_turns,
    )


def _to_turn_response(turn: ConversationTurn) -> ConversationTurnResponse:
    return ConversationTurnResponse(
        pipeline=turn.pipeline,
        question=turn.question,
        answer=turn.answer,
        sources=[
            Source(
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                page=chunk.page,
                excerpt=chunk.text,
                score=chunk.score,
            )
            for chunk in turn.sources
        ],
        prompt_tokens=turn.usage.prompt_tokens,
        completion_tokens=turn.usage.completion_tokens,
        created_at=turn.created_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    repository: ConversationRepositoryPort = Depends(get_conversation_repository),
):
    return ConversationListResponse(
        conversations=[
            _to_conversation_response(conversation)
            for conversation in repository.list_conversations()
        ]
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    repository: ConversationRepositoryPort = Depends(get_conversation_repository),
):
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "CONVERSATION_NOT_FOUND",
                "message": "Conversation was not found.",
            },
        )
    turns = repository.get_history(conversation_id, limit=_FULL_HISTORY_LIMIT)
    return ConversationDetailResponse(
        id=conversation.id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        turns=[_to_turn_response(turn) for turn in turns],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    repository: ConversationRepositoryPort = Depends(get_conversation_repository),
):
    repository.delete_conversation(conversation_id)
