CREATE TABLE fact_doc_chunks (
    chunk_id             VARCHAR(256) NOT NULL,
    doc_id               VARCHAR(256) NOT NULL,
    tenant_id            VARCHAR(64)  NOT NULL,
    date_key             INT          NOT NULL,
    section_idx          INT          NOT NULL,
    content_length       INT          NOT NULL,
    section_count        INT          NOT NULL,
    doc_type             VARCHAR(64)  NOT NULL,
    dq_passed            BIT          NOT NULL,
    error_reason         VARCHAR(512) NULL,
    error_type           VARCHAR(128) NULL,
    bronze_landed_at     DATETIME2(6)    NOT NULL,
    silver_processed_at  DATETIME2(6)    NOT NULL,
    gold_enriched_at     DATETIME2(6)    NULL        -- populated by notebook 02 on day 8
);
