# ADR 001 - Medallion vs Single-Zone Storage

**Status:** Accepted

**Context:**
Multi-tenant document ingestion needs to separate raw arrival, validated content, and AI-enriched
serving data. A single zone collapses all three concerns and makes audit trails impossible.

**Decision:**
Three-zone Medallion: Bronze (raw, immutable), Silver (validated, structured), Gold (AI-enriched,
serving-ready).

**Consequences:**
Each boundary enforces a quality contract. Bronze is an immutable audit trail - nothing overwrites
it. Corrupt data is rejected at the Silver boundary and never reaches serving. Delta Lake provides
ACID guarantees and time-travel across all zones.
