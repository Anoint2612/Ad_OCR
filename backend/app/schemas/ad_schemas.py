"""Pydantic schemas for Ad Prompt Intelligence API payloads."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedText(BaseModel):
	"""Structured OCR output extracted from a single ad image."""

	headline: str = ""
	subheadline: str = ""
	cta: str = ""
	offer: str = ""
	brand_name: str = ""
	raw_lines: list[str] = Field(default_factory=list)
	confidence_avg: float = 0.0


class VisualDescription(BaseModel):
	"""Structured visual analysis output for a single ad image."""

	model_config = ConfigDict(populate_by_name=True)

	product_type: str = ""
	layout: str = ""
	colors: list[str] = Field(default_factory=list)
	style: str = ""
	background: str = ""
	extras: list[str] = Field(default_factory=list)
	fallback: bool = Field(default=False, alias="_fallback", serialization_alias="_fallback")


class AdAnalysis(BaseModel):
	"""Complete analysis object for one uploaded image."""

	image_id: str
	image_path: str
	extracted_text: ExtractedText
	visual_description: VisualDescription


class AnalyzeRequest(BaseModel):
	"""Request payload for running analysis for an uploaded job."""

	job_id: str


class PatternReport(BaseModel):
	"""Aggregated pattern report derived from analyzed ad images."""

	summary: str
	common_layouts: list[str]
	recurring_palettes: list[str]
	style_patterns: list[str]
	primary_headline_style: str = "mixed"
	copy_tone: str
	cta_patterns: list[str]


class TemplateResponse(BaseModel):
	"""Prompt template and placeholders to be filled by user inputs."""

	template: str
	variables: list[str]


class GenerateRequest(BaseModel):
	"""Request payload for generating a final prompt."""

	job_id: str
	inputs: dict[str, str] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
	"""Generated final prompt response."""

	prompt: str


class UploadResponse(BaseModel):
	"""Response payload returned after successful image upload."""

	job_id: str
	image_count: int


class HealthResponse(BaseModel):
	"""Service health and dependency availability response."""

	status: str
	database_available: bool
	ollama_available: bool
	vision_model: str
	llm_model: str
