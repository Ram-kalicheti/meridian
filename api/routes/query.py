import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth import require_tenant
from api.router.token_budget import TokenBudget, get_token_budget

router = APIRouter(tags=["query"])

# conservative pre-flight reservation before prompt is sized in Day 11 retrieval
_PREFLIGHT_TOKENS = 500


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/query")
async def query_endpoint(
    body: QueryRequest,
    request: Request,
    tenant_id: str = Depends(require_tenant),
    budget: TokenBudget = Depends(get_token_budget),
) -> StreamingResponse:
    await budget.check_and_reserve(tenant_id, _PREFLIGHT_TOKENS)

    # hybrid search, rerank, assembler, and gpt-4o-mini stream wired on Day 11
    async def _stream():
        event = {"status": "ok", "tenant": tenant_id}
        yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")