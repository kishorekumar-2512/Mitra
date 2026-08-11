import pytest_asyncio
from app.db.adapter import SQLAlchemyAdapter


@pytest_asyncio.fixture
async def adapter():
    instance = SQLAlchemyAdapter("sqlite+aiosqlite:///:memory:")
    await instance.initialize_sample_data()
    yield instance
    await instance.engine.dispose()
