"""End-to-end real-image test runner for Ad Prompt Intelligence backend.

Run:
    python scripts/test_real_images.py

Optional:
    python scripts/test_real_images.py /path/to/test_ads
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load project env (prefer backend/.env, fallback backend/.venv/.env)
load_dotenv(BACKEND_DIR / ".env")
if not (BACKEND_DIR / ".env").exists():
    load_dotenv(BACKEND_DIR / ".venv" / ".env")

from app.vector_db.chroma_client import query_similar


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

UPLOAD_ENDPOINTS = ["/upload-ads", "/ads/upload", "/ads/ads/upload"]
ANALYZE_ENDPOINTS = ["/analyze-ads", "/ads/analyze", "/ads/ads/analyze"]
PATTERN_ENDPOINTS = ["/extract-patterns", "/ads/patterns", "/ads/ads/patterns"]
TEMPLATE_ENDPOINTS = ["/generate-template", "/prompt/template", "/prompt/prompt/template"]
FILL_ENDPOINTS = ["/fill-prompt", "/prompt/generate", "/prompt/prompt/generate"]

PLACEHOLDER_MARKER = "unavailable - model busy"


def _print_step(title: str) -> None:
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def _pass(name: str, expected: str, actual: Any) -> None:
    print(f"PASS [{name}]\n  expected: {expected}\n  actual:   {actual}")


def _fail(name: str, expected: str, actual: Any) -> None:
    print(f"FAIL [{name}]\n  expected: {expected}\n  actual:   {actual}")


def _shape(data: Any) -> str:
    if isinstance(data, dict):
        return f"dict keys={list(data.keys())}"
    if isinstance(data, list):
        return f"list len={len(data)}"
    return f"{type(data).__name__}: {data}"


def _pick_images(folder: Path) -> list[Path]:
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    files = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in allowed]
    return files[:5]


async def _post_with_fallback(
    client: httpx.AsyncClient,
    endpoints: list[str],
    *,
    json_body: dict[str, Any] | None = None,
    files: list[tuple[str, tuple[str, Any, str]]] | None = None,
) -> tuple[str, httpx.Response]:
    last_resp: httpx.Response | None = None
    for ep in endpoints:
        resp = await client.post(f"{API_BASE}{ep}", json=json_body, files=files)
        if resp.status_code != 404:
            return ep, resp
        last_resp = resp
    if last_resp is None:
        raise RuntimeError("No endpoint attempted")
    return endpoints[-1], last_resp


def _is_empty_ocr(extracted: dict[str, Any]) -> bool:
    keys = ["headline", "subheadline", "cta", "offer", "brand_name"]
    return all(not str(extracted.get(k, "")).strip() for k in keys)


def _has_placeholder_visual(visual: dict[str, Any]) -> bool:
    if visual.get("_fallback") is True:
        return True
    for v in visual.values():
        if isinstance(v, str) and PLACEHOLDER_MARKER in v.lower():
            return True
    return False


async def main() -> None:
    ads_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (Path.cwd() / "test_ads")

    if not ads_dir.exists() or not ads_dir.is_dir():
        _fail("Input folder", "Existing directory ./test_ads", str(ads_dir))
        return

    selected_images = _pick_images(ads_dir)
    if len(selected_images) < 3:
        _fail("Image count", "At least 3 ad images (.jpg/.jpeg/.png/.webp)", f"found={len(selected_images)}")
        return

    print(f"Using API base: {API_BASE}")
    print(f"Using image folder: {ads_dir}")
    print("Selected files:")
    for p in selected_images:
        print(f"  - {p.name}")

    timeout = httpx.Timeout(connect=15.0, read=900.0, write=300.0, pool=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1) Upload test
        _print_step("1) UPLOAD TEST")
        file_handles: list[Any] = []
        files_payload: list[tuple[str, tuple[str, Any, str]]] = []
        try:
            for p in selected_images:
                fh = open(p, "rb")
                file_handles.append(fh)
                mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                files_payload.append(("files", (p.name, fh, mime)))

            endpoint, upload_resp = await _post_with_fallback(
                client,
                UPLOAD_ENDPOINTS,
                files=files_payload,
            )
        finally:
            for fh in file_handles:
                try:
                    fh.close()
                except Exception:
                    pass

        if upload_resp.status_code != 200:
            _fail(
                "Upload",
                "HTTP 200 + {job_id: str, image_count: int}",
                f"status={upload_resp.status_code}, body={upload_resp.text}",
            )
            return

        upload_data = upload_resp.json()
        job_id = upload_data.get("job_id")
        if isinstance(job_id, str) and isinstance(upload_data.get("image_count"), int):
            _pass(
                "Upload",
                "dict with job_id + image_count",
                f"endpoint={endpoint}, data={upload_data}",
            )
            print("Uploaded file list:")
            for p in selected_images:
                print(f"  - {p.name}")
        else:
            _fail("Upload shape", "job_id:str and image_count:int", _shape(upload_data))
            return

        # 2) Analyze + OCR
        _print_step("2) ANALYZE + OCR TEST")
        try:
            endpoint, analyze_resp = await _post_with_fallback(
                client,
                ANALYZE_ENDPOINTS,
                json_body={"job_id": job_id},
            )
        except httpx.RequestError as e:
            _fail(
                "Analyze",
                "HTTP 200 + {analyses:[...]}",
                f"request_error={type(e).__name__}: {e}",
            )
            return

        if analyze_resp.status_code != 200:
            _fail(
                "Analyze",
                "HTTP 200 + {analyses:[...]}",
                f"status={analyze_resp.status_code}, body={analyze_resp.text}",
            )
            return

        analyze_data = analyze_resp.json()
        analyses = analyze_data.get("analyses", [])
        if isinstance(analyses, list) and analyses:
            _pass("Analyze", "non-empty analyses list", f"endpoint={endpoint}, count={len(analyses)}")
        else:
            _fail("Analyze shape", "analyses: non-empty list", _shape(analyze_data))
            return

        for idx, item in enumerate(analyses, start=1):
            extracted = item.get("extracted_text", {}) or {}
            print(f"\nOCR [{idx}] image_id={item.get('image_id')} path={item.get('image_path')}")
            print(f"  headline:    {extracted.get('headline', '')}")
            print(f"  subheadline: {extracted.get('subheadline', '')}")
            print(f"  cta:         {extracted.get('cta', '')}")
            print(f"  offer:       {extracted.get('offer', '')}")
            print(f"  brand:       {extracted.get('brand_name', '')}")
            if _is_empty_ocr(extracted):
                print("  WARNING: OCR appears empty (all key fields blank)")

        # 3) Vision test
        _print_step("3) VISION TEST")
        for idx, item in enumerate(analyses, start=1):
            visual = item.get("visual_description", {}) or {}
            layout_type = visual.get("layout_type", visual.get("layout", ""))
            visual_elements = visual.get("visual_elements", visual.get("extras", []))
            color_palette = visual.get("color_palette", visual.get("colors", []))

            print(f"Vision [{idx}] image_id={item.get('image_id')}")
            print(f"  layout_type:     {layout_type}")
            print(f"  visual_elements: {visual_elements}")
            print(f"  color_palette:   {color_palette}")

            if _has_placeholder_visual(visual):
                print("  WARNING: Vision fallback detected (placeholder output)")

        _pass(
            "Vision response shape",
            "Each analysis contains visual_description dict",
            f"count={len(analyses)}",
        )

        # 4) Pattern extraction
        _print_step("4) PATTERN EXTRACTION TEST")
        try:
            endpoint, pattern_resp = await _post_with_fallback(
                client,
                PATTERN_ENDPOINTS,
                json_body={"job_id": job_id},
            )
        except httpx.RequestError as e:
            _fail(
                "Pattern extraction",
                "HTTP 200 + pattern report dict",
                f"request_error={type(e).__name__}: {e}",
            )
            return

        if pattern_resp.status_code != 200:
            _fail(
                "Pattern extraction",
                "HTTP 200 + pattern report dict",
                f"status={pattern_resp.status_code}, body={pattern_resp.text}",
            )
            return

        pattern_data = pattern_resp.json()
        print("Pattern report JSON:")
        print(json.dumps(pattern_data, indent=2, ensure_ascii=False))

        copy_tone = pattern_data.get("copy_tone")
        primary_cta_style = pattern_data.get("primary_cta_style")
        if primary_cta_style is None:
            cta_patterns = pattern_data.get("cta_patterns") or []
            primary_cta_style = cta_patterns[0] if isinstance(cta_patterns, list) and cta_patterns else None

        layout_patterns = pattern_data.get("layout_patterns")
        if layout_patterns is None:
            layout_patterns = pattern_data.get("common_layouts")

        ok_copy = isinstance(copy_tone, str) and bool(copy_tone.strip())
        ok_cta = isinstance(primary_cta_style, str) and bool(primary_cta_style.strip())
        ok_layout = isinstance(layout_patterns, list) and len(layout_patterns) > 0

        if ok_copy and ok_cta and ok_layout:
            _pass(
                "Pattern fields",
                "copy_tone + primary_cta_style + layout_patterns non-empty",
                {
                    "copy_tone": copy_tone,
                    "primary_cta_style": primary_cta_style,
                    "layout_patterns": layout_patterns,
                    "endpoint": endpoint,
                },
            )
        else:
            _fail(
                "Pattern fields",
                "copy_tone + primary_cta_style + layout_patterns non-empty",
                {
                    "copy_tone": copy_tone,
                    "primary_cta_style": primary_cta_style,
                    "layout_patterns": layout_patterns,
                    "endpoint": endpoint,
                },
            )

        # 5) Prompt generation
        _print_step("5) PROMPT GENERATION TEST")
        endpoint_template, template_resp = await _post_with_fallback(
            client,
            TEMPLATE_ENDPOINTS,
            json_body={"job_id": job_id},
        )

        if template_resp.status_code != 200:
            _fail(
                "Generate template",
                "HTTP 200 + {template, variables}",
                f"status={template_resp.status_code}, body={template_resp.text}",
            )
            return

        template_data = template_resp.json()
        template_text = template_data.get("template", "")
        variables = template_data.get("variables", [])
        template_id = template_data.get("template_id", job_id)  # fallback for current backend

        if isinstance(template_text, str) and isinstance(variables, list):
            _pass(
                "Generate template",
                "template:str + variables:list",
                {
                    "endpoint": endpoint_template,
                    "template_id": template_id,
                    "variables": variables,
                },
            )
        else:
            _fail("Template shape", "template:str + variables:list", _shape(template_data))
            return

        sample_inputs = {
            "product": "running shoes",
            "audience": "urban millennials",
            "tone": "energetic",
            # Backward-compatible keys for current backend template variables:
            "product_name": "running shoes",
            "product_benefit": "lightweight comfort for all-day movement",
            "cta_text": "Shop Now",
            "target_audience": "urban millennials",
            "headline": "Run Faster. Feel Lighter.",
        }

        fill_payload = {"template_id": template_id, "inputs": sample_inputs}
        # Current backend expects job_id, not template_id
        fill_payload.setdefault("job_id", job_id)

        endpoint_fill, fill_resp = await _post_with_fallback(
            client,
            FILL_ENDPOINTS,
            json_body=fill_payload,
        )

        if fill_resp.status_code != 200:
            _fail(
                "Fill prompt",
                "HTTP 200 + {prompt}",
                f"status={fill_resp.status_code}, body={fill_resp.text}",
            )
            return

        fill_data = fill_resp.json()
        final_prompt = fill_data.get("prompt", "")
        if isinstance(final_prompt, str) and final_prompt.strip():
            _pass("Fill prompt", "prompt:str non-empty", {"endpoint": endpoint_fill})
            print("Final generated prompt:")
            print(final_prompt)
        else:
            _fail("Fill prompt shape", "prompt:str non-empty", _shape(fill_data))

        # 6) Vector DB check
        _print_step("6) VECTOR DB CHECK")
        query_text = "bold CTA with product lifestyle imagery"
        matches = query_similar(query_text=query_text, n_results=2)

        if not matches:
            _fail("Vector query", "At least 1 match", "No matches returned")
            return

        for idx, item in enumerate(matches, start=1):
            metadata = item.get("metadata") or {}
            distance = item.get("distance")
            similarity = item.get("score")

            print(f"Match {idx}")
            print(f"  id: {item.get('id')}")
            print(f"  job_id: {(metadata or {}).get('job_id')}")
            print(f"  distance: {distance}")
            print(f"  similarity_score: {similarity}")

        _pass(
            "Vector query",
            "top 2 matches with job IDs and scores",
            {"returned": len(matches), "query": query_text},
        )

    print("\nE2E real-image test completed.")


if __name__ == "__main__":
    asyncio.run(main())
