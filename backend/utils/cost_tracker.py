"""
Cost tracker — accumulates token usage and cost per generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UsageStats:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    stage: str


@dataclass
class CostSummary:
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_calls: int = 0
    by_stage: Dict[str, "StageStats"] = field(default_factory=dict)


@dataclass
class StageStats:
    model: str = ""
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    calls: int = 0


class CostTracker:
    """Accumulates LLM usage statistics per generation."""

    # Gemini pricing per 1K tokens (approximate, June 2024)
    PRICING: Dict[str, Dict[str, float]] = {
        "gemini-2.0-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    }

    def __init__(self) -> None:
        self._records: List[UsageStats] = []

    @classmethod
    def estimate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = cls.PRICING.get(model, {"input": 0.001, "output": 0.003})
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def track(self, usage: UsageStats) -> None:
        self._records.append(usage)

    def get_total(self) -> CostSummary:
        summary = CostSummary()
        for rec in self._records:
            summary.total_tokens += rec.total_tokens
            summary.total_cost_usd += rec.cost_usd
            summary.total_calls += 1
            if rec.stage not in summary.by_stage:
                summary.by_stage[rec.stage] = StageStats(model=rec.model)
            s = summary.by_stage[rec.stage]
            s.tokens += rec.total_tokens
            s.cost_usd += rec.cost_usd
            s.latency_ms += rec.latency_ms
            s.calls += 1
            s.model = rec.model
        return summary
