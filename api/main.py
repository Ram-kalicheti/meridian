from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from telemetry.tracing import configure_tracing
from api.config import settings
from api.routes.health import router as health_router
from api.routes.query import query_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        r = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
        await r.ping()
        app.state.redis = r
    except Exception:
        app.state.redis = None
    configure_tracing()
    yield
    if app.state.redis:
        await app.state.redis.aclose()

app = FastAPI(title="meridian", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(query_router)
