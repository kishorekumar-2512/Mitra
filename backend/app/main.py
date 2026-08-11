"""FastAPI entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from app.agents.providers import ProviderName, build_provider
from app.agents.loop import InsightForgeAgent
from app.api import router
from app.core.config import get_settings
from app.core.memory import SessionMemory
from app.db import SQLAlchemyAdapter
from app.tools import build_tool_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    adapter = SQLAlchemyAdapter(settings.database_url)
    await adapter.initialize_sample_data()
    redis = None
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
    except Exception:
        redis = None
    memory = SessionMemory(redis)
    app.state.memory = memory
    app.state.database = adapter
    app.state.registry = build_tool_registry(adapter)
    app.state.agent_factory = lambda provider, api_key, model: InsightForgeAgent(build_provider(provider, api_key), app.state.registry, memory, model, provider)
    yield
    await adapter.engine.dispose()
    if redis:
        await redis.aclose()


app = FastAPI(title="Mitra", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
