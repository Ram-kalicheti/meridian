CREATE VIEW vw_ingestion_quality_by_tenant AS
SELECT
    tenant_id,
    COUNT(*)                                                        AS total_chunks,
    SUM(CAST(dq_passed AS INT))                                     AS passed_chunks,
    COUNT(*) - SUM(CAST(dq_passed AS INT))                          AS rejected_chunks,
    CAST(SUM(CAST(dq_passed AS INT)) AS FLOAT) / NULLIF(COUNT(*), 0) * 100 AS pass_rate_pct
FROM fact_doc_chunks
GROUP BY tenant_id;

GO

CREATE VIEW vw_doc_coverage_daily AS
SELECT
    f.date_key,
    d.full_date,
    f.tenant_id,
    f.doc_type,
    COUNT(DISTINCT f.doc_id) AS document_count,
    COUNT(*)                 AS total_chunks,
    AVG(f.content_length)    AS avg_chunk_length
FROM fact_doc_chunks f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY f.date_key, d.full_date, f.tenant_id, f.doc_type;

GO

-- latency measured from first bronze file landed to last silver or gold write in the batch
CREATE VIEW vw_pipeline_latency_bronze_to_gold AS
SELECT
    date_key,
    tenant_id,
    MIN(bronze_landed_at)                                                      AS batch_bronze_start,
    MAX(silver_processed_at)                                                   AS batch_silver_end,
    MAX(gold_enriched_at)                                                      AS batch_gold_end,
    DATEDIFF(SECOND, MIN(bronze_landed_at), MAX(silver_processed_at))         AS bronze_to_silver_sec,
    DATEDIFF(SECOND, MIN(bronze_landed_at), MAX(gold_enriched_at))            AS bronze_to_gold_sec
FROM fact_doc_chunks
GROUP BY date_key, tenant_id;
