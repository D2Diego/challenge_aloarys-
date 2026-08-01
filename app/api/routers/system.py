"""Dependency health and process status endpoints."""

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient
from redis import Redis

from app.api.dependencies import (
    get_current_user,
    get_document_repository,
    get_qdrant,
    get_redis_connection,
)
from app.api.schemas import DependencyStatus, HealthResponse, StatusResponse
from app.bootstrap.settings import settings
from app.ports.document_repository import DocumentRepositoryPort

router = APIRouter(tags=["system"])
_PROCESS_STARTED_AT = time.monotonic()


def _uptime_seconds() -> float:
    return time.monotonic() - _PROCESS_STARTED_AT


@router.get("/health", response_model=HealthResponse)
async def health_endpoint(
    qdrant: QdrantClient = Depends(get_qdrant),
    redis: Redis = Depends(get_redis_connection),
):
    dependencies = {
        "qdrant": DependencyStatus.OK,
        "ollama": DependencyStatus.OK,
        "redis": DependencyStatus.OK,
    }
    try:
        qdrant.get_collections()
    except Exception:
        dependencies["qdrant"] = DependencyStatus.ERROR
    try:
        response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=5.0)
        response.raise_for_status()
    except Exception:
        dependencies["ollama"] = DependencyStatus.ERROR
    try:
        redis.ping()
    except Exception:
        dependencies["redis"] = DependencyStatus.ERROR

    overall_status = (
        DependencyStatus.OK
        if all(status == DependencyStatus.OK for status in dependencies.values())
        else DependencyStatus.ERROR
    )
    body = HealthResponse(status=overall_status, dependencies=dependencies)
    if overall_status == DependencyStatus.ERROR:
        raise HTTPException(status_code=503, detail=body.model_dump())
    return body


@router.get(
    "/status",
    response_model=StatusResponse,
    dependencies=[Depends(get_current_user)],
)
async def status_endpoint(
    repository: DocumentRepositoryPort = Depends(get_document_repository),
):
    return StatusResponse(
        total_documents=repository.count(),
        uptime_seconds=_uptime_seconds(),
    )
