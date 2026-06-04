"""
Stage 3c: DBSchemaGenerator
Generates a complete database schema from the architecture.
"""

from __future__ import annotations

import asyncio

import structlog

from models.architecture import ArchitectureSchema
from models.db_schema import DBSchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class DBSchemaGenerator:
    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="db_generator")

    async def generate(self, arch: ArchitectureSchema) -> DBSchema:
        arch_json = arch.model_dump_json(indent=2)
        prompt = load_prompt("db_schema", architecture_json=arch_json)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="db_generator",
            model=GeminiClient.POWERFUL,
            temperature=0.2,
            max_tokens=8192,
        )
        self._tracker.track(usage)

        schema = DBSchema(**raw)
        self._log.info("db_schema_generated",
                       tables=len(schema.tables),
                       tokens=usage.total_tokens)
        return schema


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    from utils.logger import setup_logging
    setup_logging()

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    gen = DBSchemaGenerator(client=client, tracker=tracker)

    from pipeline.system_architect import SystemArchitect
    from models.intent import IntentSchema, AppType, FeatureSpec, RoleSpec

    intent = IntentSchema(
        app_name="SalesCRM", app_type=AppType.crm,
        core_entities=["User", "Contact", "Deal"],
        features=[
            FeatureSpec(name="Login", description="Auth", priority="high"),
            FeatureSpec(name="Contacts", description="Contact management", priority="high"),
        ],
        user_roles=[RoleSpec(name="admin", is_admin=True), RoleSpec(name="sales_rep")],
        ambiguities=[], assumptions=[], complexity_score=5,
    )

    async def run():
        arch = await SystemArchitect(client, tracker).design(intent)
        db = await gen.generate(arch)
        print(f"✅ DB tables: {[t.name for t in db.tables]}")
        for t in db.tables:
            cols = [c.name for c in t.columns]
            has_required = all(req in cols for req in ["id", "created_at", "updated_at"])
            status = "✅" if has_required else "❌"
            print(f"   {status} {t.name}: {cols[:6]}")

    asyncio.run(run())
