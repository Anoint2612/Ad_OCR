"""ChromaDB client helpers for ad analysis vector storage and retrieval."""

from __future__ import annotations

import logging
import uuid

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import CHROMA_PERSIST_DIR, EMBEDDING_DEVICE, EMBEDDING_MODEL
from app.core.logging_config import logger


_chroma_client = None
_collection = None

# Silence noisy telemetry warnings from Chroma in local development.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)


def get_collection() -> chromadb.Collection:
	"""Return lazily initialized persistent Chroma collection."""
	global _chroma_client, _collection

	if _collection is None:
		_chroma_client = chromadb.PersistentClient(
			path=CHROMA_PERSIST_DIR,
			settings=chromadb.config.Settings(anonymized_telemetry=False),
		)
		embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
			model_name=EMBEDDING_MODEL,
			device=EMBEDDING_DEVICE,
			normalize_embeddings=True,
		)
		_collection = _chroma_client.get_or_create_collection(
			name="ad_analyses",
			embedding_function=embedding_fn,
		)
	return _collection


def upsert_analysis(image_id: str, text_content: str, metadata: dict) -> None:
	"""Upsert one analyzed image document into Chroma."""
	trace_id = uuid.uuid4().hex[:8]
	try:
		collection = get_collection()
		collection.upsert(
			ids=[image_id],
			documents=[text_content],
			metadatas=[metadata],
		)
		logger.info("Upserted analysis image_id=%s (trace=%s)", image_id, trace_id)
	except Exception as e:
		logger.exception(
			"Failed to upsert analysis image_id=%s (trace=%s): %s",
			image_id,
			trace_id,
			e,
		)


def query_similar(query_text: str, n_results: int = 5) -> list[dict]:
	"""Query similar ad analyses from Chroma and return normalized records."""
	try:
		collection = get_collection()
		response = collection.query(
			query_texts=[query_text],
			n_results=n_results,
			include=["documents", "metadatas", "distances"],
		)

		ids = (response.get("ids") or [[]])[0]
		documents = (response.get("documents") or [[]])[0]
		metadatas = (response.get("metadatas") or [[]])[0]
		distances = (response.get("distances") or [[]])[0]

		results: list[dict] = []
		for idx, item_id in enumerate(ids):
			distance = distances[idx] if idx < len(distances) else None
			score = 1 / (1 + float(distance)) if isinstance(distance, (int, float)) else None
			results.append(
				{
					"id": item_id,
					"document": documents[idx] if idx < len(documents) else "",
					"metadata": metadatas[idx] if idx < len(metadatas) else {},
					"distance": distance,
					"score": score,
				}
			)
		return results
	except Exception as e:
		logger.exception("Chroma query failed: %s", e)
		return []
