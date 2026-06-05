"""
SQLAlchemy async database setup.
Supports PostgreSQL (Supabase) in production and SQLite locally.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Determine database URL
# ---------------------------------------------------------------------------
_env_url = os.getenv("DATABASE_URL", "")

if _env_url:
    # Supabase / Railway provide postgresql:// — SQLAlchemy async needs +asyncpg
    if _env_url.startswith("postgres://"):
        _env_url = _env_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _env_url.startswith("postgresql://") and "+asyncpg" not in _env_url:
        _env_url = _env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    DB_URL = _env_url
else:
    # Local development: use SQLite
    DATA_DIR = Path(__file__).parent.parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DB_URL = f"sqlite+aiosqlite:///{DATA_DIR}/nl_compiler.db"

# PostgreSQL needs different pool settings than SQLite
_is_postgres = "postgresql" in DB_URL
_engine_kwargs = {
    "echo": False,
    "future": True,
}
if _is_postgres:
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(DB_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup."""
    from storage.models import GenerationRecord, EvalResultRecord  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
