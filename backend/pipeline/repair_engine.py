"""
Stage 5: RuleBasedRepairEngine
Surgically repairs validation errors by mutating the schema object.
Zero LLM calls for most common errors (V1, V5, V6, V7, V9).
Falls back to LLM for complex semantic fixes.
"""

from __future__ import annotations

import asyncio
from typing import Callable, List, Awaitable
import difflib

import structlog

from models.validation import ValidationError, ValidationReport
from models.output import AllSchemas
from models.architecture import ArchitectureSchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


def _closest_match(word: str, possibilities: List[str]) -> str | None:
    """Return the closest match, or None if no good match."""
    matches = difflib.get_close_matches(word.lower(), [p.lower() for p in possibilities], n=1, cutoff=0.7)
    if matches:
        match_lower = matches[0]
        # Return the original case
        for p in possibilities:
            if p.lower() == match_lower:
                return p
    return None


class RuleBasedRepairEngine:
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
        current_schemas = schemas.model_copy(deep=True)
        remaining_errors = list(errors)
        iterations = 0

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            if not remaining_errors:
                self._log.info("repair_complete", iteration=iteration - 1)
                break

            self._log.info("repair_iteration",
                           iteration=iteration,
                           error_count=len(remaining_errors))

            # Attempt mechanical fixes first
            unfixed_mechanically = []
            for err in remaining_errors:
                fixed = self._attempt_mechanical_fix(err, current_schemas, arch)
                if not fixed:
                    unfixed_mechanically.append(err)

            # Re-validate after mechanical fixes
            if revalidate_fn:
                new_report = await revalidate_fn(current_schemas)
                remaining_errors = [e for e in new_report.all_errors if e.severity.value == "critical"]
                
                # If everything is fixed, great!
                if not remaining_errors:
                    break

            # If there are still remaining critical errors that we couldn't fix mechanically,
            # we must fall back to the LLM. We group them by layer.
            if remaining_errors:
                by_layer: dict[str, List[ValidationError]] = {}
                for err in remaining_errors:
                    by_layer.setdefault(err.layer, []).append(err)

                repair_tasks = []
                for layer, layer_errors in by_layer.items():
                    repair_tasks.append(self._llm_repair_layer(
                        layer=layer,
                        errors=layer_errors,
                        schemas=current_schemas,
                        arch=arch,
                        iteration=iteration,
                    ))

                repaired_layers = await asyncio.gather(*repair_tasks, return_exceptions=True)

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

            # Final validation for this iteration
            if revalidate_fn:
                new_report = await revalidate_fn(current_schemas)
                remaining_errors = [e for e in new_report.all_errors if e.severity.value == "critical"]
                if not remaining_errors:
                    break
            else:
                break

        return current_schemas, iterations

    def _attempt_mechanical_fix(self, err: ValidationError, schemas: AllSchemas, arch: ArchitectureSchema) -> bool:
        """Attempt to fix the error by mutating the schemas directly. Return True if assumed fixed."""
        try:
            if err.check_id == "V1" and schemas.api and schemas.db:
                # API Entity References (db_entity_ref doesn't match a table)
                # Find the endpoint
                ep_id = err.affected_paths[0].split("[")[1].split("]")[0] if "[" in err.affected_paths[0] else None
                if not ep_id: return False
                
                ep = next((e for e in schemas.api.endpoints if e.id == ep_id), None)
                if not ep: return False

                valid_tables = [t.name for t in schemas.db.tables]
                best_match = _closest_match(ep.db_entity_ref, valid_tables)
                if not best_match:
                    # Fallback to checking the intent's core entities or just the first table if it's very close
                    best_match = _closest_match(ep.db_entity_ref, [e.name for e in arch.db_entities])
                    if best_match:
                        # Architecture entity name might need snake_case converting to table name. 
                        # We'll just leave it for LLM if it's this complex.
                        return False
                    return False

                ep.db_entity_ref = best_match
                self._log.info("mechanical_fix", check="V1", ep=ep_id, new_ref=best_match)
                return True

            elif err.check_id == "V5" and schemas.auth and schemas.ui:
                # Protected Routes Exist (auth protected route not in UI pages)
                route = err.affected_paths[0].split("[")[1].split("]")[0].strip("'\"") if "[" in err.affected_paths[0] else None
                if not route: return False
                
                # Check if we should just remove it from auth
                schemas.auth.protected_routes = [pr for pr in schemas.auth.protected_routes if pr.route != route]
                self._log.info("mechanical_fix", check="V5", removed_route=route)
                return True

            elif err.check_id == "V6" and schemas.api and schemas.auth:
                # API Roles in Auth (API endpoint has role not in auth schema)
                ep_id = err.affected_paths[0].split("[")[1].split("]")[0] if "[" in err.affected_paths[0] else None
                if not ep_id: return False
                
                ep = next((e for e in schemas.api.endpoints if e.id == ep_id), None)
                if not ep: return False

                # Add missing roles to auth schema
                added = False
                for role in ep.roles_allowed:
                    if role not in schemas.auth.roles:
                        schemas.auth.roles.append(role)
                        # Give them minimal permissions by default
                        from models.auth_schema import RolePermissions, Permission
                        schemas.auth.permission_matrix.roles.append(
                            RolePermissions(role=role, permissions=[])
                        )
                        added = True
                
                if added:
                    self._log.info("mechanical_fix", check="V6", ep=ep_id)
                return added

            elif err.check_id == "V7" and schemas.db:
                # FK References Valid (FK points to non-existent table/col)
                # Parse: db.tables[table_name].columns[col_name].references
                parts = err.affected_paths[0].split("[")
                if len(parts) < 3: return False
                
                table_name = parts[1].split("]")[0]
                col_name = parts[2].split("]")[0]
                
                table = next((t for t in schemas.db.tables if t.name == table_name), None)
                if not table: return False
                
                col = next((c for c in table.columns if c.name == col_name), None)
                if not col or not col.references: return False

                valid_tables = [t.name for t in schemas.db.tables]
                best_table = _closest_match(col.references.table, valid_tables)
                
                if not best_table:
                    return False
                
                ref_table = next((t for t in schemas.db.tables if t.name == best_table), None)
                if not ref_table: return False
                
                valid_cols = [c.name for c in ref_table.columns]
                best_col = _closest_match(col.references.column, valid_cols)
                if not best_col:
                    best_col = "id" if "id" in valid_cols else valid_cols[0]

                col.references.table = best_table
                col.references.column = best_col
                self._log.info("mechanical_fix", check="V7", table=table_name, col=col_name)
                return True

            elif err.check_id == "V9" and schemas.db:
                # Required Fields Not Nullable (PK is marked nullable)
                parts = err.affected_paths[0].split("[")
                if len(parts) < 3: return False
                
                table_name = parts[1].split("]")[0]
                col_name = parts[2].split("]")[0]
                
                table = next((t for t in schemas.db.tables if t.name == table_name), None)
                if not table: return False
                
                col = next((c for c in table.columns if c.name == col_name), None)
                if not col: return False

                col.nullable = False
                self._log.info("mechanical_fix", check="V9", table=table_name, col=col_name)
                return True

        except Exception as e:
            self._log.warning("mechanical_fix_error", check=err.check_id, error=str(e))
            return False

        return False

    async def _llm_repair_layer(
        self,
        layer: str,
        errors: List[ValidationError],
        schemas: AllSchemas,
        arch: ArchitectureSchema,
        iteration: int,
    ):
        """Fallback LLM repair for a specific schema layer."""
        error_description = "\n".join(
            f"[{e.check_id}] {e.description} (Fix: {e.suggested_fix})"
            for e in errors
        )
        affected_paths = [path for e in errors for path in e.affected_paths]

        self._log.info("llm_repairing_layer", layer=layer, errors=len(errors), iteration=iteration)

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
            self._log.error("llm_repair_failed", layer=layer, error=str(exc))
            raise

        return None
