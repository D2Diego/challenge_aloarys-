"""Atomic Redis-backed rate limiting for sensitive HTTP operations."""

import hashlib

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError

from app.api.errors import http_error

_FIXED_WINDOW_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {current, redis.call('TTL', KEYS[1])}
"""


class RedisFixedWindowRateLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        key_prefix: str,
        limit: int,
        window_seconds: int,
    ):
        self._redis = redis
        self._key_prefix = key_prefix
        self._limit = limit
        self._window_seconds = window_seconds

    def check(self, subject: str) -> None:
        subject_digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()
        key = f"rate-limit:{self._key_prefix}:{subject_digest}"
        try:
            count, ttl = self._redis.eval(
                _FIXED_WINDOW_SCRIPT,
                1,
                key,
                self._window_seconds,
            )
        except RedisError as error:
            raise http_error(
                503,
                "RATE_LIMIT_UNAVAILABLE",
                "Document uploads are temporarily unavailable.",
            ) from error

        if int(count) > self._limit:
            retry_after = int(ttl)
            if retry_after < 1:
                retry_after = self._window_seconds
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Document upload rate limit exceeded.",
                },
                headers={"Retry-After": str(retry_after)},
            )
