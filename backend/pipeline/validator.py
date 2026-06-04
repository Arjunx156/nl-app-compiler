"""
Stage 4: CrossLayerValidator
Runs all 10 cross-layer consistency checks across UI, API, DB, and Auth schemas.
"""

from __future__ import annotations

import uuid
from typing import List

import structlog

from models.ui_schema import UISchema
from models.api_schema import APISchema
from models.db_schema import DBSchema
from models.auth_schema import AuthSchema
from models.architecture import ArchitectureSchema
from models.intent import IntentSchema
from models.validation import (
    ValidationError, ValidationSeverity, CheckResult, ValidationReport
)

logger = structlog.get_logger(__name__)


class CrossLayerValidator:
    """Runs all 10 cross-layer validation checks."""

    async def validate(
        self,
        ui: UISchema,
        api: APISchema,
        db: DBSchema,
        auth: AuthSchema,
        arch: ArchitectureSchema | None = None,
        intent: IntentSchema | None = None,
    ) -> ValidationReport:
        check_results: List[CheckResult] = []

        check_results.append(self._check_v1_api_entity_refs(api, db))
        check_results.append(self._check_v2_api_field_column_match(api, db))
        check_results.append(self._check_v3_ui_binding_to_api(ui, api))
        check_results.append(self._check_v4_ui_form_to_api_body(ui, api))
        check_results.append(self._check_v5_protected_routes_exist(auth, ui))
        check_results.append(self._check_v6_api_roles_in_auth(api, auth))
        check_results.append(self._check_v7_fk_references_valid(db))
        check_results.append(self._check_v8_no_circular_deps(arch))
        check_results.append(self._check_v9_required_not_nullable(api, db))
        check_results.append(self._check_v10_gating_refs_valid(intent, auth))

        all_errors = [e for cr in check_results for e in cr.errors]
        passed = sum(1 for cr in check_results if cr.passed)

        report = ValidationReport(
            checks_run=len(check_results),
            checks_passed=passed,
            errors_found=len(all_errors),
            errors_fixed=0,
            unfixed_errors=all_errors,
            repair_iterations=0,
            check_results=check_results,
            all_errors=all_errors,
        )

        logger.info("validation_complete",
                    checks=len(check_results),
                    passed=passed,
                    errors=len(all_errors))
        return report

    # -------------------------------------------------------------------------
    # V1: API endpoint db_entity_ref exists in DBSchema.tables
    # -------------------------------------------------------------------------
    def _check_v1_api_entity_refs(self, api: APISchema, db: DBSchema) -> CheckResult:
        table_names = {t.name.lower() for t in db.tables}
        errors: List[ValidationError] = []

        for ep in api.endpoints:
            ref = ep.db_entity_ref.lower().replace(" ", "_")
            # Accept plural/singular variants
            variants = {ref, ref + "s", ref.rstrip("s")}
            if not variants.intersection(table_names):
                errors.append(ValidationError(
                    error_id=str(uuid.uuid4())[:8],
                    check_id="V1",
                    stage="api_generator",
                    layer="api",
                    severity=ValidationSeverity.critical,
                    description=f"Endpoint '{ep.id}' references db_entity '{ep.db_entity_ref}' "
                                f"which does not exist in DBSchema tables: {sorted(table_names)}",
                    affected_paths=[f"api.endpoints[{ep.id}].db_entity_ref"],
                    suggested_fix=f"Change db_entity_ref to one of: {sorted(table_names)}",
                ))

        return CheckResult(
            check_id="V1",
            name="API Entity References",
            description="All API endpoint db_entity_ref values exist in DBSchema tables",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V2: API request/response fields exist as columns in referenced table
    # -------------------------------------------------------------------------
    def _check_v2_api_field_column_match(self, api: APISchema, db: DBSchema) -> CheckResult:
        table_cols: dict[str, set] = {}
        for t in db.tables:
            table_cols[t.name.lower()] = {c.name.lower() for c in t.columns}

        errors: List[ValidationError] = []

        for ep in api.endpoints:
            ref = ep.db_entity_ref.lower().replace(" ", "_")
            # Find matching table
            matched = None
            for name in [ref, ref + "s", ref.rstrip("s")]:
                if name in table_cols:
                    matched = name
                    break
            if not matched:
                continue  # V1 already caught this

            cols = table_cols[matched]
            # Check request body fields
            if ep.request_body:
                for field in ep.request_body.fields:
                    if field.name.lower() not in cols and field.name.lower() not in {
                        "password", "confirm_password", "token", "refresh_token"
                    }:
                        errors.append(ValidationError(
                            error_id=str(uuid.uuid4())[:8],
                            check_id="V2",
                            stage="api_generator",
                            layer="api",
                            severity=ValidationSeverity.warning,
                            description=f"Request field '{field.name}' in endpoint '{ep.id}' "
                                        f"not found as column in table '{matched}'",
                            affected_paths=[f"api.endpoints[{ep.id}].request_body.fields[{field.name}]"],
                            suggested_fix=f"Add column '{field.name}' to table '{matched}' "
                                          f"or rename field to match existing column",
                        ))

        return CheckResult(
            check_id="V2",
            name="API Field → Column Match",
            description="API request/response fields exist as columns in referenced table",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V3: UI component data_bindings map to valid API endpoints
    # -------------------------------------------------------------------------
    def _check_v3_ui_binding_to_api(self, ui: UISchema, api: APISchema) -> CheckResult:
        valid_bindings = set()
        for ep in api.endpoints:
            valid_bindings.add(f"{ep.method.value} {ep.path}")
            # Also allow without method prefix
            valid_bindings.add(ep.path)

        errors: List[ValidationError] = []

        for page in ui.pages:
            for comp in page.components:
                if comp.data_binding and comp.data_binding.strip():
                    binding = comp.data_binding.strip()
                    # Check if binding matches any endpoint (flexible match)
                    matched = False
                    for vb in valid_bindings:
                        if binding in vb or vb in binding:
                            matched = True
                            break
                    if not matched:
                        errors.append(ValidationError(
                            error_id=str(uuid.uuid4())[:8],
                            check_id="V3",
                            stage="ui_generator",
                            layer="ui",
                            severity=ValidationSeverity.warning,
                            description=f"Component '{comp.id}' on page '{page.page_name}' "
                                        f"has data_binding '{binding}' that doesn't match any API endpoint",
                            affected_paths=[f"ui.pages[{page.page_name}].components[{comp.id}].data_binding"],
                            suggested_fix="Update data_binding to match an existing API endpoint path",
                        ))

        return CheckResult(
            check_id="V3",
            name="UI Binding → API Endpoint",
            description="UI component data_bindings map to valid API endpoints",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V4: UI form fields map to API request_body fields
    # -------------------------------------------------------------------------
    def _check_v4_ui_form_to_api_body(self, ui: UISchema, api: APISchema) -> CheckResult:
        # Build map of endpoint path → request body field names
        endpoint_fields: dict[str, set] = {}
        for ep in api.endpoints:
            if ep.request_body:
                endpoint_fields[ep.path] = {f.name.lower() for f in ep.request_body.fields}

        errors: List[ValidationError] = []

        for page in ui.pages:
            for comp in page.components:
                if comp.type == "form" and comp.data_binding:
                    # Extract path from binding (e.g., "POST /api/users" → "/api/users")
                    binding_parts = comp.data_binding.strip().split()
                    path = binding_parts[-1] if binding_parts else ""

                    if path in endpoint_fields:
                        ep_fields = endpoint_fields[path]
                        form_fields = set(comp.props.get("fields", []))
                        unknown = form_fields - ep_fields - {
                            "password", "confirm_password", "token"
                        }
                        if unknown:
                            errors.append(ValidationError(
                                error_id=str(uuid.uuid4())[:8],
                                check_id="V4",
                                stage="ui_generator",
                                layer="ui",
                                severity=ValidationSeverity.warning,
                                description=f"Form component '{comp.id}' has fields {unknown} "
                                            f"not in API request body for '{path}'",
                                affected_paths=[f"ui.pages[{page.page_name}].components[{comp.id}].props.fields"],
                                suggested_fix="Align form fields with API request body fields",
                            ))

        return CheckResult(
            check_id="V4",
            name="UI Form → API Body",
            description="UI form fields map to API request_body fields",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V5: All protected_routes exist in UISchema pages
    # -------------------------------------------------------------------------
    def _check_v5_protected_routes_exist(self, auth: AuthSchema, ui: UISchema) -> CheckResult:
        ui_routes = {p.route.lower() for p in ui.pages}
        errors: List[ValidationError] = []

        for pr in auth.protected_routes:
            if pr.route.lower() not in ui_routes:
                errors.append(ValidationError(
                    error_id=str(uuid.uuid4())[:8],
                    check_id="V5",
                    stage="auth_generator",
                    layer="auth",
                    severity=ValidationSeverity.critical,
                    description=f"Protected route '{pr.route}' doesn't exist in UISchema pages. "
                                f"Known routes: {sorted(ui_routes)}",
                    affected_paths=[f"auth.protected_routes[{pr.route}]"],
                    suggested_fix="Add the route to UISchema or remove the protected_route entry",
                ))

        return CheckResult(
            check_id="V5",
            name="Protected Routes Exist",
            description="All auth protected_routes exist in UISchema pages",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V6: All roles in API endpoints exist in AuthSchema.roles
    # -------------------------------------------------------------------------
    def _check_v6_api_roles_in_auth(self, api: APISchema, auth: AuthSchema) -> CheckResult:
        auth_roles = {r.lower() for r in auth.roles}
        errors: List[ValidationError] = []

        for ep in api.endpoints:
            for role in ep.roles_allowed:
                if role.lower() not in auth_roles:
                    errors.append(ValidationError(
                        error_id=str(uuid.uuid4())[:8],
                        check_id="V6",
                        stage="api_generator",
                        layer="api",
                        severity=ValidationSeverity.critical,
                        description=f"Endpoint '{ep.id}' allows role '{role}' "
                                    f"which is not defined in AuthSchema.roles: {sorted(auth.roles)}",
                        affected_paths=[f"api.endpoints[{ep.id}].roles_allowed"],
                        suggested_fix=f"Add role '{role}' to AuthSchema.roles or update endpoint",
                    ))

        return CheckResult(
            check_id="V6",
            name="API Roles in Auth",
            description="All roles referenced in API endpoints exist in AuthSchema",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V7: FK references point to existing tables and columns
    # -------------------------------------------------------------------------
    def _check_v7_fk_references_valid(self, db: DBSchema) -> CheckResult:
        table_map: dict[str, set] = {
            t.name.lower(): {c.name.lower() for c in t.columns}
            for t in db.tables
        }
        errors: List[ValidationError] = []

        for table in db.tables:
            for col in table.columns:
                if col.is_fk and col.references:
                    ref_table = col.references.table.lower()
                    ref_col = col.references.column.lower()
                    if ref_table not in table_map:
                        errors.append(ValidationError(
                            error_id=str(uuid.uuid4())[:8],
                            check_id="V7",
                            stage="db_generator",
                            layer="db",
                            severity=ValidationSeverity.critical,
                            description=f"Column '{table.name}.{col.name}' FK references "
                                        f"non-existent table '{col.references.table}'",
                            affected_paths=[f"db.tables[{table.name}].columns[{col.name}].references"],
                            suggested_fix=f"Change reference to an existing table: {sorted(table_map.keys())}",
                        ))
                    elif ref_col not in table_map[ref_table]:
                        errors.append(ValidationError(
                            error_id=str(uuid.uuid4())[:8],
                            check_id="V7",
                            stage="db_generator",
                            layer="db",
                            severity=ValidationSeverity.critical,
                            description=f"Column '{table.name}.{col.name}' FK references "
                                        f"non-existent column '{col.references.column}' in table '{col.references.table}'",
                            affected_paths=[f"db.tables[{table.name}].columns[{col.name}].references.column"],
                            suggested_fix=f"Change to an existing column in '{ref_table}'",
                        ))

        return CheckResult(
            check_id="V7",
            name="FK References Valid",
            description="All foreign key references point to existing tables and columns",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V8: No circular dependencies in data_flow
    # -------------------------------------------------------------------------
    def _check_v8_no_circular_deps(self, arch: ArchitectureSchema | None) -> CheckResult:
        if not arch:
            return CheckResult(
                check_id="V8",
                name="No Circular Dependencies",
                description="No circular dependencies in data_flow",
                passed=True,
                errors=[],
            )

        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for edge in arch.data_flow:
            if edge.from_node not in graph:
                graph[edge.from_node] = []
            graph[edge.from_node].append(edge.to_node)

        # Detect cycles using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    cycles.append(f"{node} → {neighbor}")
                    return True
            rec_stack.discard(node)
            return False

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)

        errors: List[ValidationError] = []
        for cycle in cycles:
            errors.append(ValidationError(
                error_id=str(uuid.uuid4())[:8],
                check_id="V8",
                stage="system_architect",
                layer="db",
                severity=ValidationSeverity.critical,
                description=f"Circular dependency detected in data_flow: {cycle}",
                affected_paths=["architecture.data_flow"],
                suggested_fix="Remove or restructure the circular data flow edge",
            ))

        return CheckResult(
            check_id="V8",
            name="No Circular Dependencies",
            description="No circular dependencies in architecture data_flow",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V9: Required fields are not nullable
    # -------------------------------------------------------------------------
    def _check_v9_required_not_nullable(self, api: APISchema, db: DBSchema) -> CheckResult:
        errors: List[ValidationError] = []

        for table in db.tables:
            for col in table.columns:
                if col.is_pk and col.nullable:
                    errors.append(ValidationError(
                        error_id=str(uuid.uuid4())[:8],
                        check_id="V9",
                        stage="db_generator",
                        layer="db",
                        severity=ValidationSeverity.critical,
                        description=f"Primary key column '{table.name}.{col.name}' is marked nullable",
                        affected_paths=[f"db.tables[{table.name}].columns[{col.name}].nullable"],
                        suggested_fix="Set nullable=false for primary key columns",
                    ))

        for ep in api.endpoints:
            if ep.request_body:
                for field in ep.request_body.fields:
                    if field.required and "optional" in field.description.lower():
                        errors.append(ValidationError(
                            error_id=str(uuid.uuid4())[:8],
                            check_id="V9",
                            stage="api_generator",
                            layer="api",
                            severity=ValidationSeverity.warning,
                            description=f"Field '{field.name}' in endpoint '{ep.id}' is marked "
                                        f"required=true but description says optional",
                            affected_paths=[f"api.endpoints[{ep.id}].request_body.fields[{field.name}]"],
                            suggested_fix="Align required flag with field description",
                        ))

        return CheckResult(
            check_id="V9",
            name="Required Fields Not Nullable",
            description="Required fields and PKs are not marked nullable",
            passed=len(errors) == 0,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # V10: Monetization gating references valid roles/routes
    # -------------------------------------------------------------------------
    def _check_v10_gating_refs_valid(
        self,
        intent: IntentSchema | None,
        auth: AuthSchema,
    ) -> CheckResult:
        if not intent or not intent.monetization:
            return CheckResult(
                check_id="V10",
                name="Monetization Gating Valid",
                description="Monetization gating references valid roles/routes",
                passed=True,
                errors=[],
            )

        auth_roles_lower = {r.lower() for r in auth.roles}
        errors: List[ValidationError] = []

        # Check tiers correspond to roles
        for tier in intent.monetization.tiers:
            tier_lower = tier.lower()
            related = [r for r in auth_roles_lower if tier_lower in r or r in tier_lower]
            if not related:
                errors.append(ValidationError(
                    error_id=str(uuid.uuid4())[:8],
                    check_id="V10",
                    stage="auth_generator",
                    layer="auth",
                    severity=ValidationSeverity.warning,
                    description=f"Monetization tier '{tier}' has no corresponding role in AuthSchema. "
                                f"Auth roles: {sorted(auth.roles)}",
                    affected_paths=["intent.monetization.tiers", "auth.roles"],
                    suggested_fix=f"Add a role for tier '{tier}' to AuthSchema",
                ))

        return CheckResult(
            check_id="V10",
            name="Monetization Gating Valid",
            description="Monetization gating tiers reference valid auth roles",
            passed=len(errors) == 0,
            errors=errors,
        )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    from models.ui_schema import UISchema, PageUISpec, ComponentSpec
    from models.api_schema import APISchema, EndpointSpec, ResponseBody, HttpMethod
    from models.db_schema import DBSchema, TableSpec, ColumnSpec
    from models.auth_schema import AuthSchema, PermissionMatrix, RolePermissions, ProtectedRoute

    validator = CrossLayerValidator()

    # Build minimal valid schemas
    db = DBSchema(tables=[
        TableSpec(
            name="users",
            columns=[
                ColumnSpec(name="id", type="UUID", is_pk=True),
                ColumnSpec(name="email", type="VARCHAR"),
                ColumnSpec(name="created_at", type="TIMESTAMP"),
                ColumnSpec(name="updated_at", type="TIMESTAMP"),
            ],
        )
    ])
    api = APISchema(endpoints=[
        EndpointSpec(
            id="users_list",
            path="/api/users",
            method=HttpMethod.GET,
            summary="List users",
            response=ResponseBody(fields=[]),
            db_entity_ref="users",
            roles_allowed=["admin"],
        )
    ])
    ui = UISchema(pages=[
        PageUISpec(
            page_name="Users",
            route="/users",
            title="Users",
            components=[
                ComponentSpec(id="users_table", type="table",
                              data_binding="GET /api/users")
            ],
        )
    ])
    auth = AuthSchema(
        roles=["admin", "user"],
        permission_matrix=PermissionMatrix(roles=[
            RolePermissions(role="admin", permissions=[]),
            RolePermissions(role="user", permissions=[]),
        ]),
        protected_routes=[ProtectedRoute(route="/users", roles_allowed=["admin"])],
    )

    async def run():
        print("Test 1: Valid schemas → expect 0 critical errors")
        report = await validator.validate(ui, api, db, auth)
        print(f"  Checks: {report.checks_run}, Passed: {report.checks_passed}, Errors: {report.errors_found}")

        print("\nTest 2: Bad db_entity_ref → expect V1 error")
        bad_ep = EndpointSpec(
            id="bad_ep",
            path="/api/nonexistent",
            method=HttpMethod.GET,
            summary="Bad",
            response=ResponseBody(fields=[]),
            db_entity_ref="nonexistent_table",
            roles_allowed=["admin"],
        )
        bad_api = APISchema(endpoints=[bad_ep])
        report2 = await validator.validate(ui, bad_api, db, auth)
        v1_errors = [e for e in report2.all_errors if e.check_id == "V1"]
        status = "✅" if v1_errors else "❌"
        print(f"  {status} V1 errors found: {len(v1_errors)}")

        print("\nTest 3: Missing auth role → expect V6 error")
        bad_api2 = APISchema(endpoints=[
            EndpointSpec(
                id="ep_unknown_role",
                path="/api/users",
                method=HttpMethod.GET,
                summary="List",
                response=ResponseBody(fields=[]),
                db_entity_ref="users",
                roles_allowed=["unknown_role"],
            )
        ])
        report3 = await validator.validate(ui, bad_api2, db, auth)
        v6_errors = [e for e in report3.all_errors if e.check_id == "V6"]
        status = "✅" if v6_errors else "❌"
        print(f"  {status} V6 errors found: {len(v6_errors)}")

    asyncio.run(run())
