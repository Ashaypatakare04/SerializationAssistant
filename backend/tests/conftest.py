import os
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DB_PATH = Path("./storage/test_studio.db").resolve()
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

# Set settings before importing app
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["LLM_PROVIDER"] = "mock"
os.environ["IMAGE_PROVIDER"] = "mock"

from backend.app.core.config import settings
settings.DATABASE_URL = TEST_DB_URL

from backend.app.models.base import Base
import backend.app.db.session as session_module
from backend.app.main import app

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_module.engine = engine
    session_module.AsyncSessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

async def wait_for_job(client: AsyncClient, job_id: str, timeout: float = 6.0) -> dict:
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        res = await client.get(f"/api/v1/jobs/{job_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] in ("completed", "failed", "cancelled"):
            return data
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s.")
