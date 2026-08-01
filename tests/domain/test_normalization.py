import unicodedata

from app.domain.normalization import normalize_text


def test_collapses_redundant_whitespace():
    raw_text = "a   text\nwith     scattered\n\nspaces"
    assert normalize_text(raw_text) == "a text with scattered spaces"


def test_strips_surrounding_whitespace():
    assert normalize_text("   text with padding   ") == "text with padding"


def test_normalizes_unicode_to_nfc():
    nfc = "naïve café résumé"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfd != nfc
    assert normalize_text(nfd) == nfc
