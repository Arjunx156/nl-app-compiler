"""
Stage 1: IntentExtractor
Extracts structured intent from a raw user prompt using Gemini.
"""

from __future__ import annotations

import asyncio
import json
from typing import Union

import structlog

from models.intent import IntentSchema, ClarificationRequest
from utils.groq_client import GroqClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class IntentExtractor:
    """Extracts structured IntentSchema from a raw user prompt."""

    def __init__(self, client: GroqClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="intent_extractor")

    async def extract(self, user_prompt: str) -> Union[IntentSchema, ClarificationRequest]:
        """
        Extract intent from user prompt.

        Returns:
            IntentSchema if the prompt is clear enough
            ClarificationRequest if the prompt is too vague or ambiguous
        """
        prompt = load_prompt("intent_extraction", user_prompt=user_prompt)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="intent_extraction",
            model=GroqClient.FAST,
            temperature=0.2,
            max_tokens=8192,
        )
        self._tracker.track(usage)
        self._log.info("intent_extracted", tokens=usage.total_tokens, cost=usage.cost_usd)

        # If the LLM returned needs_clarification
        if raw.get("needs_clarification"):
            return ClarificationRequest(**raw)

        # Parse into IntentSchema
        intent = IntentSchema(**raw)

        # Apply clarification rules — only block on truly vague prompts
        if intent.complexity_score < 2:
            return ClarificationRequest(
                needs_clarification=True,
                reason=f"Complexity score too low ({intent.complexity_score}/10) — prompt needs more detail",
                questions=intent.ambiguities[:6] if intent.ambiguities else [
                    "What are the main user roles?",
                    "What are the core features you need?",
                    "Do you need authentication?",
                    "What kind of data will the app store?",
                ],
                partial_intent=intent,
            )

        return intent


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    from utils.logger import setup_logging
    setup_logging()

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GroqClient(api_key=api_key)
    tracker = CostTracker()
    extractor = IntentExtractor(client=client, tracker=tracker)

    test_cases = [
        (
            "Build a CRM with login, contacts, deals, role-based access for "
            "sales reps and managers. Managers see analytics dashboard.",
            "IntentSchema",
        ),
        ("Build an app", "ClarificationRequest"),
        (
            "E-commerce store with products, categories, cart, checkout, "
            "and Stripe payments.",
            "IntentSchema",
        ),
    ]

    async def run_tests():
        for i, (prompt, expected_type) in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {prompt[:60]}... ---")
            result = await extractor.extract(prompt)
            actual_type = type(result).__name__
            status = "✅" if actual_type == expected_type else "❌"
            print(f"{status} Expected: {expected_type}, Got: {actual_type}")
            if hasattr(result, "app_name"):
                print(f"   App: {result.app_name}, Type: {result.app_type}, "
                      f"Complexity: {result.complexity_score}")
            elif hasattr(result, "questions"):
                print(f"   Reason: {result.reason}")
                print(f"   Questions: {result.questions[:2]}")

        total = tracker.get_total()
        print(f"\n📊 Total tokens: {total.total_tokens}, Cost: ${total.total_cost_usd:.4f}")

    asyncio.run(run_tests())
