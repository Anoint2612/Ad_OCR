"""Vision analysis service for advertisement images."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from app.core.config import (
	AI_PROVIDER,
	NIM_API_KEY,
	NIM_BASE_URL,
	NIM_VISION_MODEL,
	OLLAMA_BASE_URL,
	VISION_MODEL,
)
from app.core.logging_config import logger
from app.services.provider_errors import PLACEHOLDER_VISUAL, is_rate_limited_error


VISION_PROMPT = """
Analyze this advertisement image and return ONLY a valid JSON object with no explanation, no markdown fences.
Required fields:
- product_type (string)
- layout (string)
- colors (list of strings)
- style (string)
- background (string)
- extras (list of strings)
""".strip()


def describe_ad(image_path: str) -> dict:
	"""Describe an ad image using the configured AI provider."""
	provider = AI_PROVIDER.strip().lower()
	if provider == "nim":
		return _describe_nim(image_path)
	if provider == "ollama":
		return _describe_ollama(image_path)

	logger.warning("Unknown AI_PROVIDER=%s, falling back to placeholder", AI_PROVIDER)
	return dict(PLACEHOLDER_VISUAL)


def _load_image_b64(image_path: str) -> tuple[str, str]:
	"""Load image bytes and return base64 payload and inferred mime type."""
	path = Path(image_path)
	image_bytes = path.read_bytes()
	encoded = base64.b64encode(image_bytes).decode("utf-8")

	ext = path.suffix.lower().lstrip(".")
	if ext in {"jpg", "jpeg"}:
		mime_type = "image/jpeg"
	else:
		mime_type = f"image/{ext}" if ext else "image/png"

	return encoded, mime_type


def _parse_vision_response(raw: str) -> dict:
	"""Extract and parse the JSON object from model output."""
	cleaned = raw.replace("```json", "").replace("```", "").strip()
	match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
	if not match:
		raise ValueError("No JSON object found in vision response")
	return json.loads(match.group(0))


def _describe_ollama(image_path: str) -> dict:
	"""Describe ad image via local Ollama vision model."""
	try:
		import ollama

		b64, _ = _load_image_b64(image_path)
		client = ollama.Client(host=OLLAMA_BASE_URL)
		response = client.chat(
			model=VISION_MODEL,
			messages=[
				{
					"role": "user",
					"content": VISION_PROMPT,
					"images": [b64],
				}
			],
			options={"temperature": 0.1},
		)

		if isinstance(response, dict):
			content = response.get("message", {}).get("content", "")
		else:
			content = getattr(getattr(response, "message", None), "content", "")

		return _parse_vision_response(content)
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("Ollama vision provider is rate-limited/busy: %s", e)
			return dict(PLACEHOLDER_VISUAL)
		logger.exception("Ollama vision analysis failed for %s: %s", image_path, e)
		return dict(PLACEHOLDER_VISUAL)


def _describe_nim(image_path: str) -> dict:
	"""Describe ad image via NVIDIA NIM vision model using OpenAI-compatible API."""
	try:
		from openai import OpenAI

		b64, mime_type = _load_image_b64(image_path)
		client = OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)

		completion = client.chat.completions.create(
			model=NIM_VISION_MODEL,
			messages=[
				{
					"role": "user",
					"content": [
						{"type": "text", "text": VISION_PROMPT},
						{
							"type": "image_url",
							"image_url": {
								"url": f"data:{mime_type};base64,{b64}",
							},
						},
					],
				}
			],
			max_tokens=600,
			temperature=0.1,
		)

		content = completion.choices[0].message.content or ""
		return _parse_vision_response(content)
	except Exception as e:
		if is_rate_limited_error(e):
			logger.warning("NIM vision provider is rate-limited/busy: %s", e)
			return dict(PLACEHOLDER_VISUAL)
		logger.exception("NIM vision analysis failed for %s: %s", image_path, e)
		return dict(PLACEHOLDER_VISUAL)
