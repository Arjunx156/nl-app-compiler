"""
Google Gemini API client wrapper with adaptive rate limiting, cost tracking, and structured JSON output.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, Dict, Optional, Tuple

import google.generativeai as genai
import structlog

from utils.cost_tracker import CostTracker, UsageStats

logger = structlog.get_logger(__name__)


class GeminiClientError(Exception):
    """Non-retryable Gemini API error."""


class AdaptiveRateLimiter:
    """Token bucket style rate limiter to respect Gemini quotas without blanket sleeps."""
    def __init__(self, rpm: int = 15):
        self.rpm = rpm
        self.interval = 60.0 / rpm
        self.last_call_time = 0.0
        self._lock = asyncio.Lock()

    async def wait_if_needed(self):
        async with self._lock:
            now = time.perf_counter()
            elapsed = now - self.last_call_time
            if elapsed < self.interval:
                wait_time = self.interval - elapsed
                await asyncio.sleep(wait_time)
            self.last_call_time = time.perf_counter()


class GeminiClient:
    """
    Async wrapper around Google Gemini with:
    - Structured JSON output (response_mime_type=application/json)
    - Adaptive token bucket rate limiting
    - Retry on 429/503/truncation with exponential backoff
    - Per-call cost and latency logging
    """

    FAST = "gemini-2.0-flash"
    DEFAULT_MODEL = FAST
    MAX_RETRIES = 5
    BACKOFF_BASE = 5

    def __init__(self, api_key: str, tracker: Optional[CostTracker] = None, rpm: int = 15) -> None:
        genai.configure(api_key=api_key)
        self._tracker = tracker
        self._log = logger.bind(component="GeminiClient")
        self._rate_limiter = AdaptiveRateLimiter(rpm=rpm)

    async def generate_json(
        self,
        prompt: str,
        stage_name: str,
        model: str = DEFAULT_MODEL,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_tokens: int = 16384,  # Reduced from 65536 to save quota on truncation
    ) -> Tuple[Dict[str, Any], UsageStats]:
        
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        }
        if response_schema:
            generation_config["response_schema"] = response_schema

        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # ── Wait on rate limiter instead of unconditional sleep ──
                await self._rate_limiter.wait_if_needed()

                start = time.perf_counter()
                gemini_model = genai.GenerativeModel(
                    model_name=model,
                    generation_config=generation_config,
                )
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: gemini_model.generate_content(prompt),
                )
                latency_ms = int((time.perf_counter() - start) * 1000)

                finish_reason = None
                try:
                    candidate = response.candidates[0]
                    finish_reason = str(candidate.finish_reason)
                except (IndexError, AttributeError):
                    pass

                if finish_reason and any(
                    bad in finish_reason.upper()
                    for bad in ("MAX_TOKENS", "SAFETY", "RECITATION", "OTHER")
                ):
                    raise ValueError(f"Gemini finish_reason={finish_reason} (incomplete output)")

                try:
                    raw_text = response.text.strip()
                except ValueError as ve:
                    raise ValueError(f"Blocked response: {ve}") from ve

                usage_meta = response.usage_metadata
                prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
                completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
                total_tokens = prompt_tokens + completion_tokens
                cost = CostTracker.estimate_cost(model, prompt_tokens, completion_tokens)

                stats = UsageStats(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    stage=stage_name,
                )

                if self._tracker:
                    self._tracker.track(stats)

                self._log.info(
                    "gemini_call",
                    stage=stage_name,
                    tokens=total_tokens,
                    latency_ms=latency_ms,
                    attempt=attempt,
                )

                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    raw_text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

                try:
                    parsed = json.loads(raw_text)
                except json.JSONDecodeError as jde:
                    raise ValueError(f"Truncated/invalid JSON at char {jde.pos}: {jde.msg}") from jde

                return parsed, stats

            except Exception as exc:
                last_exc = exc
                exc_str = str(exc)

                is_retryable = (
                    "429" in exc_str
                    or "503" in exc_str
                    or "quota" in exc_str.lower()
                    or "rate" in exc_str.lower()
                    or "unavailable" in exc_str.lower()
                    or "truncated" in exc_str.lower()
                    or "incomplete" in exc_str.lower()
                    or "invalid json" in exc_str.lower()
                    or "blocked" in exc_str.lower()
                    or "finish_reason" in exc_str.lower()
                )

                if is_retryable and attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2)
                    self._log.warning(
                        "gemini_retry",
                        stage=stage_name,
                        attempt=attempt,
                        wait_s=round(wait, 1),
                        error=exc_str,
                    )
                    await asyncio.sleep(wait)
                    continue

                self._log.error("gemini_failed", stage=stage_name, error=exc_str)
                raise GeminiClientError(f"Gemini call failed at stage '{stage_name}': {exc_str}") from exc

        raise GeminiClientError(f"Gemini call failed after {self.MAX_RETRIES} retries") from last_exc
