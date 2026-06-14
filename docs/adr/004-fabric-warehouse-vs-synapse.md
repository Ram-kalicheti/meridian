# ADR 004 - Fabric Warehouse vs Azure Synapse Analytics

**Status:** Accepted

**Context:**
The analytics layer needs a SQL endpoint that integrates with the Fabric Lakehouse and serves
Power BI with minimal latency. Both Fabric Warehouse and Synapse Analytics are available on the
subscription.

**Decision:**
Fabric Warehouse. Same workspace as the Lakehouse eliminates cross-service auth complexity. Power
BI DirectLake mode reads Delta files directly, removing the import/DirectQuery latency tradeoff.

**Consequences:**
DirectLake is restricted to base tables - SQL views are analytics-only and excluded from the
semantic model. The distributed SQL engine does not support recursive CTEs, GENERATE_SERIES, or
bare DATETIME2 - all required explicit workarounds via PySpark notebooks. These are known engine
constraints, not regressions from Synapse.
