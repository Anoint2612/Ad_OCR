"""Main FastAPI application entry point for Ad Prompt Intelligence."""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import (
	ANALYSIS_OUTPUT_DIR,
	CHROMA_PERSIST_DIR,
	LLM_MODEL,
	OLLAMA_BASE_URL,
	REQUIRE_DATABASE,
	UPLOAD_DIR,
	VISION_MODEL,
)
from app.core.logging_config import logger
from app.db.database import Base, engine
from app.db import models as _models  # noqa: F401  # Ensure model metadata is registered
from app.schemas.ad_schemas import HealthResponse
from routes.analyze_ads import router as analyze_router
from routes.generate_prompt import router as prompt_router
from routes.upload_ads import router as upload_router


app = FastAPI(title="Ad Prompt Intelligence API", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


app.include_router(upload_router, prefix="/ads", tags=["Upload"])
app.include_router(analyze_router, prefix="/ads", tags=["Analysis"])
app.include_router(prompt_router, prefix="/prompt", tags=["Prompts"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
	"""Return dependency health status for database and local model server."""
	database_available = False
	ollama_available = False
	vision_model_ok = False
	llm_model_ok = False

	try:
		if engine is not None:
			async with engine.connect() as conn:
				await conn.execute(text("SELECT 1"))
			database_available = True
	except Exception as e:
		logger.warning("Database health check failed: %s", e)

	try:
		async with httpx.AsyncClient(timeout=3.0) as client:
			response = await client.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags")
			response.raise_for_status()
			payload = response.json()
			models = payload.get("models", []) if isinstance(payload, dict) else []
			model_names = {
				item.get("name", "")
				for item in models
				if isinstance(item, dict) and item.get("name")
			}
			ollama_available = True
			vision_model_ok = VISION_MODEL in model_names
			llm_model_ok = LLM_MODEL in model_names
	except Exception as e:
		logger.warning("Ollama health check failed: %s", e)

	status = "ok" if (database_available and ollama_available) else "degraded"
	if not ollama_available and not database_available:
		status = "unhealthy"

	return HealthResponse(
		status=status,
		database_available=database_available,
		ollama_available=ollama_available,
		vision_model=VISION_MODEL if vision_model_ok else f"{VISION_MODEL} (unavailable)",
		llm_model=LLM_MODEL if llm_model_ok else f"{LLM_MODEL} (unavailable)",
	)


@app.on_event("startup")
async def on_startup() -> None:
	"""Initialize required directories and database tables."""
	os.makedirs(UPLOAD_DIR, exist_ok=True)
	os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
	os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)

	logger.info("Ad Prompt Intelligence API started")

	try:
		if engine is not None:
			async with engine.begin() as conn:
				await conn.run_sync(Base.metadata.create_all)
	except Exception as e:
		if REQUIRE_DATABASE:
			logger.exception("Failed to initialize database tables: %s", e)
			raise
		logger.warning("Database initialization skipped (REQUIRE_DATABASE=False): %s", e)
