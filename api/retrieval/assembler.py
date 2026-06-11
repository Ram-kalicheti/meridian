"""
api/retrieval/assembler.py

Assembles reranked search hits into a single context string for the RAG prompt.
Enforces a soft token ceiling and returns source attribution metadata.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4

# Context window for gpt-4o-mini is 128k tokens; we budget 6k for retrieval context.
_MAX_CONTEXT_TOKENS = 6_000
_MAX_CONTEXT_CHARS = _MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN  # 24000 chars


def assemble_context(
    hits: list[dict[str, Any]],
    max_tokens: int = _MAX_CONTEXT_TOKENS,
) -> tuple[str, list[dict[str, str]]]:
    """
    Format reranked hits into a numbered context block and a source list.

    Args:
        hits:       Reranked list of hit dicts from reranker.rerank().
        max_tokens: Soft cap on context length (approximate token count).

    Returns:
        (context_str, sources)
        context_str -- numbered passages ready for RAG system prompt injection.
        sources      -- list of {"chunk_id": ..., "doc_id": ..., "section_idx": ...}
                       in context order, for response citation.
    """
    max_chars = max_tokens * _CHARS_PER_TOKEN
    sections: list[str] = []
    sources: list[dict[str, str]] = []
    total_chars = 0

    for i, hit in enumerate(hits, start=1):
        content = hit.get("content", "").strip()
        if not content:
            continue

        entry = f"[{i}] (doc: {hit['doc_id']} | chunk: {hit['chunk_id']})\n{content}"
        entry_chars = len(entry)

        if total_chars + entry_chars > max_chars:
            logger.info(
                "assemble_context: stopping at hit %d/%d -- char budget reached",
                i - 1,
                len(hits),
            )
            break

        sections.append(entry)
        sources.append(
            {
                "chunk_id": hit.get("chunk_id", ""),
                "doc_id": hit.get("doc_id", ""),
                "section_idx": str(hit.get("section_idx", 0)),
            }
        )
        total_chars += entry_chars

    context_str = "\n\n".join(sections)
    logger.info(
        "assemble_context: %d/%d hits included, ~%d tokens",
        len(sections),
        len(hits),
        total_chars // _CHARS_PER_TOKEN,
    )
    return context_str, sources


_RAG_SYSTEM_TEMPLATE = """\
You are Meridian, a multi-tenant document intelligence assistant.
Answer the user's question using ONLY the retrieved context passages below.
If the answer is not present in the context, say so -- do not hallucinate.
Cite passage numbers like [1], [2] when you use them.

Retrieved context:
{context}
"""


def build_rag_system_prompt(context_str: str) -> str:
    """Return the full system prompt with context injected."""
    return _RAG_SYSTEM_TEMPLATE.format(context=context_str)
