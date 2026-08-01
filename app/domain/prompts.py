"""Prompt construction for grounded document question answering."""

from app.domain.conversation import ConversationTurn
from app.domain.entities import FoundChunk


def build_prompt(
    question: str,
    chunks: list[FoundChunk],
    history: list[ConversationTurn] | None = None,
) -> str:
    """Build a grounded prompt with numbered sources and optional history."""
    context = "\n\n".join(
        f"[Source {index}]\n{chunk.text}"
        for index, chunk in enumerate(chunks, start=1)
    )
    history_section = ""
    if history:
        history_text = "\n\n".join(
            f"Previous question: {turn.question}\nPrevious answer: {turn.answer}"
            for turn in history
        )
        history_section = f"""Conversation history, ordered from oldest to newest. Use it only to understand the current question. Base the answer exclusively on the context below:
{history_text}

"""

    return f"""You are an assistant that answers questions exclusively from the context below, which was extracted from the user's documents. Do not use external or prior knowledge.

{history_section}Requirements:
1. Use only information present in the context.
2. Cite every claim using the exact format "[Source N]", where N is the corresponding context entry.
3. If the context answers only part of the question, answer that part and state what the available information does not cover.
4. If no context is relevant, state that the information was not found in the documents. Do not invent an answer.
5. Respond directly and concisely in English.

Context:
{context}

Question: {question}

Answer:"""
