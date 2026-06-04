"""
models package — exports all Pydantic schemas.
"""

from models.intent import (
    AppType,
    FeatureSpec,
    RoleSpec,
    MonetizationSpec,
    IntentSchema,
    ClarificationRequest,
)
from models.architecture import (
    PageSpec,
    APIGroupSpec,
    EntitySpec,
    AuthStrategySpec,
    BusinessRule,
    DataFlowEdge,
    ArchitectureSchema,
)
from models.ui_schema import ComponentSpec, PageUISpec, UISchema
from models.api_schema import (
    HttpMethod,
    FieldSpec,
    RequestBody,
    ResponseBody,
    EndpointSpec,
    APISchema,
)
from models.db_schema import ColumnSpec, FKReference, IndexSpec, TableSpec, DBSchema
from models.auth_schema import (
    Permission,
    RolePermissions,
    PermissionMatrix,
    ProtectedRoute,
    TokenConfig,
    AuthSchema,
)
from models.validation import (
    ValidationSeverity,
    ValidationError,
    CheckResult,
    ValidationReport,
)
from models.output import (
    ExecutionPreview,
    ModelUsage,
    GenerationMetadata,
    AllSchemas,
    CompilationResult,
)

__all__ = [
    "AppType", "FeatureSpec", "RoleSpec", "MonetizationSpec",
    "IntentSchema", "ClarificationRequest",
    "PageSpec", "APIGroupSpec", "EntitySpec", "AuthStrategySpec",
    "BusinessRule", "DataFlowEdge", "ArchitectureSchema",
    "ComponentSpec", "PageUISpec", "UISchema",
    "HttpMethod", "FieldSpec", "RequestBody", "ResponseBody",
    "EndpointSpec", "APISchema",
    "ColumnSpec", "FKReference", "IndexSpec", "TableSpec", "DBSchema",
    "Permission", "RolePermissions", "PermissionMatrix", "ProtectedRoute",
    "TokenConfig", "AuthSchema",
    "ValidationSeverity", "ValidationError", "CheckResult", "ValidationReport",
    "ExecutionPreview", "ModelUsage", "GenerationMetadata", "AllSchemas",
    "CompilationResult",
]
