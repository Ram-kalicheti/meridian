"""
api/retrieval/reranker.py

Cross-encoder style reranking via a single batched Azure OpenAI prompt.
Asks the model to score each retrieved chunk's relevance to the query (0.0-1.0).
Falls back to the original hybrid search order on any scoring failure.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncAzureOpenAI

from api.config import Settings

logger = logging.getLogger(__name__)

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


_RERANK_SYSTEM = (
    "You are a relevance scorer. "
    "Given a query and a list of text passages, return ONLY a JSON array of "
    "floating-point relevance scores between 0.0 and 1.0, one per passage, "
    "in the same order as the passages. "
    "Do not include any other text, explanation, or markdown."
)


def _build_rerank_prompt(query: str, hits: list[dict[str, Any]]) -> str:
    lines = [f'Query: "{query}"', "", "Passages:"]
    for i, hit in enumerate(hits, start=1):
        # Truncate to 400 chars to stay within a single prompt comfortably.
        snippet = hit["content"][:400].replace("\n", " ")
        lines.append(f"{i}. {snippet}")
    return "\n".join(lines)


async def rerank(
    query: str,
    hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Rerank *hits* by relevance to *query* using Azure OpenAI.

    A single prompt scores all passages in one call.
    Returned list is sorted descending by relevance_score.
    Each hit dict gains a 'relevance_score' float field.

    Falls back to original order (scores preserved from hybrid search)
    if the LLM response cannot be parsed.
    """
    if not hits:
        return hits

    s = _get_settings()
    client = AsyncAzureOpenAI(
        azure_endpoint=s.openai_endpoint,
        api_key=s.openai_key,
        api_version="2024-02-01",
    )

    prompt = _build_rerank_prompt(query, hits)

    try:
        response = await client.chat.completions.create(
            model=s.chat_deployment,
            messages=[
                {"role": "system", "content": _RERANK_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=64,
        )
        raw = response.choices[0].message.content or "[]"
        
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        scores: list[float] = json.loads(raw)

        if len(scores) != len(hits):
            raise ValueError(
                f"score count mismatch: got {len(scores)}, expected {len(hits)}"
            )

        for hit, score in zip(hits, scores):
            hit["relevance_score"] = float(score)

        reranked = sorted(hits, key=lambda h: h["relevance_score"], reverse=True)
        logger.info(
            "rerank: %d hits scored, top relevance=%.3f",
            len(reranked),
            reranked[0]["relevance_score"] if reranked else 0.0,
        )
        return reranked

    except Exception as exc:
        logger.warning("rerank: scoring failed (%s) -- using original order", exc)
        for hit in hits:
            hit.setdefault("relevance_score", hit.get("score", 0.0))
        return hits
