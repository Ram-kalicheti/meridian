"""
api/retrieval/searcher.py

Hybrid (vector + BM25) search against the meridian-docs Azure AI Search index.
Tenant isolation enforced via OData filter on every query.
"""
from __future__ import annotations

import logging
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI

from api.config import EMBEDDING_DIMS, INDEX_NAME, Settings

logger = logging.getLogger(__name__)

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def embed_query(query: str) -> list[float]:
    """
    Embed *query* using text-embedding-3-small via Azure OpenAI.
    Returns a 1536-dim float list.
    """
    s = _get_settings()
    client = AsyncAzureOpenAI(
        azure_endpoint=s.openai_endpoint,
        api_key=s.openai_key,
        api_version="2024-02-01",
    )
    response = await client.embeddings.create(
        input=query,
        model=s.embedding_deployment,
    )
    embedding: list[float] = response.data[0].embedding
    if len(embedding) != EMBEDDING_DIMS:
        logger.warning(
            "embed_query: unexpected embedding dim %d (expected %d)",
            len(embedding),
            EMBEDDING_DIMS,
        )
    return embedding


async def hybrid_search(
    query: str,
    tenant_id: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Run hybrid (vector + BM25) search against the meridian-docs index.

    Args:
        query:     Natural-language query string.
        tenant_id: Tenant to scope results to (OData filter).
        top_k:     Number of results to return.

    Returns:
        List of hit dicts, each containing:
            chunk_id, doc_id, tenant_id, content, section_idx, score
        Ordered descending by combined @search.score.
    """
    s = _get_settings()
    embedding = await embed_query(query)

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=top_k,
        fields="content_vector",  # matches meridian-docs index schema field name
    )

    hits: list[dict[str, Any]] = []
    try:
        async with SearchClient(
            endpoint=s.ai_search_endpoint,
            index_name=INDEX_NAME,
            credential=AzureKeyCredential(s.ai_search_key),
        ) as client:
            results = await client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=f"tenant_id eq '{tenant_id}'",
                select=["chunk_id", "doc_id", "tenant_id", "content", "section_idx"],
                top=top_k,
            )
            async for result in results:
                hits.append(
                    {
                        "chunk_id": result.get("chunk_id", ""),
                        "doc_id": result.get("doc_id", ""),
                        "tenant_id": result.get("tenant_id", tenant_id),
                        "content": result.get("content", ""),
                        "section_idx": result.get("section_idx", 0),
                        "score": result.get("@search.score", 0.0),
                    }
                )
    except Exception as exc:
        logger.warning("hybrid_search: search failed (%s) -- returning empty", exc)

    logger.info(
        "hybrid_search: tenant=%s query_len=%d hits=%d",
        tenant_id,
        len(query),
        len(hits),
    )
    return hits
