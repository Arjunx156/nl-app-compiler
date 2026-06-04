"""
Google Gemini API client wrapper with retry, cost tracking, and structured JSON output.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Optional, Tuple

import google.generativeai as genai
import structlog

from utils.cost_tracker import CostTracker, UsageStats

logger = structlog.get_logger(__name__)


class GeminiClientError(Exception):
    """Non-retryable Gemini API error."""


class GeminiClient:
    """
    Async wrapper around Google Gemini with:
    - Structured JSON output (response_mime_type=application/json)
    - Retry on 429/503 with exponential backoff (max 3 retries)
    - Per-call cost and latency logging
    """

    FAST = "gemini-2.0-flash"
    POWERFUL = "gemini-1.5-pro"

    MAX_RETRIES = 3
    RETRY_STATUSES = {429, 503}

    def __init__(self, api_key: str, tracker: Optional[CostTracker] = None) -> None:
        genai.configure(api_key=api_key)
        self._tracker = tracker
        self._log = logger.bind(component="GeminiClient")

    async def generate_json(
        self,
        prompt: str,
        stage_name: str,
        model: str = FAST,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> Tuple[Dict[str, Any], UsageStats]:
        """
        Generate a JSON response from Gemini.

        Returns:
            (parsed_dict, UsageStats)

        Raises:
            GeminiClientError: on non-retryable failure after all retries.
        """
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
                start = time.perf_counter()
                gemini_model = genai.GenerativeModel(
                    model_name=model,
                    generation_config=generation_config,
                )
                # Run blocking SDK call in thread pool
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: gemini_model.generate_content(prompt),
                )
                latency_ms = int((time.perf_counter() - start) * 1000)

                # Parse usage
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
                    model=model,
                    tokens=total_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    attempt=attempt,
                )

                # Parse JSON
                raw_text = response.text.strip()
                # Strip markdown code fences if present
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    raw_text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

                parsed = json.loads(raw_text)
                return parsed, stats

            except Exception as exc:
                last_exc = exc
                exc_str = str(exc)

                # Check if retryable
                is_retryable = (
                    "429" in exc_str
                    or "503" in exc_str
                    or "quota" in exc_str.lower()
                    or "rate" in exc_str.lower()
                    or "unavailable" in exc_str.lower()
                )

                if is_retryable and attempt < self.MAX_RETRIES:
                    wait = 2 ** attempt
                    self._log.warning(
                        "gemini_retry",
                        stage=stage_name,
                        attempt=attempt,
                        wait_s=wait,
                        error=exc_str,
                    )
                    await asyncio.sleep(wait)
                    continue

                # Non-retryable or out of retries
                self._log.error(
                    "gemini_failed",
                    stage=stage_name,
                    error=exc_str,
                    attempt=attempt,
                )
                raise GeminiClientError(f"Gemini call failed at stage '{stage_name}': {exc_str}") from exc

        raise GeminiClientError(f"Gemini call failed after {self.MAX_RETRIES} retries") from last_exc
