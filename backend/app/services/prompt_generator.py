"""Prompt template generation and prompt filling service."""

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


TEMPLATE_PROMPT = """
You are creating a reusable ad image generation prompt template from this pattern report:
{pattern_report_json}

Return ONLY valid JSON with this shape:
{{
  "template": "string",
  "variables": ["string", "..."]
}}

The template MUST include these placeholders exactly:
[PRODUCT_NAME], [PRODUCT_BENEFIT], [CTA_TEXT], [TARGET_AUDIENCE], [HEADLINE]

Do not include markdown fences or extra explanation.
""".strip()


FILL_PROMPT_TEMPLATE = """
Fill the following prompt template using the provided inputs.

Template:
{template}

Inputs (JSON):
{inputs_json}

Return ONLY valid JSON with shape:
{{"prompt": "string"}}

Do not include markdown fences or extra explanation.
""".strip()


FALLBACK_TEMPLATE = {
	"template": "Create a clean modern advertisement for [PRODUCT_NAME]. Highlight [PRODUCT_BENEFIT]. Use a minimal, professional layout with the product centered. Include headline: [HEADLINE]. Target audience: [TARGET_AUDIENCE]. CTA button: [CTA_TEXT].",
	"variables": [
		"[PRODUCT_NAME]",
		"[PRODUCT_BENEFIT]",
		"[CTA_TEXT]",
		"[TARGET_AUDIENCE]",
		"[HEADLINE]",
	],
}


def generate_template(pattern_report: dict) -> dict:
	"""Generate a reusable prompt template from an extracted pattern report."""
	provider = AI_PROVIDER.strip().lower()
	if provider == "nim":
		return _generate_template_nim(pattern_report)
	if provider == "ollama":
		return _generate_template_ollama(pattern_report)

	logger.warning("Unknown AI_PROVIDER=%s. Using fallback template.", AI_PROVIDER)
	return dict(FALLBACK_TEMPLATE)


def generate_prompt(template: str, inputs: dict[str, str]) -> str:
	"""Fill a template with provided inputs, with optional provider-assisted refinement."""
	deterministic_prompt = _fill_placeholders(template, inputs)

	provider = AI_PROVIDER.strip().lower()
	if provider == "nim":
		return _generate_prompt_nim(template, inputs, deterministic_prompt)
	if provider == "ollama":
		return _generate_prompt_ollama(template, inputs, deterministic_prompt)

	return deterministic_prompt


def _parse_llm_json(raw: str) -> dict:
	"""Parse JSON object from an LLM response string."""
	cleaned = raw.replace("```json", "").replace("```", "").strip()
	match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
	if not match:
		raise ValueError("No JSON object found in LLM response")
	return json.loads(match.group(0))


def _fill_placeholders(template: str, inputs: dict[str, str]) -> str:
	"""Replace [VARIABLE] placeholders in a case-insensitive manner."""
	if not template:
		template = FALLBACK_TEMPLATE["template"]

	normalized = {
		str(key).strip().upper().strip("[]"): str(value)
		for key, value in (inputs or {}).items()
	}

	def _replace(match: re.Match[str]) -> str:
		placeholder = match.group(0)
		core = placeholder.strip("[]").upper()
		return normalized.get(core, placeholder)

	return re.sub(r"\[[A-Za-z0-9_]+\]", _replace, template)


def _generate_template_ollama(pattern_report: dict) -> dict:
	"""Generate template using Ollama."""
	try:
		import ollama

		prompt = TEMPLATE_PROMPT.format(
			pattern_report_json=json.dumps(pattern_report, ensure_ascii=False, indent=2)
		)
		response = ollama.chat(
			model=LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			options={"temperature": 0.2},
		)
		if isinstance(response, dict):
			content = response.get("message", {}).get("content", "")
		else:
			content = getattr(getattr(response, "message", None), "content", "")

		parsed = _parse_llm_json(content)
		if not isinstance(parsed.get("template"), str) or not isinstance(
			parsed.get("variables"), list
		):
			return dict(FALLBACK_TEMPLATE)
		return parsed
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Template generation rate-limited/busy on Ollama: %s", e)
		else:
			logger.exception("Template generation failed on Ollama: %s", e)
		return dict(FALLBACK_TEMPLATE)


def _generate_template_nim(pattern_report: dict) -> dict:
	"""Generate template using NVIDIA NIM."""
	try:
		from openai import OpenAI

		prompt = TEMPLATE_PROMPT.format(
			pattern_report_json=json.dumps(pattern_report, ensure_ascii=False, indent=2)
		)
		client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)
		completion = client.chat.completions.create(
			model=NIM_LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			max_tokens=600,
			temperature=0.2,
		)
		content = completion.choices[0].message.content or ""
		parsed = _parse_llm_json(content)
		if not isinstance(parsed.get("template"), str) or not isinstance(
			parsed.get("variables"), list
		):
			return dict(FALLBACK_TEMPLATE)
		return parsed
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Template generation rate-limited/busy on NIM: %s", e)
		else:
			logger.exception("Template generation failed on NIM: %s", e)
		return dict(FALLBACK_TEMPLATE)


def _generate_prompt_ollama(
	template: str, inputs: dict[str, str], deterministic_prompt: str
) -> str:
	"""Optionally refine filled prompt using Ollama; fallback to deterministic fill."""
	try:
		import ollama

		prompt = FILL_PROMPT_TEMPLATE.format(
			template=template,
			inputs_json=json.dumps(inputs or {}, ensure_ascii=False, indent=2),
		)
		response = ollama.chat(
			model=LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			options={"temperature": 0.1},
		)
		if isinstance(response, dict):
			content = response.get("message", {}).get("content", "")
		else:
			content = getattr(getattr(response, "message", None), "content", "")

		parsed = _parse_llm_json(content)
		return str(parsed.get("prompt") or deterministic_prompt)
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Prompt fill rate-limited/busy on Ollama: %s", e)
		else:
			logger.exception("Prompt fill failed on Ollama: %s", e)
		return deterministic_prompt


def _generate_prompt_nim(
	template: str, inputs: dict[str, str], deterministic_prompt: str
) -> str:
	"""Optionally refine filled prompt using NVIDIA NIM; fallback to deterministic fill."""
	try:
		from openai import OpenAI

		prompt = FILL_PROMPT_TEMPLATE.format(
			template=template,
			inputs_json=json.dumps(inputs or {}, ensure_ascii=False, indent=2),
		)
		client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)
		completion = client.chat.completions.create(
			model=NIM_LLM_MODEL,
			messages=[{"role": "user", "content": prompt}],
			max_tokens=700,
			temperature=0.1,
		)
		content = completion.choices[0].message.content or ""
		parsed = _parse_llm_json(content)
		return str(parsed.get("prompt") or deterministic_prompt)
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Prompt fill rate-limited/busy on NIM: %s", e)
		else:
			logger.exception("Prompt fill failed on NIM: %s", e)
		return deterministic_prompt
