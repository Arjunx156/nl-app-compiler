"""
Pydantic v2 models for Validation (Stage 4).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    critical = "critical"
    warning = "warning"


class ValidationError(BaseModel):
    error_id: str = Field(..., description="Unique error identifier")
    check_id: str = Field(..., description="Which check caught this, e.g. V1, V2")
    stage: str = Field(..., description="Which stage produced the broken schema")
    layer: str = Field(..., description="ui | api | db | auth")
    severity: ValidationSeverity = Field(default=ValidationSeverity.critical)
    description: str = Field(..., description="Human-readable error description")
    affected_paths: List[str] = Field(default_factory=list, description="JSON paths to broken elements")
    suggested_fix: str = Field(default="", description="How to fix this error")
    before_value: Optional[Any] = Field(default=None, description="Value before fix")
    after_value: Optional[Any] = Field(default=None, description="Value after fix")
    repair_iteration: Optional[int] = Field(default=None, description="Which repair iteration fixed this")


class CheckResult(BaseModel):
    check_id: str = Field(..., description="e.g. V1")
    name: str = Field(..., description="Check name")
    description: str = Field(default="")
    passed: bool = Field(...)
    errors: List[ValidationError] = Field(default_factory=list)


class ValidationReport(BaseModel):
    checks_run: int = Field(default=0)
    checks_passed: int = Field(default=0)
    errors_found: int = Field(default=0)
    errors_fixed: int = Field(default=0)
    unfixed_errors: List[ValidationError] = Field(default_factory=list)
    repair_iterations: int = Field(default=0)
    check_results: List[CheckResult] = Field(default_factory=list)
    all_errors: List[ValidationError] = Field(default_factory=list)
