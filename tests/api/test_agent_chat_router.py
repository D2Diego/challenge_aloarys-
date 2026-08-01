from fastapi import WebSocketDisconnect

from app.api.routers.agent_chat import websocket_agent
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


class _FakeStreamingAgentService:
    async def stream_answer(
        self,
        question,
        document_ids=None,
        top_k=5,
        min_score=0.5,
        conversation_id=None,
    ):
        yield QueryCompletedEvent(answer="No information found", sources=[])


async def test_agent_websocket_requires_valid_token():
    websocket = _FakeWebSocket([{"token": "invalid-token"}])

    await websocket_agent(websocket)

    assert websocket.accepted is True
    assert websocket.sent_messages[0]["type"] == "error"
    assert websocket.closed_code == 4401


async def test_agent_websocket_streams_answer_with_valid_token():
    import app.api.routers.agent_chat as agent_chat_module

    original_get_qdrant = agent_chat_module.get_qdrant
    original_get_http_client = agent_chat_module.get_ollama_http_client
    original_get_db = agent_chat_module.get_conversations_db
    original_build_service = agent_chat_module.build_agent_query_service
    agent_chat_module.get_qdrant = lambda websocket: None
    agent_chat_module.get_ollama_http_client = lambda websocket: None
    agent_chat_module.get_conversations_db = lambda websocket: None
    agent_chat_module.build_agent_query_service = (
        lambda qdrant, http_client, connection: _FakeStreamingAgentService()
    )
    websocket = _FakeWebSocket(
        [
            {"token": create_access_token("admin")},
            {"question": "Any question"},
        ]
    )
    try:
        await websocket_agent(websocket)
    finally:
        agent_chat_module.get_qdrant = original_get_qdrant
        agent_chat_module.get_ollama_http_client = original_get_http_client
        agent_chat_module.get_conversations_db = original_get_db
        agent_chat_module.build_agent_query_service = original_build_service

    assert websocket.sent_messages[0]["type"] == "complete"
    assert websocket.sent_messages[0]["answer"] == "No information found"
