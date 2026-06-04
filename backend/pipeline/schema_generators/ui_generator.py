"""
Stage 3a: UISchemaGenerator
Generates a complete UI schema from the architecture.
"""

from __future__ import annotations

import asyncio

import structlog

from models.architecture import ArchitectureSchema
from models.ui_schema import UISchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class UISchemaGenerator:
    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="ui_generator")

    async def generate(self, arch: ArchitectureSchema) -> UISchema:
        arch_json = arch.model_dump_json(indent=2)
        prompt = load_prompt("ui_schema", architecture_json=arch_json)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="ui_generator",
            model=GeminiClient.POWERFUL,
            temperature=0.2,
            max_tokens=8192,
        )
        self._tracker.track(usage)
        self._log.info("ui_schema_generated", pages=len(raw.get("pages", [])), tokens=usage.total_tokens)

        return UISchema(**raw)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    from utils.logger import setup_logging
    setup_logging()
    from pipeline.system_architect import SystemArchitect
    from models.intent import IntentSchema, AppType, FeatureSpec, RoleSpec

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    gen = UISchemaGenerator(client=client, tracker=tracker)
    architect = SystemArchitect(client=client, tracker=tracker)

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
        arch = await architect.design(intent)
        ui = await gen.generate(arch)
        print(f"✅ UI pages: {[p.page_name for p in ui.pages]}")
        print(f"✅ Total components: {sum(len(p.components) for p in ui.pages)}")

    asyncio.run(run())
