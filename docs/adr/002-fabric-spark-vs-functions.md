# ADR 002 - Fabric Spark Notebooks vs Azure Functions

**Status:** Accepted

**Context:**
Document Intelligence processing of large multi-page PDFs can exceed 10 minutes. Azure Functions
Consumption tier enforces a hard 10-minute execution limit. Chunking and embedding loops for large
batches amplify this further.

**Decision:**
Fabric Spark notebooks as the primary transformation runtime. F2 capacity provisioned via personal
Azure account after all 7 free trial paths were exhausted (GMU tenant block, personal email
rejection, M365 developer program ineligibility, Entra ID admin restrictions, East US regional
quota at zero).

**Consequences:**
Configurable session timeouts eliminate the Functions ceiling. PySpark API is identical to
Databricks - skills transfer without relearning. F2 must be paused after every session to control
cost.
