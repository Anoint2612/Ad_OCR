"""Provider error helpers and fallback payloads."""

from __future__ import annotations


PLACEHOLDER_VISUAL = {
	"product_type": "unavailable - model busy",
	"layout": "unavailable - model busy",
	"colors": [],
	"style": "unavailable - model busy",
	"background": "unavailable - model busy",
	"extras": [],
	"_fallback": True,
}


def is_rate_limited_error(e: Exception) -> bool:
	"""Return whether an exception looks like provider load/rate-limit pressure."""
	message = str(e).lower()
	keywords = (
		"429",
		"503",
		"rate limit",
		"overloaded",
		"resource exhausted",
		"context deadline",
		"connection refused",
	)
	return any(keyword in message for keyword in keywords)
