"""Async SQLAlchemy database setup for the Ad Prompt Intelligence backend."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
	AsyncSession,
	async_sessionmaker,
	create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import DATABASE_URL, REQUIRE_DATABASE


Base = declarative_base()

engine = None
AsyncSessionLocal = None

if DATABASE_URL:
	engine = create_async_engine(DATABASE_URL, future=True)
	AsyncSessionLocal = async_sessionmaker(
		bind=engine,
		class_=AsyncSession,
		expire_on_commit=False,
		autoflush=False,
		autocommit=False,
	)


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
	"""Yield an async database session or ``None`` when DB is not configured."""
	if AsyncSessionLocal is None:
		if not REQUIRE_DATABASE and not DATABASE_URL:
			yield None
			return
		yield None
		return

	async with AsyncSessionLocal() as session:
		yield session
