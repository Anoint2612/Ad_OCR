"""Async storage helpers for analysis outputs and uploads."""

from __future__ import annotations

import json
import os
import uuid

import aiofiles

from app.core.config import ANALYSIS_OUTPUT_DIR, UPLOAD_DIR
from app.core.logging_config import logger


def _job_analysis_dir(job_id: str) -> str:
	return os.path.join(ANALYSIS_OUTPUT_DIR, job_id)


async def save_analyses(job_id: str, analyses: list[dict]) -> str:
	"""Save image analyses for a job and return the output file path."""
	job_dir = _job_analysis_dir(job_id)
	os.makedirs(job_dir, exist_ok=True)
	file_path = os.path.join(job_dir, "analyses.json")

	async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
		await f.write(json.dumps(analyses, ensure_ascii=False, indent=2))

	logger.info("Saved analyses for job_id=%s at %s", job_id, file_path)
	return file_path


async def load_analyses(job_id: str) -> list[dict]:
	"""Load analyses for a job. Return an empty list when missing."""
	file_path = os.path.join(_job_analysis_dir(job_id), "analyses.json")
	if not os.path.exists(file_path):
		return []

	async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
		content = await f.read()

	data = json.loads(content) if content.strip() else []
	if isinstance(data, list):
		return data
	return []


async def save_pattern_report(job_id: str, report: dict) -> str:
	"""Save a pattern report for a job and return the output file path."""
	job_dir = _job_analysis_dir(job_id)
	os.makedirs(job_dir, exist_ok=True)
	file_path = os.path.join(job_dir, "pattern_report.json")

	async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
		await f.write(json.dumps(report, ensure_ascii=False, indent=2))

	logger.info("Saved pattern report for job_id=%s at %s", job_id, file_path)
	return file_path


async def load_pattern_report(job_id: str) -> dict | None:
	"""Load a pattern report for a job, or return None when missing."""
	file_path = os.path.join(_job_analysis_dir(job_id), "pattern_report.json")
	if not os.path.exists(file_path):
		return None

	async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
		content = await f.read()

	data = json.loads(content) if content.strip() else None
	if isinstance(data, dict):
		return data
	return None


async def save_template(job_id: str, template_data: dict) -> str:
	"""Save a template payload for a job and return the output file path."""
	job_dir = _job_analysis_dir(job_id)
	os.makedirs(job_dir, exist_ok=True)
	file_path = os.path.join(job_dir, "template.json")

	async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
		await f.write(json.dumps(template_data, ensure_ascii=False, indent=2))

	logger.info("Saved template for job_id=%s at %s", job_id, file_path)
	return file_path


async def load_template(job_id: str) -> dict | None:
	"""Load a template payload for a job, or return None when missing."""
	file_path = os.path.join(_job_analysis_dir(job_id), "template.json")
	if not os.path.exists(file_path):
		return None

	async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
		content = await f.read()

	data = json.loads(content) if content.strip() else None
	if isinstance(data, dict):
		return data
	return None


def get_upload_dir(job_id: str) -> str:
	"""Return and ensure the upload directory path for a job."""
	trace_id = uuid.uuid4().hex[:8]
	upload_dir = os.path.join(UPLOAD_DIR, job_id)
	os.makedirs(upload_dir, exist_ok=True)
	logger.info("Prepared upload dir for job_id=%s at %s (trace=%s)", job_id, upload_dir, trace_id)
	return upload_dir
