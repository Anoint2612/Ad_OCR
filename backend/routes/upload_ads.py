"""Routes for uploading ad image files."""

from __future__ import annotations

import os
import uuid

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import MAX_UPLOAD_IMAGES, MIN_UPLOAD_IMAGES, UPLOAD_DIR
from app.schemas.ad_schemas import UploadResponse


router = APIRouter()

_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@router.post("/ads/upload", response_model=UploadResponse)
async def upload_ads(files: list[UploadFile] = File(...)) -> UploadResponse:
	"""Upload ad images and group them under a generated job id."""
	if not (MIN_UPLOAD_IMAGES <= len(files) <= MAX_UPLOAD_IMAGES):
		raise HTTPException(
			status_code=400,
			detail=(
				f"Upload between {MIN_UPLOAD_IMAGES} and "
				f"{MAX_UPLOAD_IMAGES} images."
			),
		)

	for file in files:
		extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
		if extension not in _ALLOWED_EXTENSIONS:
			raise HTTPException(
				status_code=400,
				detail=f"Invalid file extension for '{file.filename}'. Allowed: jpg, jpeg, png, webp.",
			)

	job_id = str(uuid.uuid4())
	job_dir = os.path.join(UPLOAD_DIR, job_id)
	os.makedirs(job_dir, exist_ok=True)

	for file in files:
		filename = os.path.basename(file.filename or f"upload-{uuid.uuid4().hex}.jpg")
		output_path = os.path.join(job_dir, filename)
		content = await file.read()
		async with aiofiles.open(output_path, mode="wb") as out:
			await out.write(content)

	return UploadResponse(job_id=job_id, image_count=len(files))
