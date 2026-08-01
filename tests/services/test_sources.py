from uuid import uuid4

from app.domain.entities import FoundChunk
from app.services.sources import build_sources


def _chunk(text: str) -> FoundChunk:
    return FoundChunk(
        document_id=uuid4(),
        document_name="document.pdf",
        page=1,
        chunk_index=0,
        text=text,
        score=0.9,
    )


def test_filters_sources_by_cited_indexes():
    sources = build_sources([_chunk("A"), _chunk("B")], cited_indexes={1})

    assert len(sources) == 1
    assert sources[0].excerpt == "A"


def test_returns_all_sources_when_no_indexes_are_cited():
    sources = build_sources([_chunk("A"), _chunk("B")], cited_indexes=set())

    assert len(sources) == 2
