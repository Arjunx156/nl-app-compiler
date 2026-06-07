"""
Evaluation runner — runs all 20 test cases through the full pipeline.
Now utilizes adaptive rate limiting and parallel execution where possible.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Awaitable

import structlog

from evaluation.test_cases import EVAL_TEST_CASES, EvalTestCase, get_test_case
from pipeline.orchestrator import PipelineOrchestrator
from models.output import CompilationResult
from models.intent import ClarificationRequest
from storage.repository import save_eval_result
from utils.groq_client import GroqClient
from utils.cost_tracker import CostTracker

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[dict], Awaitable[None]]


def _score_result(tc: EvalTestCase, result: CompilationResult) -> int:
    """Score a compilation result 0-100 against test case expectations."""
    if result.status == "failed" and not result.clarification_needed:
        return 0

    score = 0

    # Clarification check (30 pts)
    if tc.should_request_clarification:
        if result.clarification_needed:
            score += 30
        elif result.status in ("success", "partial"):
            score += 10
    else:
        if not result.clarification_needed:
            score += 30

    # Schema completeness (40 pts)
    if result.schemas.db and len(result.schemas.db.tables) >= tc.expected_min_tables:
        score += 20
    elif result.schemas.db:
        score += 10

    if result.schemas.api and len(result.schemas.api.endpoints) >= tc.expected_min_endpoints:
        score += 20
    elif result.schemas.api:
        score += 10

    # Validation (20 pts)
    if result.validation_report.checks_run > 0:
        pass_rate = result.validation_report.checks_passed / result.validation_report.checks_run
        score += int(pass_rate * 20)

    # Status (10 pts)
    if result.status == "success":
        score += 10
    elif result.status == "partial":
        score += 5

    return min(score, 100)


class EvaluationRunner:
    def __init__(self, client: GroqClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(component="eval_runner")

    async def run_all(
        self,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        
        # We no longer need the hardcoded 30s sleep because:
        # 1) Pipeline now uses 2 LLM calls instead of 6-21.
        # 2) GroqClient now has an AdaptiveRateLimiter.
        # We can run these sequentially without sleeping, or in small parallel batches.
        # Running sequentially to keep logs clean.
        
        results = []
        for tc in EVAL_TEST_CASES:
            if progress_cb:
                await progress_cb({
                    "type": "progress",
                    "test_id": tc.id,
                    "test_name": tc.name,
                    "status": "running",
                })
                
            result = await self._run_case(tc)
            results.append(result)
            
            if progress_cb:
                await progress_cb({
                    "type": "progress",
                    "test_id": tc.id,
                    "test_name": tc.name,
                    "status": result["status"],
                    "score": result["score"],
                })

        # Aggregate metrics
        total = len(results)
        success = sum(1 for r in results if r["status"] == "success")
        avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0
        avg_cost = sum(r["cost_usd"] for r in results) / total if total else 0
        avg_score = sum(r["score"] for r in results) / total if total else 0
        avg_repairs = sum(r["repair_iterations"] for r in results) / total if total else 0

        return {
            "total": total,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "avg_latency_ms": round(avg_latency),
            "avg_cost_usd": round(avg_cost, 4),
            "avg_score": round(avg_score, 1),
            "avg_repair_iterations": round(avg_repairs, 2),
            "results": results,
        }

    async def run_single(self, test_id: str) -> Dict[str, Any]:
        tc = get_test_case(test_id)
        if not tc:
            return {"error": f"Test case '{test_id}' not found"}
        return await self._run_case(tc)

    async def _run_case(self, tc: EvalTestCase) -> Dict[str, Any]:
        self._log.info("eval_case_start", test_id=tc.id, name=tc.name)
        start = time.perf_counter()
        per_case_tracker = CostTracker()
        orchestrator = PipelineOrchestrator(
            client=self._client,
            tracker=per_case_tracker,
        )

        try:
            result = await orchestrator.compile(tc.prompt, progress_callback=_noop_cb)
            latency_ms = int((time.perf_counter() - start) * 1000)
            cost_summary = per_case_tracker.get_total()

            score = _score_result(tc, result)
            status = "success" if result.status == "success" else \
                     "clarification" if result.clarification_needed else \
                     "partial" if result.status == "partial" else "failed"

            data = {
                "test_id": tc.id,
                "test_name": tc.name,
                "category": tc.category,
                "status": status,
                "score": score,
                "repair_iterations": result.validation_report.repair_iterations,
                "latency_ms": latency_ms,
                "cost_usd": cost_summary.total_cost_usd,
                "error_message": result.error_message or "",
                "generation_id": result.generation_id,
            }

            await save_eval_result(data)
            self._log.info("eval_case_done", test_id=tc.id, score=score, status=status)
            return data

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._log.error("eval_case_error", test_id=tc.id, error=str(exc))
            data = {
                "test_id": tc.id,
                "test_name": tc.name,
                "category": tc.category,
                "status": "error",
                "score": 0,
                "repair_iterations": 0,
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
                "error_message": str(exc),
                "generation_id": "",
            }
            await save_eval_result(data)
            return data


async def _noop_cb(event: dict) -> None:
    """No-op progress callback for eval runs."""
    pass
