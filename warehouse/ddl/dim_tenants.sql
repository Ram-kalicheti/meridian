CREATE TABLE dim_tenants (
    tenant_id   VARCHAR(64)  NOT NULL,
    tenant_name VARCHAR(128) NOT NULL,
    created_at  DATETIME2(6)    NOT NULL
);
