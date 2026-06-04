"""
Stage 3d: AuthSchemaGenerator
Generates a complete auth/permissions schema from the architecture.
"""

from __future__ import annotations

import asyncio

import structlog

from models.architecture import ArchitectureSchema
from models.auth_schema import AuthSchema
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from utils.prompt_loader import load_prompt

logger = structlog.get_logger(__name__)


class AuthSchemaGenerator:
    def __init__(self, client: GeminiClient, tracker: CostTracker) -> None:
        self._client = client
        self._tracker = tracker
        self._log = logger.bind(stage="auth_generator")

    async def generate(self, arch: ArchitectureSchema) -> AuthSchema:
        arch_json = arch.model_dump_json(indent=2)
        prompt = load_prompt("auth_schema", architecture_json=arch_json)

        raw, usage = await self._client.generate_json(
            prompt=prompt,
            stage_name="auth_generator",
            model=GeminiClient.POWERFUL,
            temperature=0.2,
            max_tokens=4096,
        )
        self._tracker.track(usage)

        schema = AuthSchema(**raw)

        # Enforce: every role from architecture in permission_matrix
        arch_roles = set()
        for page in arch.pages:
            arch_roles.update(page.roles_allowed)
        for group in arch.api_groups:
            pass  # groups don't have roles directly

        matrix_roles = {r.role for r in schema.permission_matrix.roles}
        missing_roles = arch_roles - matrix_roles
        if missing_roles:
            self._log.warning("auth_missing_roles", missing=list(missing_roles))

        self._log.info("auth_schema_generated",
                       roles=len(schema.roles),
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
    gen = AuthSchemaGenerator(client=client, tracker=tracker)

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
        auth = await gen.generate(arch)
        print(f"✅ Auth roles: {auth.roles}")
        print(f"✅ Protected routes: {len(auth.protected_routes)}")
        print(f"✅ Permission matrix roles: {[r.role for r in auth.permission_matrix.roles]}")

    asyncio.run(run())
