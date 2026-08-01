"""FastAPI dependency providers and HTTP composition root."""

import sqlite3

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from qdrant_client import QdrantClient
from redis import Redis

from app.adapters.ai.pydantic_runtime import PydanticAgentRuntime
from app.adapters.e5_embeddings import E5Embeddings
from app.adapters.ollama_llm import OllamaLLM
from app.adapters.qdrant.document_repository import QdrantDocumentRepository
from app.adapters.qdrant.vector_search import QdrantVectorSearch
from app.adapters.rq.connection import ingestion_queue, redis_connection
from app.adapters.rq.task_queue import RQTaskQueue
from app.adapters.sqlite.conversation_repository import SQLiteConversationRepository
from app.api.security import decode_token
from app.bootstrap.settings import settings
from app.ports.conversation_repository import ConversationRepositoryPort
from app.ports.document_repository import DocumentRepositoryPort
from app.ports.task_queue import TaskQueuePort
from app.services.agent_service import AgentQueryService
from app.services.ingestion_service import IngestionService
from app.services.moderation_service import ModerationService
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        return decode_token(token)
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token is invalid or expired.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def get_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant


def get_ollama_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.ollama_http_client


def get_conversations_db(request: Request) -> sqlite3.Connection:
    return request.app.state.conversations_db


def get_conversation_repository(
    connection: sqlite3.Connection = Depends(get_conversations_db),
) -> ConversationRepositoryPort:
    return SQLiteConversationRepository(connection)


def get_redis_connection() -> Redis:
    return redis_connection


def get_document_repository(
    qdrant: QdrantClient = Depends(get_qdrant),
) -> DocumentRepositoryPort:
    return QdrantDocumentRepository(qdrant)


def get_task_queue() -> TaskQueuePort:
    return RQTaskQueue(ingestion_queue)


def get_ingestion_service(
    repository: DocumentRepositoryPort = Depends(get_document_repository),
    task_queue: TaskQueuePort = Depends(get_task_queue),
) -> IngestionService:
    return IngestionService(repository, task_queue)


def build_query_service(
    qdrant: QdrantClient,
    connection: sqlite3.Connection,
) -> QueryService:
    return QueryService(
        QdrantVectorSearch(qdrant),
        E5Embeddings(),
        OllamaLLM(
            settings.ollama_url,
            settings.llm_model,
            timeout=settings.ollama_timeout_seconds,
        ),
        conversation_repository=SQLiteConversationRepository(connection),
        max_history_turns=settings.max_history_turns,
    )


def get_query_service(
    qdrant: QdrantClient = Depends(get_qdrant),
    connection: sqlite3.Connection = Depends(get_conversations_db),
) -> QueryService:
    return build_query_service(qdrant, connection)


def build_agent_query_service(
    qdrant: QdrantClient,
    http_client: httpx.AsyncClient,
    connection: sqlite3.Connection,
) -> AgentQueryService:
    retrieval = RetrievalService(QdrantVectorSearch(qdrant), E5Embeddings())
    moderation = ModerationService(retrieval)
    runtime = PydanticAgentRuntime.for_ollama(
        retrieval,
        ollama_url=settings.ollama_url,
        model=settings.llm_model,
        min_score=settings.min_score,
        http_client=http_client,
    )
    return AgentQueryService(
        moderation,
        runtime,
        conversation_repository=SQLiteConversationRepository(connection),
        max_history_turns=settings.max_history_turns,
    )


def get_agent_query_service(
    qdrant: QdrantClient = Depends(get_qdrant),
    http_client: httpx.AsyncClient = Depends(get_ollama_http_client),
    connection: sqlite3.Connection = Depends(get_conversations_db),
) -> AgentQueryService:
    return build_agent_query_service(qdrant, http_client, connection)
