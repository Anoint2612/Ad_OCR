"""Application configuration constants loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
if not (BASE_DIR / ".env").exists():
	load_dotenv(BASE_DIR / ".venv" / ".env")


def _get_bool(name: str, default: bool) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
	value = os.getenv(name)
	if value is None:
		return default
	try:
		return int(value)
	except ValueError:
		return default


AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VISION_MODEL: str = os.getenv("VISION_MODEL", "llava:13b")
LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral:7b")
NIM_API_KEY: str = os.getenv("NIM_API_KEY", "")
NIM_BASE_URL: str = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_VISION_MODEL: str = os.getenv(
	"NIM_VISION_MODEL", "meta/llama-3.2-90b-vision-instruct"
)
NIM_LLM_MODEL: str = os.getenv("NIM_LLM_MODEL", "meta/llama-3.1-8b-instruct")
EMBEDDING_MODEL: str = os.getenv(
	"EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REQUIRE_DATABASE: bool = _get_bool("REQUIRE_DATABASE", False)
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "storage/chroma")
ANALYSIS_OUTPUT_DIR: str = os.getenv("ANALYSIS_OUTPUT_DIR", "storage/analysis")
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "storage/uploads")
MIN_UPLOAD_IMAGES: int = _get_int("MIN_UPLOAD_IMAGES", 1)
MAX_UPLOAD_IMAGES: int = _get_int("MAX_UPLOAD_IMAGES", 10)
