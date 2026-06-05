"""
Pydantic v2 models for the System Architect stage (Stage 2).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PageSpec(BaseModel):
    name: str = Field(..., description="Page name, e.g. Dashboard, Login")
    route: str = Field(..., description="URL route, e.g. /dashboard")
    description: str = Field(default="")
    requires_auth: bool = Field(default=True)
    roles_allowed: List[str] = Field(default_factory=list)
    parent_page: Optional[str] = Field(default=None)


class APIGroupSpec(BaseModel):
    name: str = Field(..., description="API group name, e.g. contacts, auth")
    base_path: str = Field(..., description="Base path, e.g. /api/contacts")
    description: str = Field(default="")
    entity_ref: Optional[str] = Field(default=None, description="Primary entity this group operates on")


class EntitySpec(BaseModel):
    name: str = Field(..., description="Entity name, e.g. User, Product")
    description: str = Field(default="")
    relationships: List[str] = Field(default_factory=list, description="Related entities")
    is_core: bool = Field(default=True)


class AuthStrategySpec(BaseModel):
    type: str = Field(..., description="jwt | session | oauth2")
    provider: Optional[str] = Field(default=None, description="e.g. google, github")
    token_expiry_hours: int = Field(default=24)
    refresh_token: bool = Field(default=True)
    mfa_enabled: bool = Field(default=False)


class BusinessRule(BaseModel):
    id: str = Field(..., description="Unique rule ID")
    description: str = Field(..., description="Human-readable rule")
    applies_to: List[str] = Field(default_factory=list, description="Roles or entities this applies to")
    condition: str = Field(default="", description="Condition expression")
    action: str = Field(default="", description="What happens when condition is met")


class DataFlowEdge(BaseModel):
    from_node: str = Field(..., description="Source node (page or entity)")
    to_node: str = Field(..., description="Target node (API or entity)")
    description: str = Field(default="")
    data_type: str = Field(default="json")


class ArchitectureSchema(BaseModel):
    pages: List[PageSpec] = Field(..., description="All app pages")
    api_groups: List[APIGroupSpec] = Field(..., description="API groupings")
    db_entities: List[EntitySpec] = Field(..., description="Database entities")
    auth_strategy: AuthStrategySpec = Field(..., description="Authentication approach")
    business_rules: List[BusinessRule] = Field(default_factory=list)
    data_flow: List[DataFlowEdge] = Field(default_factory=list)
