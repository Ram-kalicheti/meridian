import time
from fastapi import HTTPException, Request
import redis.asyncio as aioredis
from api.config import TENANT_TPM_LIMITS

_WINDOW_SECONDS = 60
# two-window ttl - prevents key expiring mid-window under clock skew
_KEY_TTL_SECONDS = 120


class TokenBudget:
    def __init__(self, redis_client: aioredis.Redis | None) -> None:
        self._redis = redis_client

    async def check_and_reserve(self, tenant_id: str, tokens: int) -> None:
        limit = TENANT_TPM_LIMITS.get(tenant_id)
        if limit is None:
            raise HTTPException(
                status_code=401, detail=f"no budget configured for tenant: {tenant_id}"
            )
        if self._redis is None:
            # redis unavailable - skip enforcement, allow request through
            return
        bucket = int(time.time()) // _WINDOW_SECONDS
        key = f"tpm:{tenant_id}:{bucket}"
        # atomic incrby - avoids race conditions under concurrent requests
        count = await self._redis.incrby(key, tokens)
        if count == tokens:
            await self._redis.expire(key, _KEY_TTL_SECONDS)
        if count > limit:
            retry_after = _WINDOW_SECONDS - (int(time.time()) % _WINDOW_SECONDS)
            raise HTTPException(
                status_code=429,
                detail=f"token budget exceeded for {tenant_id}: {count}/{limit} tpm",
                headers={"Retry-After": str(retry_after)},
            )


def get_token_budget(request: Request) -> TokenBudget:
    return TokenBudget(request.app.state.redis)