from fastapi import Header, HTTPException

from api.config import TENANT_TPM_LIMITS

_KNOWN_TENANTS = frozenset(TENANT_TPM_LIMITS.keys())


async def require_tenant(x_tenant_id: str = Header(...)) -> str:
    if x_tenant_id not in _KNOWN_TENANTS:
        raise HTTPException(status_code=401, detail=f"unknown tenant: {x_tenant_id}")
    return x_tenant_id