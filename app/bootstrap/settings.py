"""Environment-based application settings."""

import os
from dataclasses import dataclass, field

from app.ports.vector_search import MIN_SCORE, TOP_K_DEFAULT


def _parse_cors_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    qdrant_url: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
    ollama_url: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    llm_model: str = os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")
    ollama_timeout_seconds: float = float(
        os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")
    )
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    top_k_default: int = int(os.environ.get("TOP_K_DEFAULT", TOP_K_DEFAULT))
    min_score: float = float(os.environ.get("MIN_SCORE", MIN_SCORE))
    max_upload_size_mb: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "20"))
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _parse_cors_origins(
            os.environ.get("CORS_ORIGINS", "http://localhost:5173")
        )
    )
    admin_username: str = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "change-this-password")
    jwt_secret: str = os.environ.get("JWT_SECRET", "change-this-secret-in-production")
    max_history_turns: int = int(os.environ.get("MAX_HISTORY_TURNS", "5"))
    sqlite_db_path: str = os.environ.get("SQLITE_DB_PATH", "./conversations.db")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
