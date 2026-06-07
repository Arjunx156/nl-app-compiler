"""
Persistent Prompt Cache backed by SQLite + secondary in-memory cache.
Allows cross-restart cache hits.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

CACHE_DB_PATH = Path(__file__).parent.parent / "data" / "cache.db"


class PersistentPromptCache:
    TTL_SECONDS = 86400 * 7  # 7 days for DB cache
    MEM_TTL = 3600  # 1 hour for in-memory L1

    def __init__(self) -> None:
        self._mem_store: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        CACHE_DB_PATH.parent.mkdir(exist_ok=True, parents=True)
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expire_at REAL NOT NULL
                )
            """)
            conn.commit()
            
            # Cleanup expired on startup
            conn.execute("DELETE FROM prompt_cache WHERE expire_at < ?", (time.time(),))
            conn.commit()

    @staticmethod
    def _key(prompt: str) -> str:
        normalized = prompt.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[Any]:
        k = self._key(prompt)
        now = time.time()
        
        # 1. Check memory cache first
        with self._lock:
            entry = self._mem_store.get(k)
            if entry is not None:
                value, expire_at = entry
                if now < expire_at:
                    return value
                else:
                    del self._mem_store[k]
                    
        # 2. Check DB cache
        try:
            with sqlite3.connect(CACHE_DB_PATH) as conn:
                cursor = conn.execute("SELECT value, expire_at FROM prompt_cache WHERE key = ?", (k,))
                row = cursor.fetchone()
                if row:
                    value_json, expire_at = row
                    if now < expire_at:
                        # Rehydrate CompilationResult
                        from models.output import CompilationResult
                        result = CompilationResult.model_validate_json(value_json)
                        # Backfill memory cache
                        with self._lock:
                            self._mem_store[k] = (result, now + self.MEM_TTL)
                        logger.info("db_cache_hit", key=k[:8])
                        return result
                    else:
                        conn.execute("DELETE FROM prompt_cache WHERE key = ?", (k,))
                        conn.commit()
        except Exception as e:
            logger.error("db_cache_read_error", error=str(e))
            
        return None

    def set(self, prompt: str, result: Any) -> None:
        k = self._key(prompt)
        now = time.time()
        
        # Write to memory
        with self._lock:
            self._mem_store[k] = (result, now + self.MEM_TTL)
            
        # Write to DB
        try:
            from models.output import CompilationResult
            if isinstance(result, CompilationResult):
                value_json = result.model_dump_json()
                with sqlite3.connect(CACHE_DB_PATH) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO prompt_cache (key, value, expire_at) VALUES (?, ?, ?)",
                        (k, value_json, now + self.TTL_SECONDS)
                    )
                    conn.commit()
        except Exception as e:
            logger.error("db_cache_write_error", error=str(e))

    def clear(self) -> None:
        with self._lock:
            self._mem_store.clear()
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            conn.execute("DELETE FROM prompt_cache")
            conn.commit()


# Module-level singleton
_cache = PersistentPromptCache()


def get_cache() -> PersistentPromptCache:
    return _cache
