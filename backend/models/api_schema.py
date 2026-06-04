"""
Pydantic v2 models for the API Schema (Stage 3b).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class FieldSpec(BaseModel):
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Data type: string | integer | boolean | array | object | uuid | datetime")
    required: bool = Field(default=True)
    validation: Optional[str] = Field(default=None, description="e.g. min:1|max:255|email")
    description: str = Field(default="")


class RequestBody(BaseModel):
    content_type: str = Field(default="application/json")
    fields: List[FieldSpec] = Field(default_factory=list)
    example: Dict[str, Any] = Field(default_factory=dict)


class ResponseBody(BaseModel):
    status_code: int = Field(default=200)
    content_type: str = Field(default="application/json")
    fields: List[FieldSpec] = Field(default_factory=list)
    is_list: bool = Field(default=False)
    example: Dict[str, Any] = Field(default_factory=dict)


class EndpointSpec(BaseModel):
    id: str = Field(..., description="Unique endpoint ID")
    path: str = Field(..., description="URL path, e.g. /api/contacts/{id}")
    method: HttpMethod = Field(..., description="HTTP method")
    summary: str = Field(..., description="Short description")
    description: str = Field(default="")
    request_body: Optional[RequestBody] = Field(default=None)
    response: ResponseBody = Field(...)
    auth_required: bool = Field(default=True)
    roles_allowed: List[str] = Field(default_factory=list)
    db_entity_ref: str = Field(..., description="Name of the DB entity this endpoint operates on")
    tags: List[str] = Field(default_factory=list)


class APISchema(BaseModel):
    endpoints: List[EndpointSpec] = Field(..., description="All API endpoints")
    base_url: str = Field(default="/api", description="API base URL")
    version: str = Field(default="v1")
    auth_header: str = Field(default="Authorization: Bearer <token>")
