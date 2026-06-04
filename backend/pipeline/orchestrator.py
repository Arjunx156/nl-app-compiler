"""
Pipeline Orchestrator — wires all 5 stages together with SSE progress callbacks.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Awaitable, Callable

import structlog

from models.output import (
    AllSchemas, CompilationResult, ExecutionPreview,
    GenerationMetadata, ModelUsage,
)
from models.intent import ClarificationRequest
from models.validation import ValidationReport
from pipeline.intent_extractor import IntentExtractor
from pipeline.system_architect import SystemArchitect
from pipeline.schema_generators import (
    UISchemaGenerator, APISchemaGenerator,
    DBSchemaGenerator, AuthSchemaGenerator,
)
from pipeline.validator import CrossLayerValidator
from pipeline.repair_engine import RepairEngine
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.streaming import make_pipeline_event, make_log_event
from utils.cache import get_cache

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[dict], Awaitable[None]]


class PipelineOrchestrator:
    """Wires all 5 stages, streams progress via callback, returns CompilationResult."""

    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(component="orchestrator")

        self._intent_extractor = IntentExtractor(client, tracker)
        self._system_architect = SystemArchitect(client, tracker)
        self._ui_gen = UISchemaGenerator(client, tracker)
        self._api_gen = APISchemaGenerator(client, tracker)
        self._db_gen = DBSchemaGenerator(client, tracker)
        self._auth_gen = AuthSchemaGenerator(client, tracker)
        self._validator = CrossLayerValidator()
        self._repair = RepairEngine(client, tracker)

    async def compile(
        self,
        prompt: str,
        progress_callback: ProgressCallback,
    ) -> CompilationResult:
        generation_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        self._log.info("pipeline_start", generation_id=generation_id, prompt=prompt[:80])

        # Check cache
        cache = get_cache()
        cached = cache.get(prompt)
        if cached:
            await progress_callback(make_log_event("info", "⚡ Cache hit — returning cached result"))
            return cached

        async def emit(stage: str, status: str, message: str = "", tokens: int = 0) -> None:
            elapsed = int((time.perf_counter() - start_time) * 1000)
            await progress_callback(make_pipeline_event(
                stage=stage, status=status, message=message,
                elapsed_ms=elapsed, tokens_used=tokens,
            ))
            await progress_callback(make_log_event(
                "info" if status != "error" else "error",
                f"[{stage.upper()}] {status.upper()}: {message}",
            ))

        try:
            # ── Stage 1: Intent Extraction ────────────────────────────────
            await emit("intent", "running", "Extracting intent from prompt...")
            intent_result = await self._intent_extractor.extract(prompt)
            tokens = self._tracker.get_total().total_tokens

            if isinstance(intent_result, ClarificationRequest):
                await emit("intent", "clarification", "Clarification needed")
                return CompilationResult(
                    generation_id=generation_id,
                    status="failed",
                    prompt=prompt,
                    clarification_needed=intent_result,
                    metadata=self._build_metadata(start_time),
                )

            intent = intent_result
            await emit("intent", "done", f"App: {intent.app_name} | Type: {intent.app_type}", tokens)

            # ── Stage 2: System Architect ─────────────────────────────────
            await emit("architect", "running", "Designing system architecture...")
            arch = await self._system_architect.design(intent)
            tokens = self._tracker.get_total().total_tokens
            await emit("architect", "done",
                       f"{len(arch.pages)} pages | {len(arch.db_entities)} entities | "
                       f"{len(arch.api_groups)} API groups", tokens)

            # ── Stage 3: Schema Generators (parallel) ─────────────────────
            await emit("schemas", "running", "Generating UI, API, DB, Auth schemas in parallel...")
            ui_schema, api_schema, db_schema, auth_schema = await asyncio.gather(
                self._ui_gen.generate(arch),
                self._api_gen.generate(arch),
                self._db_gen.generate(arch),
                self._auth_gen.generate(arch),
            )
            tokens = self._tracker.get_total().total_tokens
            await emit("schemas", "done",
                       f"{len(ui_schema.pages)} pages | {len(api_schema.endpoints)} endpoints | "
                       f"{len(db_schema.tables)} tables | {len(auth_schema.roles)} roles", tokens)

            schemas = AllSchemas(ui=ui_schema, api=api_schema, db=db_schema, auth=auth_schema)

            # ── Stage 4: Validation ───────────────────────────────────────
            await emit("validation", "running", "Running 10 cross-layer validation checks...")
            validation_report = await self._validator.validate(
                ui_schema, api_schema, db_schema, auth_schema, arch, intent
            )
            tokens = self._tracker.get_total().total_tokens
            critical_errors = [e for e in validation_report.all_errors if e.severity.value == "critical"]
            await emit("validation", "done",
                       f"{validation_report.checks_passed}/{validation_report.checks_run} checks passed | "
                       f"{len(critical_errors)} critical errors", tokens)

            # ── Stage 5: Repair (if needed) ───────────────────────────────
            repair_iterations = 0
            if critical_errors:
                await emit("repair", "running",
                           f"Repairing {len(critical_errors)} critical errors...")

                async def revalidate(s: AllSchemas) -> ValidationReport:
                    return await self._validator.validate(
                        s.ui or ui_schema, s.api or api_schema,
                        s.db or db_schema, s.auth or auth_schema,
                        arch, intent,
                    )

                schemas, repair_iterations = await self._repair.repair(
                    errors=critical_errors,
                    schemas=schemas,
                    arch=arch,
                    revalidate_fn=revalidate,
                )
                tokens = self._tracker.get_total().total_tokens

                # Final validation after repair
                validation_report = await self._validator.validate(
                    schemas.ui or ui_schema, schemas.api or api_schema,
                    schemas.db or db_schema, schemas.auth or auth_schema,
                    arch, intent,
                )
                validation_report.repair_iterations = repair_iterations
                unfixed = [e for e in validation_report.all_errors if e.severity.value == "critical"]
                validation_report.errors_fixed = len(critical_errors) - len(unfixed)
                validation_report.unfixed_errors = unfixed

                await emit("repair", "done",
                           f"{repair_iterations} iterations | "
                           f"{validation_report.errors_fixed} errors fixed | "
                           f"{len(unfixed)} unfixed", tokens)

            # ── Build result ──────────────────────────────────────────────
            status = "success"
            if validation_report.unfixed_errors:
                status = "partial"

            final_ui = schemas.ui or ui_schema
            final_api = schemas.api or api_schema
            final_db = schemas.db or db_schema
            final_auth = schemas.auth or auth_schema

            preview = ExecutionPreview(
                table_count=len(final_db.tables),
                endpoint_count=len(final_api.endpoints),
                page_count=len(final_ui.pages),
                role_count=len(final_auth.roles),
                complexity="high" if intent.complexity_score >= 7
                           else "medium" if intent.complexity_score >= 4
                           else "low",
            )

            result = CompilationResult(
                generation_id=generation_id,
                status=status,
                prompt=prompt,
                intent=intent,
                architecture=arch,
                schemas=AllSchemas(
                    ui=final_ui, api=final_api,
                    db=final_db, auth=final_auth,
                ),
                validation_report=validation_report,
                assumptions_made=intent.assumptions,
                execution_preview=preview,
                metadata=self._build_metadata(start_time),
            )

            # Cache result
            cache.set(prompt, result)
            self._log.info("pipeline_done",
                           generation_id=generation_id,
                           status=status,
                           latency_ms=result.metadata.latency_ms)
            return result

        except Exception as exc:
            self._log.error("pipeline_error", error=str(exc), generation_id=generation_id)
            await emit("error", "error", str(exc))
            return CompilationResult(
                generation_id=generation_id,
                status="failed",
                prompt=prompt,
                error_message=str(exc),
                metadata=self._build_metadata(start_time),
            )

    def _build_metadata(self, start_time: float) -> GenerationMetadata:
        summary = self._tracker.get_total()
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        model_usage = {
            stage: ModelUsage(
                model=stats.model,
                tokens=stats.tokens,
                cost_usd=stats.cost_usd,
                latency_ms=stats.latency_ms,
            )
            for stage, stats in summary.by_stage.items()
        }
        return GenerationMetadata(
            latency_ms=latency_ms,
            llm_calls=summary.total_calls,
            total_tokens=summary.total_tokens,
            cost_usd=summary.total_cost_usd,
            model_usage=model_usage,
        )
