"""
Deterministic Auth Schema Builder — Stage 3d replacement.

Derives AuthSchema directly from ArchitectureSchema + IntentSchema.
Zero LLM calls.
"""

from __future__ import annotations

from typing import List, Optional

import structlog

from models.architecture import ArchitectureSchema
from models.auth_schema import (
    AuthSchema, Permission, PermissionMatrix,
    ProtectedRoute, RolePermissions, TokenConfig,
)
from models.intent import IntentSchema

logger = structlog.get_logger(__name__)

_FULL_ACTIONS = ["create", "read", "update", "delete", "list"]
_READ_ACTIONS = ["read", "list"]


class DeterministicAuthBuilder:
    """
    Derives AuthSchema from ArchitectureSchema + IntentSchema. Zero LLM calls.
    """

    def __init__(self) -> None:
        self._log = logger.bind(stage="deterministic_auth_builder")

    def build(
        self,
        arch: ArchitectureSchema,
        intent: Optional[IntentSchema] = None,
    ) -> AuthSchema:
        # ── Roles ──────────────────────────────────────────────────────────
        # Collect roles from intent, falling back to roles mentioned in pages
        role_specs = intent.user_roles if intent and intent.user_roles else []
        roles: List[str] = [r.name for r in role_specs]

        # Also collect any extra roles only mentioned in architecture pages
        arch_roles: set[str] = set()
        for page in arch.pages:
            arch_roles.update(page.roles_allowed)
        for extra in arch_roles:
            if extra not in roles:
                roles.append(extra)

        if not roles:
            roles = ["admin", "user"]

        # ── Resources (from DB entities) ───────────────────────────────────
        resources = [e.name.lower() for e in arch.db_entities]

        # ── Permission matrix ──────────────────────────────────────────────
        admin_role_names = {r.name for r in role_specs if r.is_admin} if role_specs else {"admin"}
        if not admin_role_names:
            admin_role_names = {roles[0]}

        role_permission_entries: List[RolePermissions] = []
        for role in roles:
            if role in admin_role_names:
                # Admins get full CRUD on all resources
                perms = [Permission(resource=res, actions=_FULL_ACTIONS) for res in resources]
            else:
                # Non-admin roles: derive read access by default,
                # write access only for resources tied to their pages
                write_resources: set[str] = set()
                for page in arch.pages:
                    if role in page.roles_allowed:
                        # Grant write on entities whose name appears in the page name/description
                        for entity in arch.db_entities:
                            if entity.name.lower() in page.name.lower() or \
                               entity.name.lower() in page.description.lower():
                                write_resources.add(entity.name.lower())

                perms: List[Permission] = []
                for res in resources:
                    if res in write_resources:
                        perms.append(Permission(resource=res, actions=_FULL_ACTIONS))
                    else:
                        perms.append(Permission(resource=res, actions=_READ_ACTIONS))

            role_permission_entries.append(RolePermissions(role=role, permissions=perms))

        # ── Protected routes ───────────────────────────────────────────────
        protected_routes: List[ProtectedRoute] = []
        for page in arch.pages:
            if page.requires_auth:
                page_roles = page.roles_allowed if page.roles_allowed else roles
                protected_routes.append(ProtectedRoute(
                    route=page.route,
                    roles_allowed=page_roles,
                    redirect_to="/login",
                ))

        schema = AuthSchema(
            strategy="jwt",
            roles=roles,
            permission_matrix=PermissionMatrix(roles=role_permission_entries),
            protected_routes=protected_routes,
            token_config=TokenConfig(
                algorithm="HS256",
                access_token_expiry_minutes=60,
                refresh_token_expiry_days=30,
                issuer="nl-app-compiler",
            ),
            oauth_providers=[],
            password_policy={
                "min_length": 8,
                "require_uppercase": True,
                "require_number": True,
                "require_special": False,
            },
        )

        self._log.info(
            "auth_schema_built",
            roles=len(roles),
            protected_routes=len(protected_routes),
        )
        return schema
