"""Cross-ad pattern extraction service using configured LLM provider."""

from __future__ import annotations

import json
import re

from app.core.config import (
	AI_PROVIDER,
	LLM_MODEL,
	NIM_API_KEY,
	NIM_BASE_URL,
	NIM_LLM_MODEL,
)
from app.core.logging_config import logger
from app.services.provider_errors import is_rate_limited_error


DETERMINISTIC_FALLBACK = {
	"summary": "Fallback report: LLM unavailable. Common patterns detected.",
	"common_layouts": ["product center", "text overlay", "split layout"],
	"recurring_palettes": ["brand primary", "white/neutral", "accent"],
	"style_patterns": ["clean product focus", "benefit-led"],
	"primary_headline_style": "mixed",
	"copy_tone": "short, benefit-focused",
	"cta_patterns": ["Shop Now", "Learn More"],
}


PATTERN_PROMPT_TEMPLATE = """
You are analyzing creative data from {count} advertisement images.

Ad analysis data:
{analyses_json}

Identify cross-ad patterns and return ONLY a valid JSON object.
Do not include markdown fences. Do not include explanations.

Required JSON keys:
- summary (string)
- common_layouts (list of strings)
- recurring_palettes (list of strings)
- style_patterns (list of strings)
- primary_headline_style (string)
- copy_tone (string)
- cta_patterns (list of strings)
""".strip()


def extract_patterns(analyses: list[dict]) -> dict:
	"""Extract cross-ad creative patterns using the configured provider."""
	provider = AI_PROVIDER.strip().lower()
	if provider == "nim":
		return _extract_nim(analyses)
	if provider == "ollama":
		return _extract_ollama(analyses)

	logger.warning("Unknown AI_PROVIDER=%s. Using deterministic fallback.", AI_PROVIDER)
	return dict(DETERMINISTIC_FALLBACK)


def _build_prompt(analyses: list[dict]) -> str:
	"""Reduce analysis payload and format the pattern extraction prompt."""
	reduced = []
	for item in analyses:
		reduced.append(
			{
				"extracted_text": item.get("extracted_text", {}),
				"visual_description": item.get("visual_description", {}),
			}
		)

	analyses_json = json.dumps(reduced, ensure_ascii=False, indent=2)
	return PATTERN_PROMPT_TEMPLATE.format(count=len(reduced), analyses_json=analyses_json)


def _parse_llm_json(raw: str) -> dict:
	"""Parse JSON object from LLM response text."""
	cleaned = raw.replace("```json", "").replace("```", "").strip()
	match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
	if not match:
		raise ValueError("No JSON object found in LLM response")
	return json.loads(match.group(0))


def _normalize_pattern_report(report: dict) -> dict:
	"""Normalize parsed report to required schema and fallback defaults."""
	def _str_or_default(value: object, default: str) -> str:
		if isinstance(value, str) and value.strip():
			return value.strip()
		return default

	def _list_of_str(value: object, default: list[str]) -> list[str]:
		if isinstance(value, list):
			cleaned = [str(item).strip() for item in value if str(item).strip()]
			if cleaned:
				return cleaned
		return list(default)

	return {
		"summary": _str_or_default(report.get("summary"), DETERMINISTIC_FALLBACK["summary"]),
		"common_layouts": _list_of_str(
			report.get("common_layouts"), DETERMINISTIC_FALLBACK["common_layouts"]
		),
		"recurring_palettes": _list_of_str(
			report.get("recurring_palettes"), DETERMINISTIC_FALLBACK["recurring_palettes"]
		),
		"style_patterns": _list_of_str(
			report.get("style_patterns"), DETERMINISTIC_FALLBACK["style_patterns"]
		),
		"primary_headline_style": _str_or_default(
			report.get("primary_headline_style"),
			DETERMINISTIC_FALLBACK["primary_headline_style"],
		),
		"copy_tone": _str_or_default(
			report.get("copy_tone"), DETERMINISTIC_FALLBACK["copy_tone"]
		),
		"cta_patterns": _list_of_str(
			report.get("cta_patterns"), DETERMINISTIC_FALLBACK["cta_patterns"]
		),
	}


def _extract_ollama(analyses: list[dict]) -> dict:
	"""Extract pattern report using local Ollama."""
	try:
		import ollama

		prompt = _build_prompt(analyses)
		response = ollama.chat(
			model=LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			options={"temperature": 0.2},
		)

		if isinstance(response, dict):
			content = response.get("message", {}).get("content", "")
		else:
			content = getattr(getattr(response, "message", None), "content", "")

		return _normalize_pattern_report(_parse_llm_json(content))
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Pattern extraction rate-limited/busy on Ollama: %s", e)
		else:
			logger.exception("Pattern extraction failed on Ollama: %s", e)
		return dict(DETERMINISTIC_FALLBACK)


def _extract_nim(analyses: list[dict]) -> dict:
	"""Extract pattern report using NVIDIA NIM via OpenAI-compatible API."""
	try:
		from openai import OpenAI

		prompt = _build_prompt(analyses)
		client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)

		completion = client.chat.completions.create(
			model=NIM_LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			max_tokens=700,
			temperature=0.2,
		)
		content = completion.choices[0].message.content or ""
		return _normalize_pattern_report(_parse_llm_json(content))
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Pattern extraction rate-limited/busy on NIM: %s", e)
		else:
			logger.exception("Pattern extraction failed on NIM: %s", e)
		return dict(DETERMINISTIC_FALLBACK)
