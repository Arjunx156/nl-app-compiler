"""
Pydantic v2 models for the DB Schema (Stage 3c).
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FKReference(BaseModel):
    table: str = Field(..., description="Referenced table name")
    column: str = Field(default="id", description="Referenced column name")
    on_delete: str = Field(default="CASCADE", description="CASCADE | SET NULL | RESTRICT")


class ColumnSpec(BaseModel):
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="SQL type: VARCHAR | TEXT | INTEGER | BOOLEAN | TIMESTAMP | UUID | DECIMAL | JSON")
    nullable: bool = Field(default=False)
    default: Optional[Any] = Field(default=None)
    is_pk: bool = Field(default=False, description="Primary key")
    is_fk: bool = Field(default=False, description="Foreign key")
    references: Optional[FKReference] = Field(default=None, description="FK reference if is_fk=True")
    unique: bool = Field(default=False)
    index: bool = Field(default=False)
    description: str = Field(default="")


class IndexSpec(BaseModel):
    name: str = Field(..., description="Index name")
    columns: List[str] = Field(..., description="Columns in the index")
    unique: bool = Field(default=False)


class TableSpec(BaseModel):
    name: str = Field(..., description="Table name (snake_case)")
    description: str = Field(default="")
    columns: List[ColumnSpec] = Field(..., description="Table columns")
    indexes: List[IndexSpec] = Field(default_factory=list)
    primary_key: str = Field(default="id")


class DBSchema(BaseModel):
    tables: List[TableSpec] = Field(..., description="All database tables")
    db_type: str = Field(default="sqlite", description="sqlite | postgres | mysql")
    version: str = Field(default="1.0.0")
