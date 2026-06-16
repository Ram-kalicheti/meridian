# Meridian

Multi-tenant AI document intelligence platform on Microsoft Fabric OneLake.

At KPMG I maintained 12 separate point-to-point document integrations for 8 enterprise clients. Every new client added another integration. There was no shared query layer, no unified audit trail, and no way to ask a question across tenants without touching each system individually. Meridian is what I would have built instead.

## Architecture

Documents flow through three zones on ADLS Gen2 via ADF:

**Bronze** — immutable raw copy of every ingested file, partitioned by tenant and date. ADF BlobToBronze copies files from the tenant drop zone without transformation. Bronze is never overwritten.

**Silver** — validated structured chunks. A Fabric Spark notebook runs Azure Document Intelligence layout extraction, splits content at section boundaries using SectionSplitter (not fixed token sizes — this matters, see ADR 003), and enforces a six-check DQ suite before writing to Delta. Fixed-size chunking at 512 tokens returned context_precision of 0.71. Section-boundary chunking returned 0.87. The difference is that fixed-size splits cut across section headings, destroying the context that makes retrieval work.

**Gold** — AI-enriched serving layer. A second Fabric Spark notebook generates embeddings via Azure OpenAI text-embedding-3-small and upserts chunks to Azure AI Search with HNSW vector index and semantic configuration.

**API** — FastAPI SSE endpoint behind Azure APIM. Per-tenant token budgets enforced via Redis incrby atomic counter. Hybrid vector + BM25 retrieval, cross-encoder reranking, context assembly, gpt-4o-mini streaming. 30%+ semantic cache hit rate via cosine similarity at 0.95 threshold.

**Observability** — OpenTelemetry traces exported to App Insights. rag.query spans tagged with tenant_id for per-tenant latency and cost attribution.

**Quality gate** — RAGAS context_precision scored via direct Azure OpenAI calls — ragas.evaluate() is bypassed entirely (see bug 1 below). Gate blocks merges below 0.85. Final score: 0.92.

**Data at rest** — 102 chunks across 3 tenants (acme, contoso, fabrikam) in the Fabric Warehouse star schema. Power BI DirectLake dashboard with Ingestion Quality and Doc Coverage pages.

## What I learned the hard way

### 1. RAGAS on Windows fails silently — bypass the library entirely

ragas.evaluate() with LangchainLLMWrapper fails on Windows due to asyncio SSL
event loop policy. asyncio.WindowsSelectorEventLoopPolicy does not fix it.
The fix: bypass ragas.evaluate() and use direct synchronous AzureOpenAI API
calls for context_precision scoring. ragas==0.1.21 is still installed for the
Dataset format — just not the evaluation runner.
See: eval/run.py uses direct AzureOpenAI client, not ragas.evaluate()

### 2. Azure Redis Cache requires rediss:// not redis:// (2 hours lost)

Azure Cache for Redis requires SSL on port 6380 and the rediss:// scheme
(double-s). Using redis:// port 6379 produces a connection that appears to
succeed but fails silently on every operation. Always use rediss:// for Azure.

### 3. VectorizedQuery field name must match index schema exactly

Azure AI Search VectorizedQuery returns 0 results silently if the field name
is wrong. The meridian-docs index uses content_vector — not the generic name
"embedding". No error is raised. Always verify field names with:
az search index show --name meridian-docs --service-name <your-service>

### 4. Docker --env-file requires absolute path on Windows

docker run --env-file ~/meridian/.env starts without error but env vars are
silently missing. Fix: use C:/Users/USER/meridian/.env (absolute Windows path).
Tilde expansion does not work for Docker --env-file on Windows.

## Running locally

```bash
cp .env.sample .env
# fill in Key Vault secret values
docker build -t meridian-api .
docker run --env-file C:/Users/USER/meridian/.env -p 8000:8000 meridian-api
curl http://localhost:8000/health
```

## Evaluation

```bash
export QUERY_ENDPOINT=https://your-container-app-url
export OPENAI_ENDPOINT=https://your-openai-endpoint
export OPENAI_KEY=your-key
export AI_SEARCH_ENDPOINT=https://your-search-endpoint
export AI_SEARCH_KEY=your-key
python -m eval.run
python -m eval.gate
```

context_precision threshold: 0.85
final score: 0.92