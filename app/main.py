"""FastAPI application assembly and process lifecycle."""

import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.qdrant.client import ensure_collection, get_qdrant_client
from app.adapters.qdrant.document_repository import QdrantDocumentRepository
from app.adapters.sqlite.connection import open_connection
from app.api.routers import (
    auth,
    chat,
    conversations,
    documents,
    query,
    system,
)
from app.bootstrap.logging import configure_logging, get_request_id, new_request_id
from app.bootstrap.settings import settings

configure_logging(level=settings.log_level)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.qdrant = get_qdrant_client(settings.qdrant_url)
    ensure_collection(application.state.qdrant)
    stuck_documents = QdrantDocumentRepository(
        application.state.qdrant
    ).reconcile_stuck_processing()
    if stuck_documents:
        logger.warning(
            "stuck_documents_reconciled",
            extra={"document_count": stuck_documents},
        )
    application.state.conversations_db = open_connection(settings.sqlite_db_path)
    application.state.ollama_http_client = httpx.AsyncClient(
        timeout=settings.ollama_timeout_seconds
    )
    yield
    await application.state.ollama_http_client.aclose()
    application.state.conversations_db.close()


app = FastAPI(title="AI Document Analyst", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    new_request_id()
    started_at = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "method": request.method},
        )
        raise
    duration_ms = round((time.monotonic() - started_at) * 1000, 2)
    logger.info(
        "request_handled",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = get_request_id()
    return response


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(system.router)
