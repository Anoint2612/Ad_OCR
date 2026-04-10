"""Routes for prompt template creation and prompt generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.ad_schemas import (
	AnalyzeRequest,
	GenerateRequest,
	GenerateResponse,
	TemplateResponse,
)
from app.services.prompt_generator import generate_prompt, generate_template
from app.services.storage_service import (
	load_pattern_report,
	load_template,
	save_template,
)


router = APIRouter()


@router.post("/prompt/template", response_model=TemplateResponse)
async def build_template(request: AnalyzeRequest) -> TemplateResponse:
	"""Build and store reusable prompt template from a pattern report."""
	pattern_report = await load_pattern_report(request.job_id)
	if pattern_report is None:
		raise HTTPException(status_code=404, detail="Run /ads/patterns first")

	result = generate_template(pattern_report)
	await save_template(request.job_id, result)
	return TemplateResponse(**result)


@router.post("/prompt/generate", response_model=GenerateResponse)
async def build_prompt(request: GenerateRequest) -> GenerateResponse:
	"""Generate a filled final prompt from saved template and provided inputs."""
	template_data = await load_template(request.job_id)
	if template_data is None:
		raise HTTPException(status_code=404, detail="Run /prompt/template first")

	filled_prompt = generate_prompt(template_data["template"], request.inputs)
	return GenerateResponse(prompt=filled_prompt)
