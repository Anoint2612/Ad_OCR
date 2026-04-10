"""Database ORM models for the Ad Prompt Intelligence backend."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
	return datetime.now(timezone.utc)


class AnalysisRecord(Base):
	"""Stores OCR and vision analysis outputs for an uploaded ad image."""

	__tablename__ = "analysis_records"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		default=uuid.uuid4,
	)
	job_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
	image_id: Mapped[str] = mapped_column(String, nullable=False)
	image_path: Mapped[str] = mapped_column(String, nullable=False)
	extracted_text: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
	visual_description: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		default=_utcnow,
		nullable=False,
	)
