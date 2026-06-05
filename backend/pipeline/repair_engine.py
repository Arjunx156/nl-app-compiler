"""
Stage 5: RepairEngine
Surgically repairs validation errors by re-running only affected generators.
"""

from __future__ import annotations

import asyncio
from typing import Callable, List, Awaitable

import structlog

from models.validation import ValidationError, ValidationReport
from models.output import AllSchemas
from models.architecture import ArchitectureSchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class RepairEngine:
    """Surgically repairs schemas by re-running only affected sub-generators."""

    MAX_ITERATIONS = 3

    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="repair_engine")

    async def repair(
        self,
        errors: List[ValidationError],
        schemas: AllSchemas,
        arch: ArchitectureSchema,
        revalidate_fn: Callable[[AllSchemas], Awaitable[ValidationReport]] | None = None,
    ) -> tuple[AllSchemas, int]:
        """
        Repair schemas surgically.

        Returns:
            (repaired_schemas, iterations_used)
        """
        current_schemas = schemas.model_copy(deep=True)
        remaining_errors = list(errors)
        iterations = 0

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            if not remaining_errors:
                self._log.info("repair_complete", iteration=iteration - 1)
                break

            # Group errors by layer
            by_layer: dict[str, List[ValidationError]] = {}
            for err in remaining_errors:
                by_layer.setdefault(err.layer, []).append(err)

            self._log.info("repair_iteration",
                           iteration=iteration,
                           layers=list(by_layer.keys()),
                           error_count=len(remaining_errors))

            # Repair each affected layer
            repair_tasks = []
            for layer, layer_errors in by_layer.items():
                repair_tasks.append(self._repair_layer(
                    layer=layer,
                    errors=layer_errors,
                    schemas=current_schemas,
                    arch=arch,
                    iteration=iteration,
                ))

            repaired_layers = await asyncio.gather(*repair_tasks, return_exceptions=True)

            # Apply repairs
            for layer, result in zip(by_layer.keys(), repaired_layers):
                if isinstance(result, Exception):
                    self._log.error("repair_layer_failed", layer=layer, error=str(result))
                    continue
                if layer == "ui" and result is not None:
                    current_schemas.ui = result
                elif layer == "api" and result is not None:
                    current_schemas.api = result
                elif layer == "db" and result is not None:
                    current_schemas.db = result
                elif layer == "auth" and result is not None:
                    current_schemas.auth = result

            iterations = iteration

            # Re-validate if function provided
            if revalidate_fn:
                new_report = await revalidate_fn(current_schemas)
                # Only keep errors from repaired layers
                remaining_errors = [
                    e for e in new_report.all_errors
                    if e.layer in by_layer
                ]
                if not remaining_errors:
                    break
            else:
                break  # No revalidation, assume fixed

        return current_schemas, iterations

    async def _repair_layer(
        self,
        layer: str,
        errors: List[ValidationError],
        schemas: AllSchemas,
        arch: ArchitectureSchema,
        iteration: int,
    ):
        """Repair a specific schema layer."""
        error_description = "\n".join(
            f"[{e.check_id}] {e.description} (Fix: {e.suggested_fix})"
            for e in errors
        )
        affected_paths = [path for e in errors for path in e.affected_paths]

        self._log.info("repairing_layer", layer=layer, errors=len(errors), iteration=iteration)

        try:
            if layer == "api" and schemas.api:
                prompt = load_prompt(
                    "repair_api",
                    original_schema=schemas.api.model_dump_json(indent=2),
                    error_description=error_description,
                    affected_paths=str(affected_paths),
                    valid_entities=", ".join(e.name for e in arch.db_entities),
                )
                raw, usage = await self._client.generate_json(
                    prompt=prompt,
                    stage_name=f"repair_api_iter{iteration}",
                    model=GeminiClient.FAST,
                    temperature=0.1,
                )
                self._tracker.track(usage)
                from models.api_schema import APISchema
                return APISchema(**raw)

            elif layer == "db" and schemas.db:
                prompt = load_prompt(
                    "repair_db",
                    original_schema=schemas.db.model_dump_json(indent=2),
                    error_description=error_description,
                    affected_paths=str(affected_paths),
                )
                raw, usage = await self._client.generate_json(
                    prompt=prompt,
                    stage_name=f"repair_db_iter{iteration}",
                    model=GeminiClient.FAST,
                    temperature=0.1,
                )
                self._tracker.track(usage)
                from models.db_schema import DBSchema
                return DBSchema(**raw)

            elif layer == "auth" and schemas.auth:
                required_roles = list(set(
                    role for ep in (schemas.api.endpoints if schemas.api else [])
                    for role in ep.roles_allowed
                ))
                required_routes = [p.route for p in (schemas.ui.pages if schemas.ui else [])]
                prompt = load_prompt(
                    "repair_auth",
                    original_schema=schemas.auth.model_dump_json(indent=2),
                    error_description=error_description,
                    affected_paths=str(affected_paths),
                    required_roles=str(required_roles),
                    required_routes=str(required_routes),
                )
                raw, usage = await self._client.generate_json(
                    prompt=prompt,
                    stage_name=f"repair_auth_iter{iteration}",
                    model=GeminiClient.FAST,
                    temperature=0.1,
                )
                self._tracker.track(usage)
                from models.auth_schema import AuthSchema
                return AuthSchema(**raw)

            elif layer == "ui" and schemas.ui:
                prompt = load_prompt(
                    "repair_ui",
                    original_schema=schemas.ui.model_dump_json(indent=2),
                    error_description=error_description,
                    affected_paths=str(affected_paths),
                )
                raw, usage = await self._client.generate_json(
                    prompt=prompt,
                    stage_name=f"repair_ui_iter{iteration}",
                    model=GeminiClient.FAST,
                    temperature=0.1,
                )
                self._tracker.track(usage)
                from models.ui_schema import UISchema
                return UISchema(**raw)

        except Exception as exc:
            self._log.error("repair_failed", layer=layer, error=str(exc))
            raise

        return None
