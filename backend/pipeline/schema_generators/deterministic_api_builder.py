"""
Deterministic API Schema Builder — Stage 3b replacement.

Generates a complete APISchema from the ArchitectureSchema using a CRUD
generator. Every entity gets the standard 5 CRUD endpoints + auth endpoints
are always emitted. Zero LLM calls.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import structlog

from models.architecture import ArchitectureSchema, EntitySpec
from models.api_schema import APISchema, EndpointSpec, FieldSpec, HttpMethod, RequestBody, ResponseBody
from models.intent import IntentSchema

logger = structlog.get_logger(__name__)


def _to_snake_case(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower().replace(" ", "_").replace("-", "_")


def _pluralise(name: str) -> str:
    if name.endswith("y") and not name.endswith("ey"):
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


# ---------------------------------------------------------------------------
# Domain field rules: keyword → request body fields for POST/PUT
# ---------------------------------------------------------------------------
_FIELD_RULES: List[tuple[tuple[str, ...], List[FieldSpec]]] = [
    (("user", "account", "member"),
     [
         FieldSpec(name="email", type="string", required=True, validation="email", description="User email"),
         FieldSpec(name="password", type="string", required=True, validation="min:8", description="Password"),
         FieldSpec(name="first_name", type="string", required=False, description="First name"),
         FieldSpec(name="last_name", type="string", required=False, description="Last name"),
         FieldSpec(name="role", type="string", required=False, description="User role"),
     ]),
    (("product", "item", "good"),
     [
         FieldSpec(name="name", type="string", required=True, validation="min:1|max:255", description="Product name"),
         FieldSpec(name="description", type="string", required=False, description="Description"),
         FieldSpec(name="price", type="number", required=True, validation="min:0", description="Price"),
         FieldSpec(name="sku", type="string", required=False, description="SKU"),
         FieldSpec(name="stock_quantity", type="integer", required=False, description="Stock quantity"),
     ]),
    (("order",),
     [
         FieldSpec(name="status", type="string", required=False, description="Order status"),
         FieldSpec(name="total_amount", type="number", required=True, description="Total amount"),
         FieldSpec(name="notes", type="string", required=False, description="Notes"),
     ]),
    (("contact",),
     [
         FieldSpec(name="first_name", type="string", required=True, description="First name"),
         FieldSpec(name="last_name", type="string", required=False, description="Last name"),
         FieldSpec(name="email", type="string", required=False, validation="email", description="Email"),
         FieldSpec(name="phone", type="string", required=False, description="Phone"),
         FieldSpec(name="company", type="string", required=False, description="Company"),
     ]),
    (("deal", "opportunity"),
     [
         FieldSpec(name="title", type="string", required=True, description="Deal title"),
         FieldSpec(name="value", type="number", required=False, description="Deal value"),
         FieldSpec(name="stage", type="string", required=False, description="Pipeline stage"),
         FieldSpec(name="probability", type="integer", required=False, description="Win probability"),
         FieldSpec(name="close_date", type="datetime", required=False, description="Expected close date"),
     ]),
    (("appointment", "booking", "slot"),
     [
         FieldSpec(name="scheduled_at", type="datetime", required=True, description="Appointment time"),
         FieldSpec(name="duration_minutes", type="integer", required=False, description="Duration"),
         FieldSpec(name="notes", type="string", required=False, description="Notes"),
     ]),
    (("task", "card", "ticket", "issue"),
     [
         FieldSpec(name="title", type="string", required=True, description="Title"),
         FieldSpec(name="description", type="string", required=False, description="Description"),
         FieldSpec(name="status", type="string", required=False, description="Status"),
         FieldSpec(name="priority", type="string", required=False, description="Priority"),
         FieldSpec(name="due_date", type="datetime", required=False, description="Due date"),
     ]),
    (("project", "board"),
     [
         FieldSpec(name="name", type="string", required=True, description="Project name"),
         FieldSpec(name="description", type="string", required=False, description="Description"),
         FieldSpec(name="status", type="string", required=False, description="Status"),
         FieldSpec(name="start_date", type="datetime", required=False, description="Start date"),
         FieldSpec(name="end_date", type="datetime", required=False, description="End date"),
     ]),
    (("category", "tag"),
     [
         FieldSpec(name="name", type="string", required=True, description="Name"),
         FieldSpec(name="description", type="string", required=False, description="Description"),
     ]),
    (("payment", "transaction"),
     [
         FieldSpec(name="amount", type="number", required=True, description="Amount"),
         FieldSpec(name="currency", type="string", required=False, description="Currency"),
         FieldSpec(name="payment_method", type="string", required=False, description="Payment method"),
     ]),
    (("course",),
     [
         FieldSpec(name="title", type="string", required=True, description="Course title"),
         FieldSpec(name="description", type="string", required=False, description="Description"),
         FieldSpec(name="price", type="number", required=False, description="Price"),
         FieldSpec(name="duration_hours", type="integer", required=False, description="Duration in hours"),
     ]),
    (("employee", "staff"),
     [
         FieldSpec(name="first_name", type="string", required=True, description="First name"),
         FieldSpec(name="last_name", type="string", required=True, description="Last name"),
         FieldSpec(name="email", type="string", required=True, validation="email", description="Email"),
         FieldSpec(name="job_title", type="string", required=False, description="Job title"),
         FieldSpec(name="salary", type="number", required=False, description="Salary"),
     ]),
    (("property", "listing"),
     [
         FieldSpec(name="title", type="string", required=True, description="Property title"),
         FieldSpec(name="price", type="number", required=True, description="Price"),
         FieldSpec(name="address", type="string", required=True, description="Address"),
         FieldSpec(name="bedrooms", type="integer", required=False, description="Bedrooms"),
         FieldSpec(name="bathrooms", type="integer", required=False, description="Bathrooms"),
     ]),
]

_DEFAULT_FIELDS: List[FieldSpec] = [
    FieldSpec(name="name", type="string", required=True, description="Name"),
    FieldSpec(name="description", type="string", required=False, description="Description"),
    FieldSpec(name="status", type="string", required=False, description="Status"),
]


def _fields_for(entity_name: str) -> List[FieldSpec]:
    lower = entity_name.lower()
    for keywords, fields in _FIELD_RULES:
        if any(kw in lower for kw in keywords):
            return [f.model_copy() for f in fields]
    return [f.model_copy() for f in _DEFAULT_FIELDS]


def _id_field() -> FieldSpec:
    return FieldSpec(name="id", type="uuid", required=True, description="Resource ID")


def _response_fields(entity_name: str) -> List[FieldSpec]:
    """Response includes id + all writable fields."""
    return [_id_field()] + _fields_for(entity_name)


def _all_roles(intent: Optional[IntentSchema]) -> List[str]:
    if intent and intent.user_roles:
        return [r.name for r in intent.user_roles]
    return ["admin", "user"]


def _admin_roles(intent: Optional[IntentSchema]) -> List[str]:
    if intent and intent.user_roles:
        admins = [r.name for r in intent.user_roles if r.is_admin]
        return admins if admins else [intent.user_roles[0].name]
    return ["admin"]


def _entity_roles(entity: EntitySpec, arch: ArchitectureSchema,
                  intent: Optional[IntentSchema]) -> List[str]:
    """Derive roles that can access this entity from the architecture pages."""
    roles: set[str] = set()
    entity_lower = entity.name.lower()
    for page in arch.pages:
        if entity_lower in page.name.lower() or entity_lower in page.description.lower():
            roles.update(page.roles_allowed)
    if not roles:
        roles = set(_all_roles(intent))
    return sorted(roles)


class DeterministicAPIBuilder:
    """
    Deterministic API schema builder. Generates CRUD endpoints for every
    entity in the architecture. Zero LLM calls.
    """

    def __init__(self) -> None:
        self._log = logger.bind(stage="deterministic_api_builder")

    def build(self, arch: ArchitectureSchema, intent: Optional[IntentSchema] = None) -> APISchema:
        endpoints: List[EndpointSpec] = []

        # Auth endpoints (always present)
        endpoints.extend(self._auth_endpoints())

        for entity in arch.db_entities:
            snake = _to_snake_case(entity.name)
            plural = _pluralise(snake)
            base = f"/api/{plural}"
            all_r = _entity_roles(entity, arch, intent)
            admin_r = _admin_roles(intent)
            write_roles = list(set(all_r) | set(admin_r))
            body_fields = _fields_for(entity.name)
            resp_fields = _response_fields(entity.name)

            # GET /api/{entities}  — list
            endpoints.append(EndpointSpec(
                id=f"{plural}_list",
                path=base,
                method=HttpMethod.GET,
                summary=f"List {entity.name} records",
                description=f"Returns a paginated list of {entity.name} records",
                request_body=None,
                response=ResponseBody(status_code=200, fields=resp_fields, is_list=True),
                auth_required=True,
                roles_allowed=all_r,
                db_entity_ref=plural,  # matches DB table name exactly
                tags=[plural],
            ))

            # GET /api/{entities}/{id}  — get one
            endpoints.append(EndpointSpec(
                id=f"{plural}_get",
                path=f"{base}/{{id}}",
                method=HttpMethod.GET,
                summary=f"Get {entity.name} by ID",
                description=f"Returns a single {entity.name} record",
                request_body=None,
                response=ResponseBody(status_code=200, fields=resp_fields, is_list=False),
                auth_required=True,
                roles_allowed=all_r,
                db_entity_ref=plural,
                tags=[plural],
            ))

            # POST /api/{entities}  — create
            endpoints.append(EndpointSpec(
                id=f"{plural}_create",
                path=base,
                method=HttpMethod.POST,
                summary=f"Create {entity.name}",
                description=f"Creates a new {entity.name} record",
                request_body=RequestBody(fields=body_fields),
                response=ResponseBody(status_code=201, fields=resp_fields, is_list=False),
                auth_required=True,
                roles_allowed=write_roles,
                db_entity_ref=plural,
                tags=[plural],
            ))

            # PUT /api/{entities}/{id}  — update
            endpoints.append(EndpointSpec(
                id=f"{plural}_update",
                path=f"{base}/{{id}}",
                method=HttpMethod.PUT,
                summary=f"Update {entity.name}",
                description=f"Updates an existing {entity.name} record",
                request_body=RequestBody(fields=body_fields),
                response=ResponseBody(status_code=200, fields=resp_fields, is_list=False),
                auth_required=True,
                roles_allowed=write_roles,
                db_entity_ref=plural,
                tags=[plural],
            ))

            # DELETE /api/{entities}/{id}  — delete
            endpoints.append(EndpointSpec(
                id=f"{plural}_delete",
                path=f"{base}/{{id}}",
                method=HttpMethod.DELETE,
                summary=f"Delete {entity.name}",
                description=f"Permanently deletes a {entity.name} record",
                request_body=None,
                response=ResponseBody(status_code=204, fields=[], is_list=False),
                auth_required=True,
                roles_allowed=admin_r,
                db_entity_ref=plural,
                tags=[plural],
            ))

        schema = APISchema(endpoints=endpoints, base_url="/api", version="v1")
        self._log.info("api_schema_built", endpoints=len(endpoints))
        return schema

    def _auth_endpoints(self) -> List[EndpointSpec]:
        return [
            EndpointSpec(
                id="auth_login",
                path="/api/auth/login",
                method=HttpMethod.POST,
                summary="User login",
                description="Authenticates user and returns JWT token",
                request_body=RequestBody(fields=[
                    FieldSpec(name="email", type="string", required=True, validation="email"),
                    FieldSpec(name="password", type="string", required=True, validation="min:8"),
                ]),
                response=ResponseBody(status_code=200, fields=[
                    FieldSpec(name="access_token", type="string", required=True),
                    FieldSpec(name="refresh_token", type="string", required=True),
                    FieldSpec(name="expires_in", type="integer", required=True),
                ]),
                auth_required=False,
                roles_allowed=[],
                db_entity_ref="users",  # matches plural snake_case table name
                tags=["auth"],
            ),
            EndpointSpec(
                id="auth_register",
                path="/api/auth/register",
                method=HttpMethod.POST,
                summary="User registration",
                description="Creates a new user account",
                request_body=RequestBody(fields=[
                    FieldSpec(name="email", type="string", required=True, validation="email"),
                    FieldSpec(name="password", type="string", required=True, validation="min:8"),
                    FieldSpec(name="first_name", type="string", required=False),
                    FieldSpec(name="last_name", type="string", required=False),
                ]),
                response=ResponseBody(status_code=201, fields=[
                    FieldSpec(name="id", type="uuid", required=True),
                    FieldSpec(name="email", type="string", required=True),
                ]),
                auth_required=False,
                roles_allowed=[],
                db_entity_ref="users",  # matches plural snake_case table name
                tags=["auth"],
            ),
            EndpointSpec(
                id="auth_logout",
                path="/api/auth/logout",
                method=HttpMethod.POST,
                summary="User logout",
                description="Invalidates the current session token",
                request_body=None,
                response=ResponseBody(status_code=200, fields=[
                    FieldSpec(name="message", type="string", required=True),
                ]),
                auth_required=True,
                roles_allowed=[],
                db_entity_ref="users",  # matches plural snake_case table name
                tags=["auth"],
            ),
            EndpointSpec(
                id="auth_me",
                path="/api/auth/me",
                method=HttpMethod.GET,
                summary="Get current user",
                description="Returns the currently authenticated user's profile",
                request_body=None,
                response=ResponseBody(status_code=200, fields=[
                    FieldSpec(name="id", type="uuid", required=True),
                    FieldSpec(name="email", type="string", required=True),
                    FieldSpec(name="role", type="string", required=True),
                ]),
                auth_required=True,
                roles_allowed=[],
                db_entity_ref="users",  # matches plural snake_case table name
                tags=["auth"],
            ),
        ]
