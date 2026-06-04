"""
Pydantic v2 models for the Intent Extraction stage (Stage 1).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AppType(str, Enum):
    crm = "crm"
    ecommerce = "ecommerce"
    saas = "saas"
    dashboard = "dashboard"
    social = "social"
    custom = "custom"


class FeatureSpec(BaseModel):
    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="What this feature does")
    priority: str = Field(default="high", description="Priority: high | medium | low")
    requires_auth: bool = Field(default=True)


class RoleSpec(BaseModel):
    name: str = Field(..., description="Role name, e.g. admin, user, manager")
    description: str = Field(default="", description="What this role can do")
    is_admin: bool = Field(default=False)


class MonetizationSpec(BaseModel):
    model: str = Field(..., description="subscription | one-time | freemium | usage-based")
    tiers: List[str] = Field(default_factory=list, description="Tier names e.g. free, pro, enterprise")
    payment_provider: Optional[str] = Field(default=None, description="stripe | paypal | etc.")


class IntentSchema(BaseModel):
    app_name: str = Field(..., description="Inferred app name")
    app_type: AppType = Field(..., description="Category of app")
    core_entities: List[str] = Field(..., description="Main data entities, e.g. User, Product")
    features: List[FeatureSpec] = Field(..., description="List of features")
    user_roles: List[RoleSpec] = Field(..., description="User roles in the system")
    monetization: Optional[MonetizationSpec] = Field(default=None)
    integrations: List[str] = Field(default_factory=list, description="External integrations needed")
    ambiguities: List[str] = Field(default_factory=list, description="Unclear aspects of the prompt")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made")
    complexity_score: int = Field(..., ge=1, le=10, description="App complexity 1-10")


class ClarificationRequest(BaseModel):
    needs_clarification: bool = Field(default=True)
    reason: str = Field(..., description="Why clarification is needed")
    questions: List[str] = Field(..., description="Specific questions for the user")
    partial_intent: Optional[IntentSchema] = Field(default=None)
