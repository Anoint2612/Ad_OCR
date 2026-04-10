"""Routes for ad analysis and pattern extraction."""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UPLOAD_DIR
from app.core.logging_config import logger
from app.db.database import get_db
from app.db.models import AnalysisRecord
from app.schemas.ad_schemas import AdAnalysis, AnalyzeRequest, ExtractedText, VisualDescription
from app.services.ocr_service import extract_text
from app.services.pattern_extractor import extract_patterns
from app.services.rag_service import store_analysis
from app.services.storage_service import (
	load_analyses,
	save_analyses,
	save_pattern_report,
)
from app.services.vision_service import describe_ad


router = APIRouter()

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/ads/analyze")
async def analyze_ads(
	request: AnalyzeRequest,
	db: AsyncSession | None = Depends(get_db),
) -> dict:
	"""Analyze uploaded ad images for a job and persist outputs."""
	job_dir = os.path.join(UPLOAD_DIR, request.job_id)
	if not os.path.isdir(job_dir):
		raise HTTPException(status_code=404, detail="job_id not found")

	image_files = [
		filename
		for filename in sorted(os.listdir(job_dir))
		if os.path.splitext(filename)[1].lower() in _ALLOWED_EXTENSIONS
	]
	if not image_files:
		raise HTTPException(status_code=404, detail="job_id not found")

	analyses_list: list[dict] = []

	for filename in image_files:
		image_id = str(uuid.uuid4())
		image_path = os.path.join(job_dir, filename)

		extracted_text_dict = extract_text(image_path)
		visual_description_dict = describe_ad(image_path)

		ad_analysis = AdAnalysis(
			image_id=image_id,
			image_path=image_path,
			extracted_text=ExtractedText(**extracted_text_dict),
			visual_description=VisualDescription(**visual_description_dict),
		)
		analysis_dict = ad_analysis.model_dump(by_alias=True)
		analysis_dict["job_id"] = request.job_id

		store_analysis(image_id=image_id, analysis=analysis_dict)

		if db is not None:
			record = AnalysisRecord(
				job_id=request.job_id,
				image_id=image_id,
				image_path=image_path,
				extracted_text=analysis_dict["extracted_text"],
				visual_description=analysis_dict["visual_description"],
			)
			db.add(record)

		analyses_list.append(analysis_dict)

	if db is not None:
		try:
			await db.commit()
		except Exception as e:
			await db.rollback()
			logger.exception("Failed to commit analysis records for job_id=%s: %s", request.job_id, e)

	await save_analyses(request.job_id, analyses_list)
	return {"analyses": analyses_list}


@router.post("/ads/patterns")
async def analyze_patterns(request: AnalyzeRequest) -> dict:
	"""Generate and persist a cross-ad pattern report for a job."""
	analyses = await load_analyses(request.job_id)
	if not analyses:
		raise HTTPException(status_code=404, detail="No analyses found for this job_id")

	report = extract_patterns(analyses)
	await save_pattern_report(request.job_id, report)
	return report
