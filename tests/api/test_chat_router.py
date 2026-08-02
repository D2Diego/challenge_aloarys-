from fastapi import WebSocketDisconnect

from app.api.routers.chat import websocket_chat
from app.api.security import create_access_token
from app.services.query_service import QueryCompletedEvent


class _FakeWebSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent_messages = []
        self.closed_code = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        if not self._messages:
            raise WebSocketDisconnect(code=1000)
        return self._messages.pop(0)

    async def send_json(self, message):
        self.sent_messages.append(message)

    async def close(self, code):
        self.closed_code = code


class _FakeStreamingQueryService:
    async def stream_answer(
        self,
        question,
        document_ids=None,
        top_k=5,
        min_score=0.5,
        conversation_id=None,
    ):
        yield QueryCompletedEvent(answer="No information found", sources=[])


async def test_websocket_requires_valid_token():
    websocket = _FakeWebSocket([{"token": "invalid-token"}])

    await websocket_chat(websocket)

    assert websocket.accepted is True
    assert websocket.sent_messages[0]["type"] == "error"
    assert websocket.closed_code == 4401


async def test_websocket_streams_answer_with_valid_token():
    import app.api.routers.chat as chat_module

    original_get_qdrant = chat_module.get_qdrant
    original_get_http_client = chat_module.get_ollama_http_client
    original_get_db = chat_module.get_conversations_db
    original_build_service = chat_module.build_query_service
    chat_module.get_qdrant = lambda websocket: None
    chat_module.get_ollama_http_client = lambda websocket: None
    chat_module.get_conversations_db = lambda websocket: None
    chat_module.build_query_service = (
        lambda qdrant, http_client, connection: _FakeStreamingQueryService()
    )
    websocket = _FakeWebSocket(
        [
            {"token": create_access_token("admin")},
            {"question": "Any question"},
        ]
    )
    try:
        await websocket_chat(websocket)
    finally:
        chat_module.get_qdrant = original_get_qdrant
        chat_module.get_ollama_http_client = original_get_http_client
        chat_module.get_conversations_db = original_get_db
        chat_module.build_query_service = original_build_service

    assert websocket.sent_messages[0]["type"] == "complete"
    assert websocket.sent_messages[0]["answer"] == "No information found"
