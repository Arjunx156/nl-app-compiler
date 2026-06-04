"""
Pydantic v2 models for the final CompilationResult output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.intent import IntentSchema, ClarificationRequest
from models.architecture import ArchitectureSchema
from models.ui_schema import UISchema
from models.api_schema import APISchema
from models.db_schema import DBSchema
from models.auth_schema import AuthSchema
from models.validation import ValidationReport


class ExecutionPreview(BaseModel):
    table_count: int = Field(default=0)
    endpoint_count: int = Field(default=0)
    page_count: int = Field(default=0)
    role_count: int = Field(default=0)
    complexity: str = Field(default="medium", description="low | medium | high")


class ModelUsage(BaseModel):
    model: str = Field(...)
    tokens: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    latency_ms: int = Field(default=0)


class GenerationMetadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    latency_ms: int = Field(default=0)
    llm_calls: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_usage: Dict[str, ModelUsage] = Field(default_factory=dict)


class AllSchemas(BaseModel):
    ui: Optional[UISchema] = Field(default=None)
    api: Optional[APISchema] = Field(default=None)
    db: Optional[DBSchema] = Field(default=None)
    auth: Optional[AuthSchema] = Field(default=None)


class CompilationResult(BaseModel):
    generation_id: str = Field(...)
    status: str = Field(..., description="success | partial | failed")
    prompt: str = Field(...)
    intent: Optional[IntentSchema] = Field(default=None)
    clarification_needed: Optional[ClarificationRequest] = Field(default=None)
    architecture: Optional[ArchitectureSchema] = Field(default=None)
    schemas: AllSchemas = Field(default_factory=AllSchemas)
    validation_report: ValidationReport = Field(default_factory=ValidationReport)
    assumptions_made: List[str] = Field(default_factory=list)
    execution_preview: ExecutionPreview = Field(default_factory=ExecutionPreview)
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
    error_message: Optional[str] = Field(default=None)
