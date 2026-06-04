"""
SSE streaming helper utilities.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional


def make_pipeline_event(
    stage: str,
    status: str,
    message: str = "",
    elapsed_ms: int = 0,
    tokens_used: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardised pipeline progress event dict."""
    event = {
        "type": "progress",
        "stage": stage,
        "status": status,
        "message": message,
        "elapsed_ms": elapsed_ms,
        "tokens_used": tokens_used,
        "timestamp": int(time.time() * 1000),
    }
    if extra:
        event.update(extra)
    return event


def make_log_event(level: str, message: str) -> Dict[str, Any]:
    """Create a live-log event."""
    return {
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": int(time.time() * 1000),
    }
