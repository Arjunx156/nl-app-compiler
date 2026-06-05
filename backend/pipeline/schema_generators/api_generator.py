"""
Stage 3b: APISchemaGenerator
Generates a complete REST API schema from the architecture.
"""

from __future__ import annotations

import asyncio

import structlog

from models.architecture import ArchitectureSchema
from models.api_schema import APISchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class APISchemaGenerator:
    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="api_generator")

    async def generate(self, arch: ArchitectureSchema) -> APISchema:
        arch_json = arch.model_dump_json(indent=2)
        prompt = load_prompt("api_schema", architecture_json=arch_json)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="api_generator",
            model=GeminiClient.FAST,
            temperature=0.2,
            max_tokens=8192,
        )
        self._tracker.track(usage)

        schema = APISchema(**raw)
        self._log.info("api_schema_generated",
                       endpoints=len(schema.endpoints),
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
    gen = APISchemaGenerator(client=client, tracker=tracker)

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
        api = await gen.generate(arch)
        print(f"✅ API endpoints: {len(api.endpoints)}")
        for ep in api.endpoints[:5]:
            print(f"   {ep.method} {ep.path} → db_entity: {ep.db_entity_ref}")

    asyncio.run(run())
