# ADR 003 - Delta Lake over Parquet and SectionSplitter over Fixed-Size Chunking

**Status:** Accepted

**Context:**
Two decisions are coupled - storage format and chunking strategy both affect retrieval quality and
pipeline correctness.

Parquet is append-only. Correcting a DQ rejection requires a full table rewrite. Fixed-size chunking
at 512 tokens returned a RAGAS context_precision of 0.71, below the 0.85 gate threshold. Section
heading context was separated by fixed-size splits, fragmenting policy clauses across chunk
boundaries.

**Decision:**
Delta Lake for all Medallion zones - MERGE supports idempotent upserts, time-travel preserves the
full audit history, ACID guarantees prevent partial writes from failed Spark jobs.

SectionSplitter using the Document Intelligence layout model - chunks at heading boundaries, tables
are never split across chunk boundaries, chunk IDs are deterministic from doc_id and section index.

**Consequences:**
context_precision rose from 0.71 to 0.87 after switching to SectionSplitter. The tradeoff is
variable-length chunks (50 to 2000 tokens) - the embedding layer handles this without modification.
