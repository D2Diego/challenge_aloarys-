"""Citation extraction from language model responses."""

import re

_CITATION_RE = re.compile(r"\[Source (\d+)\]")


def extract_citations(text: str) -> set[int]:
    """Return the one-based source indexes cited in a response."""
    return {int(index) for index in _CITATION_RE.findall(text)}
