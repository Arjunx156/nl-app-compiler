"""
Deterministic DB Schema Builder — Stage 3c replacement.

Generates a complete DBSchema from the ArchitectureSchema using a rule engine
and entity-to-column lookup table. Zero LLM calls.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import structlog

from models.architecture import ArchitectureSchema, EntitySpec
from models.db_schema import ColumnSpec, DBSchema, FKReference, IndexSpec, TableSpec

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Domain column rules: keyword → columns
# Each entry is (keyword_substrings, columns_list).
# First match wins. Order matters — more specific rules first.
# ---------------------------------------------------------------------------
_STANDARD_COLS: List[ColumnSpec] = [
    ColumnSpec(name="id", type="UUID", nullable=False, default="gen_random_uuid()",
               is_pk=True, is_fk=False, unique=True, index=True, description="Primary key"),
    ColumnSpec(name="created_at", type="TIMESTAMP", nullable=False,
               default="CURRENT_TIMESTAMP", description="Creation timestamp"),
    ColumnSpec(name="updated_at", type="TIMESTAMP", nullable=False,
               default="CURRENT_TIMESTAMP", description="Last update timestamp"),
]

_DOMAIN_RULES: List[tuple[tuple[str, ...], List[ColumnSpec]]] = [
    # Users / accounts
    (("user", "account", "member", "person"),
     [
         ColumnSpec(name="email", type="VARCHAR", nullable=False, unique=True, index=True, description="Email address"),
         ColumnSpec(name="password_hash", type="VARCHAR", nullable=False, description="Hashed password"),
         ColumnSpec(name="first_name", type="VARCHAR", nullable=True, description="First name"),
         ColumnSpec(name="last_name", type="VARCHAR", nullable=True, description="Last name"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Account active flag"),
         ColumnSpec(name="role", type="VARCHAR", nullable=False, default="user", description="User role"),
     ]),
    # Products / items / goods
    (("product", "item", "good", "sku", "listing"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Product name"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Product description"),
         ColumnSpec(name="price", type="DECIMAL", nullable=False, default=0, description="Price"),
         ColumnSpec(name="sku", type="VARCHAR", nullable=True, unique=True, index=True, description="Stock-keeping unit"),
         ColumnSpec(name="stock_quantity", type="INTEGER", nullable=False, default=0, description="Stock count"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Active flag"),
     ]),
    # Orders
    (("order",),
     [
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="pending", index=True, description="Order status"),
         ColumnSpec(name="total_amount", type="DECIMAL", nullable=False, default=0, description="Total amount"),
         ColumnSpec(name="currency", type="VARCHAR", nullable=False, default="USD", description="Currency code"),
         ColumnSpec(name="order_date", type="TIMESTAMP", nullable=False, default="CURRENT_TIMESTAMP", description="Order date"),
         ColumnSpec(name="notes", type="TEXT", nullable=True, description="Order notes"),
     ]),
    # Contacts (CRM)
    (("contact",),
     [
         ColumnSpec(name="first_name", type="VARCHAR", nullable=False, description="First name"),
         ColumnSpec(name="last_name", type="VARCHAR", nullable=True, description="Last name"),
         ColumnSpec(name="email", type="VARCHAR", nullable=True, index=True, description="Email"),
         ColumnSpec(name="phone", type="VARCHAR", nullable=True, description="Phone number"),
         ColumnSpec(name="company", type="VARCHAR", nullable=True, description="Company name"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="active", description="Contact status"),
     ]),
    # Deals / opportunities (CRM)
    (("deal", "opportunity", "pipeline"),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Deal title"),
         ColumnSpec(name="value", type="DECIMAL", nullable=True, description="Deal monetary value"),
         ColumnSpec(name="stage", type="VARCHAR", nullable=False, default="prospect", index=True, description="Sales stage"),
         ColumnSpec(name="probability", type="INTEGER", nullable=False, default=0, description="Win probability %"),
         ColumnSpec(name="close_date", type="TIMESTAMP", nullable=True, description="Expected close date"),
     ]),
    # Appointments / slots / bookings
    (("appointment", "booking", "slot", "schedule"),
     [
         ColumnSpec(name="scheduled_at", type="TIMESTAMP", nullable=False, index=True, description="Appointment time"),
         ColumnSpec(name="duration_minutes", type="INTEGER", nullable=False, default=30, description="Duration in minutes"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="pending", description="Appointment status"),
         ColumnSpec(name="notes", type="TEXT", nullable=True, description="Notes"),
         ColumnSpec(name="location", type="VARCHAR", nullable=True, description="Location or meeting link"),
     ]),
    # Tasks / cards (project management)
    (("task", "card", "ticket", "issue"),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Title"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="todo", index=True, description="Status"),
         ColumnSpec(name="priority", type="VARCHAR", nullable=False, default="medium", description="Priority level"),
         ColumnSpec(name="due_date", type="TIMESTAMP", nullable=True, description="Due date"),
     ]),
    # Projects / boards
    (("project", "board", "workspace"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Project name"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="active", description="Status"),
         ColumnSpec(name="start_date", type="TIMESTAMP", nullable=True, description="Start date"),
         ColumnSpec(name="end_date", type="TIMESTAMP", nullable=True, description="End date"),
     ]),
    # Categories
    (("category", "tag", "label", "genre"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, unique=True, description="Category name"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="slug", type="VARCHAR", nullable=True, unique=True, description="URL-friendly name"),
     ]),
    # Payments / transactions
    (("payment", "transaction", "invoice"),
     [
         ColumnSpec(name="amount", type="DECIMAL", nullable=False, description="Payment amount"),
         ColumnSpec(name="currency", type="VARCHAR", nullable=False, default="USD", description="Currency"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="pending", index=True, description="Status"),
         ColumnSpec(name="payment_method", type="VARCHAR", nullable=True, description="Payment method"),
         ColumnSpec(name="reference_id", type="VARCHAR", nullable=True, unique=True, description="External reference ID"),
         ColumnSpec(name="paid_at", type="TIMESTAMP", nullable=True, description="Payment timestamp"),
     ]),
    # Notifications / alerts
    (("notification", "alert", "message"),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Notification title"),
         ColumnSpec(name="body", type="TEXT", nullable=True, description="Notification body"),
         ColumnSpec(name="type", type="VARCHAR", nullable=False, default="info", description="Notification type"),
         ColumnSpec(name="is_read", type="BOOLEAN", nullable=False, default=False, description="Read flag"),
     ]),
    # Files / attachments / media
    (("file", "attachment", "document", "media", "asset"),
     [
         ColumnSpec(name="filename", type="VARCHAR", nullable=False, description="Original filename"),
         ColumnSpec(name="file_url", type="VARCHAR", nullable=False, description="Storage URL"),
         ColumnSpec(name="file_size", type="INTEGER", nullable=True, description="Size in bytes"),
         ColumnSpec(name="mime_type", type="VARCHAR", nullable=True, description="MIME type"),
     ]),
    # Reviews / ratings / feedback
    (("review", "rating", "feedback"),
     [
         ColumnSpec(name="rating", type="INTEGER", nullable=False, description="Numeric rating"),
         ColumnSpec(name="comment", type="TEXT", nullable=True, description="Review text"),
         ColumnSpec(name="is_approved", type="BOOLEAN", nullable=False, default=False, description="Moderation flag"),
     ]),
    # Courses / lessons (LMS)
    (("course",),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Course title"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="price", type="DECIMAL", nullable=False, default=0, description="Price"),
         ColumnSpec(name="duration_hours", type="INTEGER", nullable=True, description="Total hours"),
         ColumnSpec(name="is_published", type="BOOLEAN", nullable=False, default=False, description="Published flag"),
     ]),
    (("lesson", "module", "chapter"),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Lesson title"),
         ColumnSpec(name="content", type="TEXT", nullable=True, description="Lesson content"),
         ColumnSpec(name="order_index", type="INTEGER", nullable=False, default=0, description="Display order"),
         ColumnSpec(name="duration_minutes", type="INTEGER", nullable=True, description="Duration in minutes"),
         ColumnSpec(name="is_published", type="BOOLEAN", nullable=False, default=False, description="Published flag"),
     ]),
    # Employees / HR
    (("employee", "staff", "worker"),
     [
         ColumnSpec(name="first_name", type="VARCHAR", nullable=False, description="First name"),
         ColumnSpec(name="last_name", type="VARCHAR", nullable=False, description="Last name"),
         ColumnSpec(name="email", type="VARCHAR", nullable=False, unique=True, index=True, description="Work email"),
         ColumnSpec(name="job_title", type="VARCHAR", nullable=True, description="Job title"),
         ColumnSpec(name="salary", type="DECIMAL", nullable=True, description="Salary"),
         ColumnSpec(name="hire_date", type="TIMESTAMP", nullable=True, description="Date of hire"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Employment status"),
     ]),
    (("department", "team", "group"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, unique=True, description="Department name"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="budget", type="DECIMAL", nullable=True, description="Budget"),
     ]),
    # Properties / real estate
    (("property", "listing", "estate"),
     [
         ColumnSpec(name="title", type="VARCHAR", nullable=False, description="Property title"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
         ColumnSpec(name="price", type="DECIMAL", nullable=False, description="Price"),
         ColumnSpec(name="address", type="TEXT", nullable=False, description="Address"),
         ColumnSpec(name="bedrooms", type="INTEGER", nullable=True, description="Number of bedrooms"),
         ColumnSpec(name="bathrooms", type="INTEGER", nullable=True, description="Number of bathrooms"),
         ColumnSpec(name="area_sqft", type="DECIMAL", nullable=True, description="Area in sq ft"),
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="available", description="Listing status"),
     ]),
    # Restaurants / venues
    (("restaurant", "venue", "store", "shop"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Name"),
         ColumnSpec(name="address", type="TEXT", nullable=True, description="Address"),
         ColumnSpec(name="phone", type="VARCHAR", nullable=True, description="Phone"),
         ColumnSpec(name="rating", type="DECIMAL", nullable=True, description="Average rating"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Active flag"),
     ]),
    # Inventory / warehouses / suppliers
    (("warehouse", "location", "facility"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Warehouse name"),
         ColumnSpec(name="address", type="TEXT", nullable=True, description="Address"),
         ColumnSpec(name="capacity", type="INTEGER", nullable=True, description="Storage capacity"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Active flag"),
     ]),
    (("supplier", "vendor", "manufacturer"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Supplier name"),
         ColumnSpec(name="email", type="VARCHAR", nullable=True, description="Contact email"),
         ColumnSpec(name="phone", type="VARCHAR", nullable=True, description="Phone"),
         ColumnSpec(name="address", type="TEXT", nullable=True, description="Address"),
         ColumnSpec(name="is_active", type="BOOLEAN", nullable=False, default=True, description="Active flag"),
     ]),
    # Agents / professionals
    (("agent", "doctor", "driver", "instructor", "trainer"),
     [
         ColumnSpec(name="first_name", type="VARCHAR", nullable=False, description="First name"),
         ColumnSpec(name="last_name", type="VARCHAR", nullable=False, description="Last name"),
         ColumnSpec(name="email", type="VARCHAR", nullable=False, unique=True, description="Email"),
         ColumnSpec(name="phone", type="VARCHAR", nullable=True, description="Phone"),
         ColumnSpec(name="specialization", type="VARCHAR", nullable=True, description="Area of specialization"),
         ColumnSpec(name="is_available", type="BOOLEAN", nullable=False, default=True, description="Availability"),
     ]),
    # Sessions / tokens
    (("session", "token", "refresh"),
     [
         ColumnSpec(name="token", type="VARCHAR", nullable=False, unique=True, index=True, description="Token value"),
         ColumnSpec(name="expires_at", type="TIMESTAMP", nullable=False, description="Expiry time"),
         ColumnSpec(name="ip_address", type="VARCHAR", nullable=True, description="Client IP"),
         ColumnSpec(name="is_revoked", type="BOOLEAN", nullable=False, default=False, description="Revocation flag"),
     ]),
    # Roles / permissions (RBAC tables)
    (("role", "permission"),
     [
         ColumnSpec(name="name", type="VARCHAR", nullable=False, unique=True, description="Role name"),
         ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
     ]),
    # Carts / basket
    (("cart", "basket", "wishlist"),
     [
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="active", description="Cart status"),
         ColumnSpec(name="total_amount", type="DECIMAL", nullable=False, default=0, description="Cart total"),
     ]),
    # Progress / enrollment
    (("progress", "enrollment", "completion"),
     [
         ColumnSpec(name="status", type="VARCHAR", nullable=False, default="in_progress", description="Progress status"),
         ColumnSpec(name="progress_percentage", type="INTEGER", nullable=False, default=0, description="Completion %"),
         ColumnSpec(name="completed_at", type="TIMESTAMP", nullable=True, description="Completion timestamp"),
     ]),
]

# Default columns when no domain rule matches
_DEFAULT_DOMAIN_COLS: List[ColumnSpec] = [
    ColumnSpec(name="name", type="VARCHAR", nullable=False, description="Name"),
    ColumnSpec(name="description", type="TEXT", nullable=True, description="Description"),
    ColumnSpec(name="status", type="VARCHAR", nullable=False, default="active", description="Status"),
]


def _to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase entity name to snake_case table name."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower().replace(" ", "_").replace("-", "_")


def _pluralise(name: str) -> str:
    """Simple pluralisation for table names."""
    if name.endswith("y") and not name.endswith("ey"):
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


def _domain_columns(entity_name: str) -> List[ColumnSpec]:
    """Return domain-specific columns for a given entity name."""
    lower = entity_name.lower()
    for keywords, cols in _DOMAIN_RULES:
        if any(kw in lower for kw in keywords):
            # Deep-copy to avoid shared references
            return [c.model_copy() for c in cols]
    return [c.model_copy() for c in _DEFAULT_DOMAIN_COLS]


def _fk_columns(entity: EntitySpec, all_entity_names: Dict[str, str]) -> List[ColumnSpec]:
    """Generate FK columns for each relationship listed in the entity."""
    cols: List[ColumnSpec] = []
    seen: set[str] = set()
    for rel in entity.relationships:
        rel_table = all_entity_names.get(rel.lower())
        if rel_table is None:
            # Try case-insensitive lookup
            for k, v in all_entity_names.items():
                if k == rel.lower() or k.rstrip("s") == rel.lower().rstrip("s"):
                    rel_table = v
                    break
        if rel_table and rel_table not in seen:
            seen.add(rel_table)
            fk_name = f"{rel_table.rstrip('s')}_id" if rel_table.endswith("s") else f"{rel_table}_id"
            cols.append(ColumnSpec(
                name=fk_name,
                type="UUID",
                nullable=True,
                is_pk=False,
                is_fk=True,
                references=FKReference(table=rel_table, column="id", on_delete="CASCADE"),
                index=True,
                description=f"FK to {rel_table}",
            ))
    return cols


def _build_indexes(table_name: str, columns: List[ColumnSpec]) -> List[IndexSpec]:
    """Build sensible indexes from indexed columns."""
    indexes: List[IndexSpec] = []
    for col in columns:
        if col.index and not col.is_pk:
            indexes.append(IndexSpec(
                name=f"idx_{table_name}_{col.name}",
                columns=[col.name],
                unique=col.unique,
            ))
    return indexes


class DeterministicDBBuilder:
    """
    Deterministic DB schema builder. Produces DBSchema from ArchitectureSchema
    using a rule engine. Zero LLM calls.
    """

    def __init__(self) -> None:
        self._log = logger.bind(stage="deterministic_db_builder")

    def build(self, arch: ArchitectureSchema) -> DBSchema:
        # Build entity-name → table-name lookup (for FK resolution)
        entity_to_table: Dict[str, str] = {}
        for entity in arch.db_entities:
            snake = _to_snake_case(entity.name)
            plural = _pluralise(snake)
            entity_to_table[entity.name.lower()] = plural
            entity_to_table[snake] = plural

        tables: List[TableSpec] = []
        for entity in arch.db_entities:
            snake = _to_snake_case(entity.name)
            table_name = _pluralise(snake)

            # Build column list
            columns: List[ColumnSpec] = []
            columns.extend(c.model_copy() for c in _STANDARD_COLS)  # id, created_at, updated_at
            columns.extend(_fk_columns(entity, entity_to_table))
            columns.extend(_domain_columns(entity.name))

            # Deduplicate by name (FK wins over domain if same name)
            seen_names: set[str] = set()
            deduped: List[ColumnSpec] = []
            for col in columns:
                if col.name not in seen_names:
                    seen_names.add(col.name)
                    deduped.append(col)

            indexes = _build_indexes(table_name, deduped)

            tables.append(TableSpec(
                name=table_name,
                description=entity.description or f"Stores {entity.name} records",
                columns=deduped,
                indexes=indexes,
                primary_key="id",
            ))

        schema = DBSchema(tables=tables, db_type="postgresql", version="1.0.0")
        self._log.info("db_schema_built", tables=len(tables))
        return schema
