from unittest.mock import MagicMock

import app.adapters.e5_embeddings as embeddings_module
from app.adapters.e5_embeddings import E5Embeddings


class _Array:
    def __init__(self, value):
        self._value = value

    def tolist(self):
        return self._value


def test_applies_e5_prefixes_and_normalizes_embeddings(monkeypatch):
    model = MagicMock()
    model.encode.side_effect = [_Array([0.1]), _Array([0.2])]
    monkeypatch.setattr(embeddings_module, "_get_model", lambda: model)
    embeddings = E5Embeddings()

    assert embeddings.embed_query("question") == [0.1]
    assert embeddings.embed_passage("passage") == [0.2]

    assert model.encode.call_args_list[0].args == ("query: question",)
    assert model.encode.call_args_list[1].args == ("passage: passage",)
    for call in model.encode.call_args_list:
        assert call.kwargs == {
            "normalize_embeddings": True,
            "show_progress_bar": False,
        }


def test_embeds_sentences_without_query_or_passage_prefix(monkeypatch):
    model = MagicMock()
    model.encode.return_value = _Array([[0.1], [0.2]])
    monkeypatch.setattr(embeddings_module, "_get_model", lambda: model)

    result = E5Embeddings().embed_sentences(["First.", "Second."])

    assert result == [[0.1], [0.2]]
    assert model.encode.call_args.args == (["First.", "Second."],)


def test_counts_tokens_with_special_tokens(monkeypatch):
    model = MagicMock()
    model.tokenizer.encode.return_value = [1, 2, 3]
    monkeypatch.setattr(embeddings_module, "_get_model", lambda: model)

    assert E5Embeddings().count_tokens("some text") == 3
    model.tokenizer.encode.assert_called_once_with(
        "some text",
        add_special_tokens=True,
    )
