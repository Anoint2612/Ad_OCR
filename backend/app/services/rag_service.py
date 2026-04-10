"""RAG bridge service between ad analyses and ChromaDB vector storage."""

from __future__ import annotations

import json

from app.core.logging_config import logger
from app.vector_db.chroma_client import query_similar, upsert_analysis


def store_analysis(image_id: str, analysis: dict) -> None:
	"""Store one analysis record in Chroma with summarized text and metadata."""
	extracted = analysis.get("extracted_text", {}) or {}
	visual = analysis.get("visual_description", {}) or {}

	headline = extracted.get("headline", "")
	cta = extracted.get("cta", "")
	visual_elements = visual.get("visual_elements", visual.get("extras", []))
	visual_elements_text = (
		", ".join(str(v).strip() for v in visual_elements if str(v).strip())
		if isinstance(visual_elements, list)
		else str(visual_elements)
	)
	copy_tone = analysis.get("copy_tone", "")
	layout_type = visual.get("layout_type", visual.get("layout", ""))
	style = visual.get("style", "")
	layout = visual.get("layout", "")
	colors = visual.get("colors", [])

	colors_text = ", ".join(colors) if isinstance(colors, list) else str(colors)
	text_content = (
		f"Headline: {headline}. "
		f"CTA: {cta}. "
		f"Visual elements: {visual_elements_text}. "
		f"Copy tone: {copy_tone}. "
		f"Layout type: {layout_type}. "
		f"Style: {style}. "
		f"Layout: {layout}. "
		f"Colors: {colors_text}."
	)

	metadata = {
		"job_id": analysis.get("job_id", ""),
		"image_path": analysis.get("image_path", ""),
		"product_type": visual.get("product_type", ""),
		"style": style,
		"layout": layout,
	}

	upsert_analysis(image_id=image_id, text_content=text_content, metadata=metadata)
	logger.info("Stored analysis in vector DB for image_id=%s", image_id)


def retrieve_context(job_id: str, query: str = "advertisement patterns") -> str:
	"""Retrieve similar documents and format them as a readable context block."""
	results = query_similar(query_text=query, n_results=10)
	if not results:
		return "No context available."

	filtered = []
	for item in results:
		metadata = item.get("metadata") or {}
		if metadata.get("job_id") == job_id:
			filtered.append(item)

	selected = filtered if filtered else results
	if not selected:
		return "No context available."

	lines: list[str] = ["Retrieved ad context:"]
	for idx, item in enumerate(selected, start=1):
		metadata = item.get("metadata") or {}
		lines.append(f"{idx}. ID: {item.get('id', '')}")
		lines.append(f"   Document: {item.get('document', '')}")
		lines.append(f"   Metadata: {json.dumps(metadata, ensure_ascii=False)}")

	return "\n".join(lines)


def get_analyses_as_context(analyses: list[dict]) -> str:
	"""Format analyses directly into a readable context string."""
	if not analyses:
		return "No context available."

	lines: list[str] = ["Direct ad analyses context:"]
	for idx, analysis in enumerate(analyses, start=1):
		extracted = analysis.get("extracted_text", {}) or {}
		visual = analysis.get("visual_description", {}) or {}
		lines.append(f"{idx}. image_id: {analysis.get('image_id', '')}")
		lines.append(f"   image_path: {analysis.get('image_path', '')}")
		lines.append(f"   headline: {extracted.get('headline', '')}")
		lines.append(f"   cta: {extracted.get('cta', '')}")
		lines.append(f"   style: {visual.get('style', '')}")
		lines.append(f"   layout: {visual.get('layout', '')}")
		lines.append(
			f"   colors: {', '.join(visual.get('colors', [])) if isinstance(visual.get('colors', []), list) else visual.get('colors', '')}"
		)

	return "\n".join(lines)
