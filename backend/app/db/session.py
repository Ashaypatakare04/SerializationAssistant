import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from backend.app.core.config import settings
from backend.app.models.base import Base


def get_engine_kwargs(db_url: str) -> Dict[str, Any]:
    """Returns engine kwargs tailored to SQLite vs PostgreSQL."""
    kwargs: Dict[str, Any] = {
        "echo": False,
        "future": True,
    }
    
    if "sqlite" in db_url:
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        if db_path and not db_path.startswith(":memory:"):
            parent = Path(db_path).parent
            parent.mkdir(parents=True, exist_ok=True)
        kwargs["connect_args"] = {
            "timeout": 30.0,
            "check_same_thread": False,
        }
    elif "postgres" in db_url or "asyncpg" in db_url:
        # Production connection pool parameters for PostgreSQL
        kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        })
        
    return kwargs


engine = create_async_engine(
    settings.DATABASE_URL,
    **get_engine_kwargs(settings.DATABASE_URL)
)

if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Unique index for partial null-tolerant uniqueness across SQLite and PostgreSQL
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_panel_asset_type ON assets(panel_id, asset_type) WHERE panel_id IS NOT NULL;"))
