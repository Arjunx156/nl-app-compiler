"""
Repository layer — CRUD operations for generation history and eval results.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import AsyncSessionLocal
from storage.models import GenerationRecord, EvalResultRecord
from models.output import CompilationResult


async def save_generation(result: CompilationResult) -> GenerationRecord:
    """Persist a CompilationResult to the database."""
    async with AsyncSessionLocal() as session:
        record = GenerationRecord(
            id=result.generation_id,
            prompt=result.prompt,
            status=result.status,
            app_type=result.intent.app_type.value if result.intent else "custom",
            full_result_json=result.model_dump_json(),
            page_count=result.execution_preview.page_count,
            table_count=result.execution_preview.table_count,
            endpoint_count=result.execution_preview.endpoint_count,
            role_count=result.execution_preview.role_count,
            total_tokens=result.metadata.total_tokens,
            cost_usd=result.metadata.cost_usd,
            latency_ms=result.metadata.latency_ms,
            repair_iterations=result.validation_report.repair_iterations,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_generation(gen_id: str) -> Optional[GenerationRecord]:
    async with AsyncSessionLocal() as session:
        result = await session.get(GenerationRecord, gen_id)
        return result


async def list_generations(limit: int = 50, offset: int = 0) -> List[GenerationRecord]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(GenerationRecord)
            .order_by(GenerationRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def search_generations(query: str) -> List[GenerationRecord]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(GenerationRecord)
            .where(GenerationRecord.prompt.ilike(f"%{query}%"))
            .order_by(GenerationRecord.created_at.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def save_eval_result(data: Dict[str, Any]) -> EvalResultRecord:
    async with AsyncSessionLocal() as session:
        record = EvalResultRecord(
            id=str(uuid.uuid4()),
            test_id=data.get("test_id", ""),
            test_name=data.get("test_name", ""),
            category=data.get("category", "normal"),
            status=data.get("status", "unknown"),
            score=data.get("score", 0),
            repair_iterations=data.get("repair_iterations", 0),
            latency_ms=data.get("latency_ms", 0),
            cost_usd=data.get("cost_usd", 0.0),
            error_message=data.get("error_message", ""),
            generation_id=data.get("generation_id", ""),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def list_eval_results() -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        stmt = select(EvalResultRecord).order_by(EvalResultRecord.created_at.desc())
        result = await session.execute(stmt)
        records = result.scalars().all()
        return [
            {
                "id": r.id,
                "test_id": r.test_id,
                "test_name": r.test_name,
                "category": r.category,
                "status": r.status,
                "score": r.score,
                "repair_iterations": r.repair_iterations,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
                "error_message": r.error_message,
                "generation_id": r.generation_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
