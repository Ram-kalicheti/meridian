from fastapi import APIRouter

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0"}