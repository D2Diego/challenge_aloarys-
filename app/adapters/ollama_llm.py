"""Ollama language model adapter."""

import json
from collections.abc import AsyncIterator

import httpx

from app.domain.conversation import TokenUsage
from app.ports.llm import LLMResponse, LLMTextChunk, LLMUsageChunk

_OLLAMA_GENERATE_PATH = "/api/generate"


class OllamaLLM:
    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def generate_response(self, prompt: str) -> LLMResponse:
        response = httpx.post(
            f"{self._base_url}{_OLLAMA_GENERATE_PATH}",
            json={"model": self._model, "prompt": prompt, "stream": False},
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        usage = TokenUsage(
            prompt_tokens=payload.get("prompt_eval_count") or 0,
            completion_tokens=payload.get("eval_count") or 0,
        )
        return LLMResponse(text=payload["response"].strip(), usage=usage)

    async def generate_response_stream(
        self,
        prompt: str,
    ) -> AsyncIterator[LLMTextChunk | LLMUsageChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}{_OLLAMA_GENERATE_PATH}",
                json={"model": self._model, "prompt": prompt, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    text = payload.get("response", "")
                    if text:
                        yield LLMTextChunk(text=text)
                    if payload.get("done"):
                        yield LLMUsageChunk(
                            usage=TokenUsage(
                                prompt_tokens=payload.get("prompt_eval_count") or 0,
                                completion_tokens=payload.get("eval_count") or 0,
                            )
                        )
                        break
