"""
Pydantic v2 models for the Auth Schema (Stage 3d).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Permission(BaseModel):
    resource: str = Field(..., description="Resource name, e.g. contacts, orders")
    actions: List[str] = Field(..., description="Allowed actions: create | read | update | delete | list")


class RolePermissions(BaseModel):
    role: str = Field(..., description="Role name")
    permissions: List[Permission] = Field(default_factory=list)
    inherits_from: Optional[str] = Field(default=None, description="Parent role to inherit permissions from")


class PermissionMatrix(BaseModel):
    roles: List[RolePermissions] = Field(..., description="All roles and their permissions")


class ProtectedRoute(BaseModel):
    route: str = Field(..., description="URL route that is protected")
    roles_allowed: List[str] = Field(..., description="Which roles can access this route")
    redirect_to: str = Field(default="/login", description="Where to redirect if not authorized")


class TokenConfig(BaseModel):
    algorithm: str = Field(default="HS256")
    access_token_expiry_minutes: int = Field(default=60)
    refresh_token_expiry_days: int = Field(default=30)
    issuer: str = Field(default="nl-app-compiler")


class AuthSchema(BaseModel):
    strategy: str = Field(default="jwt", description="jwt | session | oauth2")
    roles: List[str] = Field(..., description="All role names in the system")
    permission_matrix: PermissionMatrix = Field(...)
    protected_routes: List[ProtectedRoute] = Field(default_factory=list)
    token_config: TokenConfig = Field(default_factory=TokenConfig)
    oauth_providers: List[str] = Field(default_factory=list)
    password_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "min_length": 8,
        "require_uppercase": True,
        "require_number": True,
        "require_special": False,
    })
