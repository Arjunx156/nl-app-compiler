"""
Simple in-memory + SQLite backed prompt cache.
Key: sha256(normalized prompt) → CompilationResult
TTL: 1 hour
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional


class PromptCache:
    TTL_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}  # key → (value, expire_at)

    @staticmethod
    def _key(prompt: str) -> str:
        normalized = prompt.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[Any]:
        k = self._key(prompt)
        entry = self._store.get(k)
        if entry is None:
            return None
        value, expire_at = entry
        if time.time() > expire_at:
            del self._store[k]
            return None
        return value

    def set(self, prompt: str, result: Any) -> None:
        k = self._key(prompt)
        self._store[k] = (result, time.time() + self.TTL_SECONDS)

    def clear(self) -> None:
        self._store.clear()


# Module-level singleton
_cache = PromptCache()


def get_cache() -> PromptCache:
    return _cache
