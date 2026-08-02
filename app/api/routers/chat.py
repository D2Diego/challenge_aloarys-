"""Streaming RAG queries over WebSocket."""

import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import (
    build_query_service,
    get_conversations_db,
    get_ollama_http_client,
    get_qdrant,
)
from app.api.mapping import to_stream_payload
from app.api.security import decode_token
from app.bootstrap.settings import settings

logger = logging.getLogger("app")
router = APIRouter(tags=["chat"])


def _parse_conversation_id(raw_value: object) -> UUID | None:
    """Parse an optional conversation identifier from a WebSocket message."""
    if not raw_value:
        return None
    if not isinstance(raw_value, str):
        raise ValueError("conversation_id must be a string.")
    return UUID(raw_value)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        first_message = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    try:
        user = decode_token(first_message.get("token", ""))
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Not authenticated."})
        await websocket.close(code=4401)
        return

    try:
        conversation_id = _parse_conversation_id(
            first_message.get("conversation_id")
        )
    except ValueError:
        await websocket.send_json(
            {"type": "error", "message": "Invalid conversation_id."}
        )
        await websocket.close(code=4401)
        return

    logger.info("chat_websocket_connected", extra={"user": user})
    query_service = build_query_service(
        get_qdrant(websocket),
        get_ollama_http_client(websocket),
        get_conversations_db(websocket),
    )
    try:
        while True:
            message = await websocket.receive_json()
            question = (message.get("question") or "").strip()
            if not question:
                await websocket.send_json(
                    {"type": "error", "message": "The 'question' field is empty."}
                )
                continue
            try:
                async for event in query_service.stream_answer(
                    question,
                    document_ids=message.get("document_ids"),
                    top_k=settings.top_k_default,
                    min_score=settings.min_score,
                    conversation_id=conversation_id,
                ):
                    await websocket.send_json(to_stream_payload(event))
                logger.info(
                    "chat_websocket_answered",
                    extra={"question_length": len(question)},
                )
            except Exception:
                logger.exception("chat_websocket_query_failed")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Unable to generate an answer. Please try again.",
                    }
                )
    except WebSocketDisconnect:
        logger.info("chat_websocket_disconnected", extra={"user": user})
