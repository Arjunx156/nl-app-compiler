"""
Stage 2: SystemArchitect
Designs a complete application architecture from a structured IntentSchema.
"""

from __future__ import annotations

import asyncio
import json

import structlog

from models.intent import IntentSchema
from models.architecture import ArchitectureSchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class SystemArchitect:
    """Designs ArchitectureSchema from IntentSchema."""

    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="system_architect")

    async def design(self, intent: IntentSchema) -> ArchitectureSchema:
        """
        Generate an ArchitectureSchema from an IntentSchema.
        Validates that every core entity and feature is covered.
        Re-prompts once if basic checks fail.
        """
        intent_json = intent.model_dump_json(indent=2)
        prompt = load_prompt("system_architect", intent_json=intent_json)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="system_architect",
            model=GeminiClient.FAST,
        )
        self._tracker.track(usage)
        self._log.info("architecture_generated", tokens=usage.total_tokens)

        arch = ArchitectureSchema(**raw)

        # Validate: every core entity must appear in db_entities
        db_entity_names = {e.name.lower() for e in arch.db_entities}
        missing_entities = [
            e for e in intent.core_entities
            if e.lower() not in db_entity_names
        ]

        # Validate: every feature must map to at least one api_group
        api_group_names = " ".join(g.name.lower() for g in arch.api_groups)
        missing_features = [
            f.name for f in intent.features
            if not any(word in api_group_names for word in f.name.lower().split())
        ]

        # Re-prompt if critical checks fail
        if missing_entities or missing_features:
            error_ctx = ""
            if missing_entities:
                error_ctx += f"\nMISSING ENTITIES (must be in db_entities): {missing_entities}"
            if missing_features:
                error_ctx += f"\nMISSING FEATURE COVERAGE (each must map to api_group): {missing_features}"

            self._log.warning("architecture_incomplete", missing_entities=missing_entities,
                              missing_features=missing_features)

            retry_prompt = (
                f"{prompt}\n\n"
                f"⚠️ YOUR PREVIOUS RESPONSE HAD THESE ISSUES:{error_ctx}\n"
                f"Please fix these issues and return the complete corrected architecture."
            )
            raw2, usage2 = await self._client.generate_json(
                prompt=retry_prompt,
                stage_name="system_architect_retry",
                model=GeminiClient.FAST,
            )
            self._tracker.track(usage2)
            arch = ArchitectureSchema(**raw2)

        self._log.info(
            "architecture_final",
            pages=len(arch.pages),
            api_groups=len(arch.api_groups),
            db_entities=len(arch.db_entities),
        )
        return arch


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    from utils.logger import setup_logging
    setup_logging()

    from models.intent import IntentSchema, AppType, FeatureSpec, RoleSpec

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    architect = SystemArchitect(client=client, tracker=tracker)

    # Use a realistic IntentSchema
    intent = IntentSchema(
        app_name="SalesCRM",
        app_type=AppType.crm,
        core_entities=["User", "Contact", "Deal", "Company"],
        features=[
            FeatureSpec(name="Login", description="Email/password authentication", priority="high"),
            FeatureSpec(name="Contacts", description="Manage contact list", priority="high"),
            FeatureSpec(name="Deals", description="Sales pipeline management", priority="high"),
            FeatureSpec(name="Analytics", description="Sales analytics dashboard", priority="medium"),
        ],
        user_roles=[
            RoleSpec(name="admin", description="Full access", is_admin=True),
            RoleSpec(name="manager", description="View analytics, manage team"),
            RoleSpec(name="sales_rep", description="Manage own contacts and deals"),
        ],
        integrations=[],
        ambiguities=[],
        assumptions=["Email/password auth", "JWT tokens"],
        complexity_score=6,
    )

    async def run_test():
        print("Testing SystemArchitect with CRM intent...")
        arch = await architect.design(intent)
        print(f"✅ Pages: {[p.name for p in arch.pages]}")
        print(f"✅ API groups: {[g.name for g in arch.api_groups]}")
        print(f"✅ DB entities: {[e.name for e in arch.db_entities]}")

        total = tracker.get_total()
        print(f"\n📊 Total tokens: {total.total_tokens}, Cost: ${total.total_cost_usd:.4f}")

    asyncio.run(run_test())
