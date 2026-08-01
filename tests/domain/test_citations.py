"""Tests for citation extraction."""

from app.domain.citations import extract_citations


def test_extracts_cited_source_indexes():
    text = "The term is 30 days [Source 1]. It then renews automatically [Source 2]."
    assert extract_citations(text) == {1, 2}


def test_returns_empty_set_when_response_has_no_citations():
    assert extract_citations("No citations appear in this response.") == set()


def test_deduplicates_repeated_citations():
    assert extract_citations("[Source 1] and [Source 1] again.") == {1}
