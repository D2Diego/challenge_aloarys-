"""Moderated agent query endpoint."""

import logging

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent_query_service, get_current_user
from app.api.mapping import to_query_response
from app.api.schemas import QueryRequest, QueryResponse
from app.bootstrap.settings import settings
from app.services.agent_service import AgentQueryService

logger = logging.getLogger("app")
router = APIRouter(tags=["agent"], dependencies=[Depends(get_current_user)])


@router.post("/agent/query", response_model=QueryResponse)
async def agent_query_endpoint(
    request: QueryRequest,
    service: AgentQueryService = Depends(get_agent_query_service),
):
    document_ids = (
        [str(document_id) for document_id in request.document_ids]
        if request.document_ids
        else None
    )
    result = service.answer_question(
        request.question,
        document_ids=document_ids,
        top_k=request.top_k or settings.top_k_default,
        min_score=settings.min_score,
        conversation_id=request.conversation_id,
    )
    logger.info(
        "agent_query_answered",
        extra={
            "question_length": len(request.question),
            "source_count": len(result.sources),
        },
    )
    return to_query_response(result)
