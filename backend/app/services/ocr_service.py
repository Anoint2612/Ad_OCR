"""OCR extraction service using EasyOCR for ad image text parsing."""

from __future__ import annotations

import logging
import re

import easyocr

from app.core.config import EMBEDDING_DEVICE
from app.core.logging_config import logger


_reader = None
_module_logger = logging.getLogger(__name__)


def _clean_text(value: str) -> str:
	"""Normalize OCR text by collapsing newlines and repeated whitespace."""
	return re.sub(r"\s+", " ", str(value).strip())


def _get_reader() -> easyocr.Reader:
	"""Return a lazily initialized EasyOCR reader singleton."""
	global _reader
	if _reader is None:
		logger.info("Initializing EasyOCR...")
		use_gpu = False
		try:
			import torch

			if EMBEDDING_DEVICE.lower() == "mps":
				use_gpu = bool(
					torch.backends.mps.is_built() and torch.backends.mps.is_available()
				)
			elif EMBEDDING_DEVICE.lower() == "cuda":
				use_gpu = bool(torch.cuda.is_available())
		except Exception:
			use_gpu = False

		try:
			_reader = easyocr.Reader(["en"], gpu=use_gpu)
			logger.info("EasyOCR initialized with gpu=%s", use_gpu)
		except Exception as e:
			logger.warning("EasyOCR GPU init failed (%s). Falling back to CPU.", e)
			_reader = easyocr.Reader(["en"], gpu=False)
			logger.info("EasyOCR initialized with gpu=False")
	return _reader


def _find_headline(lines: list[str]) -> str:
	"""Return the longest candidate headline from the first three lines."""
	if not lines:
		return ""
	candidates = lines[:3]
	return max(candidates, key=len, default="")


def _find_subheadline(headline: str, results: list[tuple]) -> str:
	"""Return second-highest-confidence line that is not the chosen headline."""
	if not results:
		return ""

	sorted_by_conf = sorted(results, key=lambda r: float(r[2]), reverse=True)
	for item in sorted_by_conf:
		if len(item) != 3:
			continue
		_, text, _ = item
		candidate = _clean_text(text)
		if not candidate:
			continue
		if candidate.lower() == headline.lower():
			continue
		return candidate
	return ""


def _find_cta(text: str) -> str:
	"""Return the first matching CTA phrase found in text (case-insensitive)."""
	cta_phrases = [
		"Shop Now",
		"Buy Now",
		"Order Now",
		"Get Started",
		"Learn More",
		"Sign Up",
		"Try Free",
		"Download Now",
		"Claim Offer",
		"Book Now",
		"Subscribe",
	]
	for phrase in cta_phrases:
		if re.search(re.escape(phrase), text, flags=re.IGNORECASE):
			return phrase
	return ""


def _find_offer(text: str) -> str:
	"""Find common promotional offer patterns in extracted text."""
	patterns = [
		r"\b\d{1,3}%\s*off\b",
		r"\bfree\s+shipping\b",
		r"\$\s?\d{1,4}\s*off\b",
		r"\bbuy\s*1\s*get\s*1\b",
		r"\bsave\s*\$\s?\d{1,4}\b",
	]

	for pattern in patterns:
		match = re.search(pattern, text, flags=re.IGNORECASE)
		if match:
			return match.group(0)
	return ""


def _extract_y_bounds(bbox: list) -> tuple[float, float]:
	"""Extract min/max y values from a 4-point OCR bounding box."""
	points = bbox if isinstance(bbox, list) else []
	if not points:
		return 0.0, 0.0
	y_values = [float(point[1]) for point in points if isinstance(point, (list, tuple)) and len(point) >= 2]
	if not y_values:
		return 0.0, 0.0
	return min(y_values), max(y_values)


def _find_brand(lines: list[str], results: list[tuple]) -> str:
	"""Guess brand name from top/bottom image bands using high-confidence short lines."""
	if not results:
		return lines[-1] if lines else ""

	global_min_y = float("inf")
	global_max_y = float("-inf")
	for item in results:
		if len(item) != 3:
			continue
		bbox, _, _ = item
		min_y, max_y = _extract_y_bounds(bbox)
		global_min_y = min(global_min_y, min_y)
		global_max_y = max(global_max_y, max_y)

	if not (global_min_y < float("inf") and global_max_y > float("-inf")):
		return lines[-1] if lines else ""

	height = max(global_max_y - global_min_y, 1.0)
	top_band_end = global_min_y + (0.2 * height)
	bottom_band_start = global_max_y - (0.2 * height)

	candidates: list[str] = []
	for item in results:
		if len(item) != 3:
			continue
		bbox, text, confidence = item
		min_y, max_y = _extract_y_bounds(bbox)
		center_y = (min_y + max_y) / 2
		in_brand_zone = center_y <= top_band_end or center_y >= bottom_band_start
		cleaned = _clean_text(text)
		if in_brand_zone and confidence > 0.7 and 1 <= len(cleaned) <= 20:
			candidates.append(cleaned)

	if candidates:
		return min(candidates, key=len)
	if lines:
		return lines[-1]
	return ""


def _empty_ocr_result() -> dict:
	"""Return an empty structured OCR response."""
	return {
		"headline": "",
		"subheadline": "",
		"cta": "",
		"offer": "",
		"brand_name": "",
		"raw_lines": [],
		"confidence_avg": 0.0,
	}


def extract_text(image_path: str) -> dict:
	"""Extract structured text fields from an advertisement image."""
	try:
		reader = _get_reader()
		raw_results = reader.readtext(image_path, detail=1)

		sorted_results = sorted(
			raw_results,
			key=lambda r: float(r[0][0][1]) if r and r[0] else 0.0,
		)
		filtered_results = [r for r in sorted_results if float(r[2]) >= 0.3]

		lines = [_clean_text(r[1]) for r in filtered_results if _clean_text(r[1])]
		full_text = "\n".join(lines)
		headline = _clean_text(_find_headline(lines))
		subheadline = _clean_text(_find_subheadline(headline, filtered_results))
		cta = _clean_text(_find_cta(full_text))
		offer = _clean_text(_find_offer(full_text))
		brand_name = _clean_text(_find_brand(lines, filtered_results))

		confidence_avg = (
			sum(float(r[2]) for r in filtered_results) / len(filtered_results)
			if filtered_results
			else 0.0
		)

		return {
			"headline": headline,
			"subheadline": subheadline,
			"cta": cta,
			"offer": offer,
			"brand_name": brand_name,
			"raw_lines": lines,
			"confidence_avg": round(confidence_avg, 4),
		}
	except Exception as e:
		logger.exception("OCR extraction failed for image_path=%s: %s", image_path, e)
		_module_logger.debug("Falling back to empty OCR result")
		return _empty_ocr_result()
