"""Local smoke tests for Ad Prompt Intelligence backend components."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
	sys.path.insert(0, str(BACKEND_DIR))


from app.services.ocr_service import extract_text
from app.services.pattern_extractor import extract_patterns
from app.services.vision_service import describe_ad
from app.vector_db.local_embeddings import get_embedding_function


def main() -> None:
	"""Run local smoke tests without starting the API server."""
	test_image_path = Path("/tmp/test_ad.jpg")
	any_failed = False

	# 1) Create test image
	try:
		image = Image.new("RGB", (400, 300), color="white")
		draw = ImageDraw.Draw(image)
		draw.text((20, 140), "SALE 50% OFF - Shop Now", fill="black")
		image.save(test_image_path, format="JPEG")
		print(f"Created test image: {test_image_path}")
	except Exception as e:
		any_failed = True
		print(f"FAIL [Image Create] {e}")

	# 2) OCR test
	try:
		ocr_result = extract_text(str(test_image_path))
		assert isinstance(ocr_result, dict), "OCR result must be a dict"
		assert "headline" in ocr_result, "OCR result missing 'headline'"
		print("OCR Result:", ocr_result)
		print("PASS [OCR]")
	except Exception as e:
		any_failed = True
		print(f"FAIL [OCR] {e}")

	# 3) Vision test
	try:
		vision_result = describe_ad(str(test_image_path))
		assert isinstance(vision_result, dict), "Vision result must be a dict"
		assert "product_type" in vision_result, "Vision result missing 'product_type'"
		print("Vision Result:", vision_result)
		print("PASS [Vision]")
	except Exception as e:
		any_failed = True
		print(f"FAIL [Vision] {e}")

	# 4) LLM pattern extraction test
	try:
		fake_analyses = [
			{
				"image_id": "test-image-1",
				"image_path": "/tmp/test_ad.jpg",
				"extracted_text": {"headline": "Glow Better"},
				"visual_description": {"style": "minimal luxury"},
			}
		]
		pattern_result = extract_patterns(fake_analyses)
		assert isinstance(pattern_result, dict), "Pattern result must be a dict"
		assert "copy_tone" in pattern_result, "Pattern result missing 'copy_tone'"
		print("Pattern Result:", pattern_result)
		print("PASS [LLM]")
	except Exception as e:
		any_failed = True
		print(f"FAIL [LLM] {e}")

	# 5) Embeddings test
	try:
		embedding_fn = get_embedding_function()
		vectors = embedding_fn.embed_documents(
			["A clean skincare ad with soft lighting", "Bold sale ad with red CTA"]
		)
		assert len(vectors) == 2, "Expected exactly two embeddings"
		assert len(vectors[0]) > 0 and len(vectors[1]) > 0, "Embedding vectors are empty"
		print(f"Embedding dims: {len(vectors[0])}, {len(vectors[1])}")
		print("PASS [Embeddings]")
	except Exception as e:
		any_failed = True
		print(f"FAIL [Embeddings] {e}")

	if any_failed:
		print("One or more tests failed.")
	else:
		print("All tests passed.")


if __name__ == "__main__":
	main()
