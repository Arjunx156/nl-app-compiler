"""
Pydantic v2 models for the UI Schema (Stage 3a).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    rule: str = Field(..., description="e.g. required | min_length:3 | email")
    message: str = Field(default="", description="Error message to show user")


class ComponentSpec(BaseModel):
    id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="e.g. table | form | chart | button | input | card | modal")
    props: Dict[str, Any] = Field(default_factory=dict, description="Component-specific props")
    data_binding: Optional[str] = Field(default=None, description="API endpoint this binds to, e.g. GET /api/contacts")
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    conditional_visibility: Optional[str] = Field(default=None, description="Condition for showing this component")
    children: List["ComponentSpec"] = Field(default_factory=list)


class PageUISpec(BaseModel):
    page_name: str = Field(..., description="Matches PageSpec.name from architecture")
    route: str = Field(..., description="URL route")
    title: str = Field(..., description="Page title shown in browser")
    layout: str = Field(default="default", description="Layout type: default | sidebar | full-width")
    components: List[ComponentSpec] = Field(..., description="UI components on this page")
    requires_auth: bool = Field(default=True)
    roles_allowed: List[str] = Field(default_factory=list)


class UISchema(BaseModel):
    pages: List[PageUISpec] = Field(..., description="All UI pages")
    navigation: Dict[str, Any] = Field(default_factory=dict, description="Navigation structure")
    theme: Dict[str, Any] = Field(default_factory=dict, description="Theme overrides")
