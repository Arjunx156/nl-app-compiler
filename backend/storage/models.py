"""
SQLAlchemy ORM models for persistence.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base


class GenerationRecord(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    app_type: Mapped[str] = mapped_column(String(50), default="custom")
    full_result_json: Mapped[str] = mapped_column(Text)

    # Summary fields for quick listing
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    endpoint_count: Mapped[int] = mapped_column(Integer, default=0)
    role_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    repair_iterations: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt_preview": self.prompt[:120],
            "status": self.status,
            "app_type": self.app_type,
            "page_count": self.page_count,
            "table_count": self.table_count,
            "endpoint_count": self.endpoint_count,
            "role_count": self.role_count,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "repair_iterations": self.repair_iterations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EvalResultRecord(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    test_id: Mapped[str] = mapped_column(String(50), index=True)
    test_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer, default=0)
    repair_iterations: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    generation_id: Mapped[str] = mapped_column(String(36), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
