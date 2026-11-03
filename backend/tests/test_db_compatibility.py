import pytest
from backend.app.db.session import get_engine_kwargs
from alembic.config import Config
from alembic import command


def test_sqlite_engine_kwargs():
    kwargs = get_engine_kwargs("sqlite+aiosqlite:///./test.db")
    assert "connect_args" in kwargs
    assert kwargs["connect_args"]["timeout"] == 30.0
    assert kwargs["connect_args"]["check_same_thread"] is False
    assert "pool_size" not in kwargs


def test_postgresql_engine_kwargs():
    kwargs = get_engine_kwargs("postgresql+asyncpg://user:pass@localhost:5432/webtoon_studio")
    assert kwargs["pool_size"] == 10
    assert kwargs["max_overflow"] == 20
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_recycle"] == 3600
    assert "connect_args" not in kwargs


def test_alembic_upgrade_head():
    alembic_cfg = Config("alembic.ini")
    # Should run migration to head cleanly on current database
    command.upgrade(alembic_cfg, "head")
