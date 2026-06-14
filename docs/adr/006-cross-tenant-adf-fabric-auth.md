# ADR 006 - Cross-Tenant ADF to Fabric Auth via Service Principal

**Status:** Accepted

**Context:**
ADF is deployed in the student Azure tenant. Fabric is deployed in a personal Azure tenant. ADF
managed identity is scoped to its home Entra ID directory and cannot authenticate to resources in
a different tenant.

**Decision:**
Service principal meridian-adf-sp registered in the personal tenant, granted Contributor role in
the Fabric workspace. Client ID, secret, and tenant ID stored in Key Vault in the student tenant.
ADF WebActivity uses ServicePrincipal auth, pulling credentials at runtime via the LS_KeyVault
linked service.

**Consequences:**
This is the standard enterprise pattern for cross-tenant ADF to Fabric integration. The service
principal secret expires December 2026 - rotation must be handled before that date in production.
All credential access is auditable via Key Vault diagnostic logs.
