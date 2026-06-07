"""
Groq API client wrapper with adaptive rate limiting, cost tracking, and structured JSON output.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, Dict, Optional, Tuple

from groq import AsyncGroq
import structlog

from utils.cost_tracker import CostTracker, UsageStats

logger = structlog.get_logger(__name__)


class GroqClientError(Exception):
    """Non-retryable Groq API error."""


class AdaptiveRateLimiter:
    """Token bucket style rate limiter to respect Groq quotas without blanket sleeps."""
    def __init__(self, rpm: int = 30):
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


class GroqClient:
    """
    Async wrapper around Groq with:
    - Structured JSON output (response_format={"type": "json_object"})
    - Adaptive token bucket rate limiting (30 RPM default)
    - Retry on 429/503/truncation with exponential backoff
    - Per-call cost and latency logging
    """

    FAST = "llama-3.3-70b-versatile"
    DEFAULT_MODEL = FAST
    MAX_RETRIES = 5
    BACKOFF_BASE = 5

    def __init__(self, api_key: str, tracker: Optional[CostTracker] = None, rpm: int = 25) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._tracker = tracker
        self._log = logger.bind(component="GroqClient")
        self._rate_limiter = AdaptiveRateLimiter(rpm=rpm)

    async def generate_json(
        self,
        prompt: str,
        stage_name: str,
        model: str = DEFAULT_MODEL,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> Tuple[Dict[str, Any], UsageStats]:
        
        # Groq requires JSON output instructions in the prompt if using json_object
        system_prompt = "You are a precise, deterministic system architect. You MUST output ONLY valid JSON matching the exact schema required. Do not include markdown blocks or any other text."
        if response_schema:
            system_prompt += f"\n\nYour output must exactly match this JSON schema:\n{json.dumps(response_schema, indent=2)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                await self._rate_limiter.wait_if_needed()

                start = time.perf_counter()
                
                response = await self._client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                
                latency_ms = int((time.perf_counter() - start) * 1000)

                choice = response.choices[0]
                finish_reason = choice.finish_reason

                if finish_reason and finish_reason.lower() == "length":
                    raise ValueError(f"Groq finish_reason={finish_reason} (incomplete output due to max_tokens)")

                raw_text = choice.message.content or ""
                raw_text = raw_text.strip()

                usage_meta = response.usage
                prompt_tokens = usage_meta.prompt_tokens if usage_meta else 0
                completion_tokens = usage_meta.completion_tokens if usage_meta else 0
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
                    "groq_call",
                    stage=stage_name,
                    tokens=total_tokens,
                    latency_ms=latency_ms,
                    attempt=attempt,
                )

                # Strip markdown fences if Llama decides to ignore the json_object constraint partially
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()

                try:
                    parsed = json.loads(raw_text)
                except json.JSONDecodeError as jde:
                    raise ValueError(f"Truncated/invalid JSON at char {jde.pos}: {jde.msg}") from jde

                return parsed, stats

            except Exception as exc:
                last_exc = exc
                exc_str = str(exc)

                # If we hit a daily token limit, do not retry because it won't resolve for hours.
                is_daily_limit = "tokens per day" in exc_str.lower() or "tpd" in exc_str.lower()

                if is_daily_limit:
                    if model == self.FAST:
                        # Fallback 1: The older 70B model (separate 100k quota)
                        self._log.warning("groq_daily_limit_fallback_1", original=model, fallback="llama3-70b-8192")
                        model = "llama3-70b-8192"
                        continue
                    elif model == "llama3-70b-8192":
                        # Fallback 2: The 8B model (separate 100k quota)
                        self._log.warning("groq_daily_limit_fallback_2", original=model, fallback="llama-3.1-8b-instant")
                        model = "llama-3.1-8b-instant"
                        continue
                    else:
                        self._log.error("groq_daily_limit_exhausted", stage=stage_name, error=exc_str)
                        raise GroqClientError(f"Groq daily token limit exhausted across all models: {exc_str}") from exc

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
                    or "length" in exc_str.lower()
                )

                if is_retryable and attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2)
                    self._log.warning(
                        "groq_retry",
                        stage=stage_name,
                        attempt=attempt,
                        wait_s=round(wait, 1),
                        error=exc_str,
                    )
                    await asyncio.sleep(wait)
                    continue

                self._log.error("groq_failed", stage=stage_name, error=exc_str)
                raise GroqClientError(f"Groq call failed at stage '{stage_name}': {exc_str}") from exc

        raise GroqClientError(f"Groq call failed after {self.MAX_RETRIES} retries") from last_exc
