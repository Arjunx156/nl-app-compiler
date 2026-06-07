"""
Deterministic UI Schema Builder — Stage 3a replacement.

Generates UISchema from ArchitectureSchema using a template engine.
Every page gets sensible default components based on its name and role.
Zero LLM calls.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import structlog

from models.architecture import ArchitectureSchema, PageSpec
from models.ui_schema import ComponentSpec, PageUISpec, UISchema, ValidationRule

logger = structlog.get_logger(__name__)


def _to_snake_case(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower().replace(" ", "_").replace("-", "_")


def _pluralise(name: str) -> str:
    if name.endswith("y") and not name.endswith("ey"):
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


# ---------------------------------------------------------------------------
# Page classifier: what kind of page is this?
# ---------------------------------------------------------------------------
_LOGIN_KEYWORDS = ("login", "signin", "sign_in", "auth")
_REGISTER_KEYWORDS = ("register", "signup", "sign_up", "create_account")
_DASHBOARD_KEYWORDS = ("dashboard", "home", "overview", "analytics", "summary")
_SETTINGS_KEYWORDS = ("setting", "profile", "account", "preference", "config")
_DETAIL_KEYWORDS = ("detail", "view", "show", "single")
_CREATE_KEYWORDS = ("create", "new", "add")
_EDIT_KEYWORDS = ("edit", "update", "modify")


def _classify_page(page: PageSpec) -> str:
    name = page.name.lower().replace(" ", "_")
    route = page.route.lower()
    combined = name + " " + route

    if any(k in combined for k in _LOGIN_KEYWORDS):
        return "login"
    if any(k in combined for k in _REGISTER_KEYWORDS):
        return "register"
    if any(k in combined for k in _DASHBOARD_KEYWORDS):
        return "dashboard"
    if any(k in combined for k in _SETTINGS_KEYWORDS):
        return "settings"
    if any(k in combined for k in _DETAIL_KEYWORDS) or re.search(r"/\{[^}]+\}", route):
        return "detail"
    if any(k in combined for k in _CREATE_KEYWORDS):
        return "create_form"
    if any(k in combined for k in _EDIT_KEYWORDS):
        return "edit_form"
    return "list"


def _infer_entity_from_page(page: PageSpec, arch: ArchitectureSchema) -> Optional[str]:
    """Try to find the primary entity for this page."""
    page_lower = page.name.lower()
    for entity in arch.db_entities:
        entity_lower = entity.name.lower()
        singular = entity_lower.rstrip("s")
        if entity_lower in page_lower or singular in page_lower:
            return entity.name
    return None


def _api_path_for(entity_name: str) -> str:
    snake = _to_snake_case(entity_name)
    return f"/api/{_pluralise(snake)}"


def _list_columns_for(entity_name: str) -> List[str]:
    lower = entity_name.lower()
    if any(k in lower for k in ("user", "account", "member")):
        return ["email", "first_name", "last_name", "role", "is_active", "created_at"]
    if any(k in lower for k in ("product", "item")):
        return ["name", "sku", "price", "stock_quantity", "is_active"]
    if "order" in lower:
        return ["id", "status", "total_amount", "order_date"]
    if "contact" in lower:
        return ["first_name", "last_name", "email", "company", "status"]
    if "deal" in lower or "opportunity" in lower:
        return ["title", "value", "stage", "probability", "close_date"]
    if any(k in lower for k in ("task", "ticket", "issue", "card")):
        return ["title", "status", "priority", "due_date"]
    if "employee" in lower:
        return ["first_name", "last_name", "email", "job_title", "is_active"]
    if "property" in lower or "listing" in lower:
        return ["title", "price", "address", "status", "bedrooms"]
    if "course" in lower:
        return ["title", "price", "duration_hours", "is_published"]
    return ["name", "status", "created_at"]


def _form_fields_for(entity_name: str) -> List[str]:
    lower = entity_name.lower()
    if any(k in lower for k in ("user", "account")):
        return ["email", "password", "first_name", "last_name"]
    if any(k in lower for k in ("product", "item")):
        return ["name", "description", "price", "sku", "stock_quantity"]
    if "order" in lower:
        return ["status", "total_amount", "notes"]
    if "contact" in lower:
        return ["first_name", "last_name", "email", "phone", "company"]
    if "deal" in lower:
        return ["title", "value", "stage", "probability", "close_date"]
    if any(k in lower for k in ("task", "ticket")):
        return ["title", "description", "status", "priority", "due_date"]
    return ["name", "description", "status"]


def _build_login_components(page: PageSpec) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    return [
        ComponentSpec(
            id=f"{page_slug}_form",
            type="form",
            props={"title": "Sign In", "fields": ["email", "password"],
                   "submit_label": "Login"},
            data_binding="POST /api/auth/login",
            validation_rules=[
                ValidationRule(rule="required", message="Email is required"),
                ValidationRule(rule="email", message="Enter a valid email"),
            ],
        ),
    ]


def _build_register_components(page: PageSpec) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    return [
        ComponentSpec(
            id=f"{page_slug}_form",
            type="form",
            props={"title": "Create Account",
                   "fields": ["email", "password", "first_name", "last_name"],
                   "submit_label": "Register"},
            data_binding="POST /api/auth/register",
            validation_rules=[
                ValidationRule(rule="required", message="All required fields must be filled"),
                ValidationRule(rule="email", message="Enter a valid email"),
            ],
        ),
    ]


def _build_dashboard_components(page: PageSpec, arch: ArchitectureSchema) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    comps: List[ComponentSpec] = [
        ComponentSpec(
            id=f"{page_slug}_stats",
            type="card",
            props={"title": "Overview", "variant": "stats-grid"},
            data_binding=None,
        ),
        ComponentSpec(
            id=f"{page_slug}_activity_chart",
            type="chart",
            props={"title": "Activity Overview", "chart_type": "line"},
            data_binding=None,
        ),
    ]
    # Add a recent-items table for the first core entity if available
    core_entities = [e for e in arch.db_entities if e.is_core]
    if core_entities:
        entity = core_entities[0]
        api_path = _api_path_for(entity.name)
        comps.append(ComponentSpec(
            id=f"{page_slug}_recent_{_to_snake_case(entity.name)}",
            type="table",
            props={"title": f"Recent {entity.name}s",
                   "columns": _list_columns_for(entity.name)[:4]},
            data_binding=f"GET {api_path}",
        ))
    return comps


def _build_list_components(page: PageSpec, entity_name: Optional[str],
                           arch: ArchitectureSchema) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    entity = entity_name or page.name
    api_path = _api_path_for(entity) if entity_name else None

    comps: List[ComponentSpec] = []

    # Search / filter bar
    comps.append(ComponentSpec(
        id=f"{page_slug}_search",
        type="input",
        props={"placeholder": f"Search {entity}s...", "type": "search"},
        data_binding=None,
    ))

    # Main table
    comps.append(ComponentSpec(
        id=f"{page_slug}_table",
        type="table",
        props={
            "title": f"{entity} List",
            "columns": _list_columns_for(entity) if entity_name else ["name", "status", "created_at"],
        },
        data_binding=f"GET {api_path}" if api_path else None,
    ))

    # Create button
    comps.append(ComponentSpec(
        id=f"{page_slug}_create_btn",
        type="button",
        props={"label": f"New {entity}", "variant": "primary"},
        data_binding=None,
    ))

    return comps


def _build_form_components(page: PageSpec, entity_name: Optional[str],
                           method: str = "POST") -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    entity = entity_name or page.name
    api_path = _api_path_for(entity) if entity_name else None

    fields = _form_fields_for(entity) if entity_name else ["name", "description"]
    endpoint = f"{method} {api_path}" if api_path else None

    return [
        ComponentSpec(
            id=f"{page_slug}_form",
            type="form",
            props={"title": page.name, "fields": fields, "submit_label": "Save"},
            data_binding=endpoint,
            validation_rules=[
                ValidationRule(rule="required", message="Required fields must be filled"),
            ],
        ),
        ComponentSpec(
            id=f"{page_slug}_cancel_btn",
            type="button",
            props={"label": "Cancel", "variant": "secondary"},
            data_binding=None,
        ),
    ]


def _build_detail_components(page: PageSpec, entity_name: Optional[str]) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    entity = entity_name or page.name
    api_path = f"{_api_path_for(entity)}/{{id}}" if entity_name else None

    return [
        ComponentSpec(
            id=f"{page_slug}_detail_card",
            type="card",
            props={"title": f"{entity} Details"},
            data_binding=f"GET {api_path}" if api_path else None,
        ),
        ComponentSpec(
            id=f"{page_slug}_edit_btn",
            type="button",
            props={"label": "Edit", "variant": "primary"},
            data_binding=None,
        ),
        ComponentSpec(
            id=f"{page_slug}_delete_btn",
            type="button",
            props={"label": "Delete", "variant": "danger"},
            data_binding=f"DELETE {api_path}" if api_path else None,
        ),
    ]


def _build_settings_components(page: PageSpec) -> List[ComponentSpec]:
    page_slug = _to_snake_case(page.name)
    return [
        ComponentSpec(
            id=f"{page_slug}_profile_form",
            type="form",
            props={"title": "Profile Settings",
                   "fields": ["first_name", "last_name", "email"],
                   "submit_label": "Save Changes"},
            data_binding="PUT /api/auth/me",
        ),
        ComponentSpec(
            id=f"{page_slug}_password_form",
            type="form",
            props={"title": "Change Password",
                   "fields": ["current_password", "new_password", "confirm_password"],
                   "submit_label": "Update Password"},
            data_binding="POST /api/auth/change-password",
        ),
    ]


class DeterministicUIBuilder:
    """
    Template-based UI schema builder. Generates UISchema from ArchitectureSchema.
    Zero LLM calls.
    """

    def __init__(self) -> None:
        self._log = logger.bind(stage="deterministic_ui_builder")

    def build(self, arch: ArchitectureSchema) -> UISchema:
        pages: List[PageUISpec] = []

        for page in arch.pages:
            page_type = _classify_page(page)
            entity_name = _infer_entity_from_page(page, arch)

            if page_type == "login":
                components = _build_login_components(page)
                layout = "full-width"
            elif page_type == "register":
                components = _build_register_components(page)
                layout = "full-width"
            elif page_type == "dashboard":
                components = _build_dashboard_components(page, arch)
                layout = "sidebar"
            elif page_type == "settings":
                components = _build_settings_components(page)
                layout = "sidebar"
            elif page_type == "detail":
                components = _build_detail_components(page, entity_name)
                layout = "sidebar"
            elif page_type == "create_form":
                components = _build_form_components(page, entity_name, "POST")
                layout = "sidebar"
            elif page_type == "edit_form":
                components = _build_form_components(page, entity_name, "PUT")
                layout = "sidebar"
            else:  # list (default)
                components = _build_list_components(page, entity_name, arch)
                layout = "sidebar"

            pages.append(PageUISpec(
                page_name=page.name,
                route=page.route,
                title=page.name,
                layout=layout,
                components=components,
                requires_auth=page.requires_auth,
                roles_allowed=page.roles_allowed,
            ))

        # Navigation structure from arch pages (exclude login/register)
        nav_items = [
            {"label": p.name, "route": p.route, "icon": _icon_for(p.name),
             "roles": p.roles_allowed}
            for p in arch.pages
            if not any(k in p.name.lower() for k in ("login", "register", "signup"))
        ]

        schema = UISchema(
            pages=pages,
            navigation={"type": "sidebar", "items": nav_items},
            theme={"primary_color": "#7c3aed", "dark_mode": True},
        )

        self._log.info("ui_schema_built", pages=len(pages))
        return schema


def _icon_for(page_name: str) -> str:
    lower = page_name.lower()
    if "dashboard" in lower or "home" in lower:
        return "home"
    if "user" in lower or "account" in lower or "profile" in lower:
        return "users"
    if any(k in lower for k in ("product", "item", "inventory")):
        return "package"
    if "order" in lower:
        return "shopping-cart"
    if "setting" in lower or "config" in lower:
        return "settings"
    if "analytic" in lower or "report" in lower or "chart" in lower:
        return "bar-chart"
    if "contact" in lower:
        return "address-book"
    if "deal" in lower or "opportunity" in lower:
        return "trending-up"
    if any(k in lower for k in ("task", "ticket", "issue")):
        return "check-square"
    if "project" in lower or "board" in lower:
        return "layout"
    if any(k in lower for k in ("employee", "staff", "hr")):
        return "briefcase"
    if "course" in lower or "lesson" in lower:
        return "book"
    return "file-text"
