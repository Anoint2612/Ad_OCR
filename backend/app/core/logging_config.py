"""Shared logging configuration for the Ad Prompt Intelligence backend."""

from __future__ import annotations

import logging
import sys


logger = logging.getLogger("adprompt")
logger.setLevel(logging.INFO)

if not logger.handlers:
	stream_handler = logging.StreamHandler(sys.stdout)
	formatter = logging.Formatter(
		"%(asctime)s | %(levelname)s | %(name)s | %(message)s"
	)
	stream_handler.setFormatter(formatter)
	logger.addHandler(stream_handler)

logger.propagate = False
