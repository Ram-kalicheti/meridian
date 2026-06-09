CREATE TABLE dim_documents (
    doc_id           VARCHAR(256)  NOT NULL,
    raw_path         VARCHAR(1024) NOT NULL,
    doc_type         VARCHAR(64)   NOT NULL,
    tenant_id        VARCHAR(64)   NOT NULL,
    batch_date       DATE          NOT NULL,
    bronze_landed_at DATETIME2(6)    NOT NULL
);
