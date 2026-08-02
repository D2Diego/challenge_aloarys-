import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from app.api.dependencies import enforce_document_upload_rate_limit
from app.api.rate_limit import RedisFixedWindowRateLimiter
from app.api.routers.documents import router


class _FakeRedis:
    def __init__(self):
        self.count = 0
        self.keys = []

    def eval(self, script, number_of_keys, key, window_seconds):
        self.count += 1
        self.keys.append(key)
        return [self.count, window_seconds]


def test_rejects_requests_over_the_limit_with_retry_after():
    redis = _FakeRedis()
    limiter = RedisFixedWindowRateLimiter(
        redis,
        key_prefix="document-upload",
        limit=1,
        window_seconds=60,
    )

    limiter.check("test-user")
    with pytest.raises(HTTPException) as captured:
        limiter.check("test-user")

    assert captured.value.status_code == 429
    assert captured.value.detail["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert captured.value.headers == {"Retry-After": "60"}
    assert "test-user" not in redis.keys[0]


def test_fails_closed_when_redis_is_unavailable():
    class _UnavailableRedis:
        def eval(self, *args):
            raise ConnectionError("unavailable")

    limiter = RedisFixedWindowRateLimiter(
        _UnavailableRedis(),
        key_prefix="document-upload",
        limit=10,
        window_seconds=60,
    )

    with pytest.raises(HTTPException) as captured:
        limiter.check("test-user")

    assert captured.value.status_code == 503
    assert captured.value.detail["error_code"] == "RATE_LIMIT_UNAVAILABLE"


def test_document_upload_endpoint_has_rate_limit_dependency():
    upload_route = next(
        route
        for route in router.routes
        if route.path == "/documents" and "POST" in route.methods
    )

    dependency_calls = {
        dependency.call for dependency in upload_route.dependant.dependencies
    }
    assert enforce_document_upload_rate_limit in dependency_calls
