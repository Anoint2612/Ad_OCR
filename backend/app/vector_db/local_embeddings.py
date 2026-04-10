"""Local embedding model loader for vector search."""

from __future__ import annotations

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import EMBEDDING_DEVICE, EMBEDDING_MODEL
from app.core.logging_config import logger


_embedding_fn = None


def get_embedding_function() -> HuggingFaceEmbeddings:
	"""Return a lazily initialized HuggingFace embedding function singleton."""
	global _embedding_fn
	if _embedding_fn is None:
		logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
		_embedding_fn = HuggingFaceEmbeddings(
			model_name=EMBEDDING_MODEL,
			model_kwargs={"device": EMBEDDING_DEVICE},
			encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
		)
	return _embedding_fn
