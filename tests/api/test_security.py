import pytest

from app.api.security import create_access_token, decode_token


def test_token_round_trip():
    token = create_access_token("admin")
    assert decode_token(token) == "admin"


def test_invalid_token_raises_stable_error():
    with pytest.raises(ValueError, match="Token is invalid or expired"):
        decode_token("invalid-token")
