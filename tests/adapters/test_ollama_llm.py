from unittest.mock import AsyncMock, MagicMock

import app.adapters.ollama_llm as ollama_llm_module
from app.adapters.ollama_llm import OllamaLLM
from app.ports.llm import LLMTextChunk, LLMUsageChunk


def test_returns_text_and_token_usage(monkeypatch):
    response = MagicMock()
    response.json.return_value = {
        "response": "Answer using [Source 1].",
        "prompt_eval_count": 42,
        "eval_count": 8,
    }
    post = MagicMock(return_value=response)
    monkeypatch.setattr(ollama_llm_module.httpx, "post", post)

    result = OllamaLLM(
        "http://ollama:11434",
        "qwen2.5:7b-instruct",
    ).generate_response("prepared prompt")

    assert result.text == "Answer using [Source 1]."
    assert result.usage.prompt_tokens == 42
    assert result.usage.completion_tokens == 8
    post.assert_called_once()
    assert post.call_args.args[0] == "http://ollama:11434/api/generate"
    assert post.call_args.kwargs["json"] == {
        "model": "qwen2.5:7b-instruct",
        "prompt": "prepared prompt",
        "stream": False,
    }


def test_uses_zero_when_token_counts_are_missing(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"response": "text"}
    monkeypatch.setattr(
        ollama_llm_module.httpx,
        "post",
        MagicMock(return_value=response),
    )

    result = OllamaLLM("http://ollama:11434", "model").generate_response("prompt")

    assert result.usage.prompt_tokens == 0
    assert result.usage.completion_tokens == 0


async def test_streams_text_and_final_usage(monkeypatch):
    lines = [
        '{"response": "Hello ", "done": false}',
        '{"response": "world", "done": false}',
        '{"response": "", "done": true, "prompt_eval_count": 15, "eval_count": 6}',
    ]

    async def iterate_lines():
        for line in lines:
            yield line

    response = MagicMock()
    response.aiter_lines = iterate_lines
    response.raise_for_status = MagicMock()

    stream_context = MagicMock()
    stream_context.__aenter__ = AsyncMock(return_value=response)
    stream_context.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.stream = MagicMock(return_value=stream_context)
    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client)
    client_context.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        ollama_llm_module.httpx,
        "AsyncClient",
        MagicMock(return_value=client_context),
    )

    events = [
        event
        async for event in OllamaLLM(
            "http://ollama:11434",
            "model",
        ).generate_response_stream("prompt")
    ]

    texts = [event.text for event in events if isinstance(event, LLMTextChunk)]
    assert texts == ["Hello ", "world"]

    usage_events = [event for event in events if isinstance(event, LLMUsageChunk)]
    assert len(usage_events) == 1
    assert usage_events[0].usage.prompt_tokens == 15
    assert usage_events[0].usage.completion_tokens == 6

    client.stream.assert_called_once()
    assert client.stream.call_args.args == (
        "POST",
        "http://ollama:11434/api/generate",
    )
    assert client.stream.call_args.kwargs["json"] == {
        "model": "model",
        "prompt": "prompt",
        "stream": True,
    }
