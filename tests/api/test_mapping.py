from uuid import uuid4

from app.api.mapping import to_query_response, to_stream_payload
from app.services.query_service import (
    QueryCompletedEvent,
    QueryResult,
    QueryTokenEvent,
)
from app.services.sources import QuerySource


def _source() -> QuerySource:
    return QuerySource(
        document_id=uuid4(),
        document_name="contract.pdf",
        page=2,
        excerpt="The term is 30 days.",
        score=0.91,
    )


def test_maps_internal_result_to_http_contract():
    source = _source()

    response = to_query_response(
        QueryResult(answer="Answer [Source 1].", sources=[source])
    )

    assert response.answer == "Answer [Source 1]."
    assert response.sources[0].document_id == source.document_id
    assert response.sources[0].excerpt == source.excerpt


def test_maps_internal_events_to_websocket_payloads():
    source = _source()

    token = to_stream_payload(QueryTokenEvent(text="part"))
    completed = to_stream_payload(
        QueryCompletedEvent(answer="Answer [Source 1].", sources=[source])
    )

    assert token == {"type": "token", "text": "part"}
    assert completed["type"] == "complete"
    assert completed["sources"][0]["document_id"] == str(source.document_id)
