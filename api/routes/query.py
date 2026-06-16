"""
api/routes/query.py

POST /query  -- multi-tenant RAG endpoint with SSE streaming.

Pipeline:
  1. Token pre-flight reservation (TokenBudget)
  2. Redis semantic cache lookup  (cosine >= SEMANTIC_CACHE_THRESHOLD -> cache hit)
  3. Hybrid vector + BM25 search  (searcher.hybrid_search)
  4. LLM reranking                (reranker.rerank)
  5. Context assembly             (assembler.assemble_context)
  6. Azure OpenAI streaming chat  (gpt-4o-mini, SSE)
  7. Cache write                  (store embedding + full response)
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from api.auth import require_tenant
from api.config import SEMANTIC_CACHE_THRESHOLD, Settings
from api.retrieval.assembler import assemble_context, build_rag_system_prompt
from api.retrieval.reranker import rerank
from api.retrieval.searcher import embed_query, hybrid_search
from api.router.token_budget import get_token_budget, TokenBudget
from telemetry.tracing import get_tracer

_tracer = get_tracer(__name__)

logger = logging.getLogger(__name__)
query_router = APIRouter()

_PREFLIGHT_TOKENS = 500
_CACHE_TTL_SECONDS = 86_400
_CACHE_KEY_PREFIX = "semcache"

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


async def _cache_lookup(
    redis: aioredis.Redis | None,
    tenant_id: str,
    embedding: list[float],
) -> str | None:
    """
    Scan Redis for a semantically similar cached query for this tenant.
    Returns the cached response string if cosine similarity >= threshold, else None.
    """
    if redis is None:
        return None
    pattern = f"{_CACHE_KEY_PREFIX}:{tenant_id}:*"
    try:
        keys = await redis.keys(pattern)
        for key in keys:
            raw = await redis.get(key)
            if raw is None:
                continue
            entry: dict = json.loads(raw)
            cached_emb: list[float] = entry["embedding"]
            similarity = _cosine(embedding, cached_emb)
            if similarity >= SEMANTIC_CACHE_THRESHOLD:
                logger.info(
                    "cache hit: key=%s similarity=%.4f", key, similarity
                )
                return entry["response"]
    except Exception as exc:
        logger.warning("cache_lookup failed: %s", exc)
    return None


async def _cache_write(
    redis: aioredis.Redis | None,
    tenant_id: str,
    embedding: list[float],
    response: str,
) -> None:
    """Write a new entry to the semantic cache with a 24-hour TTL."""
    if redis is None:
        return
    key = f"{_CACHE_KEY_PREFIX}:{tenant_id}:{uuid.uuid4().hex}"
    payload = json.dumps({"embedding": embedding, "response": response})
    try:
        await redis.set(key, payload, ex=_CACHE_TTL_SECONDS)
        logger.info("cache write: key=%s", key)
    except Exception as exc:
        logger.warning("cache_write failed: %s", exc)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream_cached(response_text: str) -> AsyncGenerator[str, None]:
    """Re-stream a cache hit as SSE chunks (word-by-word for UX parity)."""
    # emit empty sources so clients and eval always receive a sources event
    yield _sse({"type": "sources", "sources": []})
    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yield _sse({"type": "token", "content": chunk})
    yield _sse({"type": "done", "cached": True})


async def _stream_openai(
    client: AsyncAzureOpenAI,
    chat_deployment: str,
    system_prompt: str,
    query: str,
    sources: list[dict],
    redis: aioredis.Redis,
    tenant_id: str,
    embedding: list[float],
) -> AsyncGenerator[str, None]:
    """
    Stream the Azure OpenAI chat completion as SSE.
    Accumulates the full response for cache write after streaming.
    """
    full_response: list[str] = []

    # Emit sources first so the client can render citations immediately.
    yield _sse({"type": "sources", "sources": sources})

    stream = await client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        stream=True,
        temperature=0.2,
        max_tokens=1024,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            full_response.append(delta.content)
            yield _sse({"type": "token", "content": delta.content})

    response_text = "".join(full_response)
    yield _sse({"type": "done", "cached": False})

    await _cache_write(redis, tenant_id, embedding, response_text)


@query_router.post("/query")
async def post_query(
    body: QueryRequest,
    request: Request,
    tenant_id: str = Depends(require_tenant),
    budget: TokenBudget = Depends(get_token_budget),
) -> StreamingResponse:
    """
    Multi-tenant RAG query endpoint with SSE streaming.

    Headers required:
        X-Tenant-ID: acme | contoso | fabrikam

    Returns:
        text/event-stream -- sequence of SSE events:
            {"type": "sources",  "sources": [...]}
            {"type": "token",    "content": "..."}   (one per streamed token)
            {"type": "done",     "cached": bool}
    """
    # 1. Pre-flight token reservation.
    await budget.check_and_reserve(tenant_id, _PREFLIGHT_TOKENS)

    s = _get_settings()
    redis: aioredis.Redis = request.app.state.redis
    oai = AsyncAzureOpenAI(
        azure_endpoint=s.openai_endpoint,
        api_key=s.openai_key,
        api_version="2024-02-01",
    )

    # 2. Embed the query (needed for both cache lookup and search).
    embedding = await embed_query(body.query)

    # 3. Semantic cache lookup.
    cached = await _cache_lookup(redis, tenant_id, embedding)
    if cached is not None:
        return StreamingResponse(
            _stream_cached(cached),
            media_type="text/event-stream",
        )

    # 4. Hybrid search + rerank + context assembly  (traced as a single retrieval span).
    with _tracer.start_as_current_span("rag.query") as span:
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("query.length", len(body.query))

        hits = await hybrid_search(
            query=body.query,
            tenant_id=tenant_id,
            top_k=body.top_k,
        )

        if not hits:
            async def _no_results() -> AsyncGenerator[str, None]:
                yield _sse({"type": "sources", "sources": []})
                yield _sse({"type": "token", "content": "No relevant documents found for your query."})
                yield _sse({"type": "done", "cached": False})

            return StreamingResponse(_no_results(), media_type="text/event-stream")

        # 5. Rerank.
        reranked = await rerank(query=body.query, hits=hits)

        # 6. Assemble context.
        context_str, sources = assemble_context(reranked)
        system_prompt = build_rag_system_prompt(context_str)

    # 7. Stream via Azure OpenAI + async cache write.
    return StreamingResponse(
        _stream_openai(
            client=oai,
            chat_deployment=s.chat_deployment,
            system_prompt=system_prompt,
            query=body.query,
            sources=sources,
            redis=redis,
            tenant_id=tenant_id,
            embedding=embedding,
        ),
        media_type="text/event-stream",
    )