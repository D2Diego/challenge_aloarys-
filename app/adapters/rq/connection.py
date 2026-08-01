"""Shared Redis and RQ resources."""

from redis import Redis
from rq import Queue

from app.bootstrap.settings import settings

redis_connection = Redis.from_url(settings.redis_url)
ingestion_queue = Queue("ingestion", connection=redis_connection)
