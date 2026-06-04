"""
All 20 hardcoded evaluation test cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EvalTestCase:
    id: str
    name: str
    category: str  # "normal" | "edge"
    prompt: str
    expected_min_tables: int
    expected_min_endpoints: int
    should_request_clarification: bool
    description: str = ""


EVAL_TEST_CASES: List[EvalTestCase] = [
    # ── Normal Cases (1-10) ────────────────────────────────────────────────
    EvalTestCase(
        id="TC01",
        name="CRM with Role-Based Access",
        category="normal",
        prompt=(
            "Build a CRM with login, contacts, deals, role-based access for "
            "sales reps and managers. Managers see analytics dashboard."
        ),
        expected_min_tables=4,
        expected_min_endpoints=10,
        should_request_clarification=False,
        description="Standard CRM with multiple roles and analytics",
    ),
    EvalTestCase(
        id="TC02",
        name="E-Commerce Store",
        category="normal",
        prompt=(
            "E-commerce store with products, categories, cart, checkout, "
            "Stripe payments, order history, and admin panel."
        ),
        expected_min_tables=5,
        expected_min_endpoints=15,
        should_request_clarification=False,
        description="Full e-commerce with payments and admin",
    ),
    EvalTestCase(
        id="TC03",
        name="Project Management Tool",
        category="normal",
        prompt=(
            "Project management tool with boards, cards, teams, due dates, "
            "file attachments, and activity feed."
        ),
        expected_min_tables=5,
        expected_min_endpoints=12,
        should_request_clarification=False,
        description="Kanban-style project management",
    ),
    EvalTestCase(
        id="TC04",
        name="Healthcare Appointment Booking",
        category="normal",
        prompt=(
            "Healthcare appointment booking with patients, doctors, "
            "available slots, notifications, and medical history."
        ),
        expected_min_tables=5,
        expected_min_endpoints=12,
        should_request_clarification=False,
        description="Medical appointment system",
    ),
    EvalTestCase(
        id="TC05",
        name="SaaS Analytics Platform",
        category="normal",
        prompt=(
            "SaaS analytics platform with multi-tenant, usage-based billing, "
            "API key management, and team member roles."
        ),
        expected_min_tables=5,
        expected_min_endpoints=12,
        should_request_clarification=False,
        description="Multi-tenant SaaS with billing",
    ),
    EvalTestCase(
        id="TC06",
        name="Food Delivery App",
        category="normal",
        prompt=(
            "Food delivery app with restaurants, menus, orders, delivery "
            "riders, real-time tracking, and ratings."
        ),
        expected_min_tables=5,
        expected_min_endpoints=12,
        should_request_clarification=False,
        description="Food delivery marketplace",
    ),
    EvalTestCase(
        id="TC07",
        name="Learning Management System",
        category="normal",
        prompt=(
            "Learning management system with courses, lessons, quizzes, "
            "student progress tracking, and certificates."
        ),
        expected_min_tables=5,
        expected_min_endpoints=10,
        should_request_clarification=False,
        description="LMS with courses and certificates",
    ),
    EvalTestCase(
        id="TC08",
        name="HR Management System",
        category="normal",
        prompt=(
            "HR management with employees, departments, leave requests, "
            "payroll records, and performance reviews."
        ),
        expected_min_tables=5,
        expected_min_endpoints=12,
        should_request_clarification=False,
        description="HR platform with payroll and reviews",
    ),
    EvalTestCase(
        id="TC09",
        name="Real Estate Listing Platform",
        category="normal",
        prompt=(
            "Real estate listing platform with properties, agents, "
            "inquiries, saved searches, and mortgage calculator."
        ),
        expected_min_tables=4,
        expected_min_endpoints=10,
        should_request_clarification=False,
        description="Property listings with agent management",
    ),
    EvalTestCase(
        id="TC10",
        name="Inventory Management",
        category="normal",
        prompt=(
            "Inventory management with warehouses, products, stock level "
            "alerts, purchase orders, and suppliers."
        ),
        expected_min_tables=5,
        expected_min_endpoints=10,
        should_request_clarification=False,
        description="Warehouse and inventory system",
    ),

    # ── Edge Cases (11-20) ─────────────────────────────────────────────────
    EvalTestCase(
        id="TC11",
        name="Too Vague — Build an app",
        category="edge",
        prompt="Build an app",
        expected_min_tables=0,
        expected_min_endpoints=0,
        should_request_clarification=True,
        description="Extremely vague prompt should trigger clarification",
    ),
    EvalTestCase(
        id="TC12",
        name="Conflicting Logic — Free users get premium",
        category="edge",
        prompt=(
            "CRM where free users get all premium features but premium "
            "users get extra free features"
        ),
        expected_min_tables=2,
        expected_min_endpoints=4,
        should_request_clarification=False,
        description="Contradictory monetization logic",
    ),
    EvalTestCase(
        id="TC13",
        name="Impossible Specs — Zero latency & 100% uptime",
        category="edge",
        prompt=(
            "Social platform with infinite scalability, zero latency, "
            "100% uptime, and free hosting"
        ),
        expected_min_tables=3,
        expected_min_endpoints=6,
        should_request_clarification=False,
        description="Technically impossible specifications",
    ),
    EvalTestCase(
        id="TC14",
        name="Single Word — app",
        category="edge",
        prompt="app",
        expected_min_tables=0,
        expected_min_endpoints=0,
        should_request_clarification=True,
        description="Single word prompt",
    ),
    EvalTestCase(
        id="TC15",
        name="Scope Creep — Netflix+Uber+Airbnb+Blockchain",
        category="edge",
        prompt=(
            "Build something like Netflix but better and also like Uber "
            "and also like Airbnb with blockchain"
        ),
        expected_min_tables=5,
        expected_min_endpoints=10,
        should_request_clarification=False,
        description="Extreme scope creep with multiple contradictory products",
    ),
    EvalTestCase(
        id="TC16",
        name="Underspecified — todo list",
        category="edge",
        prompt="todo list",
        expected_min_tables=1,
        expected_min_endpoints=4,
        should_request_clarification=True,
        description="Minimally specified app",
    ),
    EvalTestCase(
        id="TC17",
        name="Logical Conflict — Admins can't see user data",
        category="edge",
        prompt=(
            "System where admins manage users but admins cannot see user "
            "data but users can see all admin data"
        ),
        expected_min_tables=2,
        expected_min_endpoints=4,
        should_request_clarification=False,
        description="Logically conflicting permission requirements",
    ),
    EvalTestCase(
        id="TC18",
        name="Contradiction — E-commerce with no database",
        category="edge",
        prompt=(
            "E-commerce with 500 product fields, real-time inventory sync "
            "across 200 warehouses, AI recommendations, and no database"
        ),
        expected_min_tables=3,
        expected_min_endpoints=6,
        should_request_clarification=False,
        description="Self-contradictory technical requirements",
    ),
    EvalTestCase(
        id="TC19",
        name="Non-English — Hindi CRM",
        category="edge",
        prompt="एक CRM बनाओ जिसमें login और contacts हों",
        expected_min_tables=2,
        expected_min_endpoints=4,
        should_request_clarification=False,
        description="Non-English (Hindi) prompt",
    ),
    EvalTestCase(
        id="TC20",
        name="Overspecified — 40+ features, 8 roles",
        category="edge",
        prompt=(
            "Build an enterprise SaaS platform with the following requirements: "
            "1) Multi-tenant architecture with subdomain routing, 2) SSO with SAML 2.0 and OAuth2, "
            "3) Role-based access with 8 roles: super_admin, org_admin, manager, team_lead, "
            "senior_dev, junior_dev, client, and guest, 4) Three payment tiers: starter ($29/mo, 5 users), "
            "professional ($99/mo, 25 users, API access), enterprise (custom, unlimited), "
            "5) Stripe + PayPal + wire transfer payment methods, 6) Real-time collaboration with WebSockets, "
            "7) Advanced analytics with custom dashboards and 30+ chart types, "
            "8) Automated CI/CD pipeline integration with GitHub, GitLab, Bitbucket, "
            "9) Slack, Teams, and email notifications, 10) File storage with S3, GCS, Azure Blob, "
            "11) Full audit trail and compliance logging (SOC2, GDPR, HIPAA), "
            "12) AI-powered code review and suggestions, 13) Custom workflow builder with drag-and-drop, "
            "14) API rate limiting and quota management, 15) White-labeling and custom branding, "
            "16) Mobile apps for iOS and Android, 17) Offline mode with sync, "
            "18) Multi-language support (20 languages), 19) Dark/light/custom themes, "
            "20) Video conferencing integration, 21) Time tracking and billing, "
            "22) Resource planning and capacity management, 23) Budget tracking and cost forecasting, "
            "24) Customer support ticketing system, 25) Knowledge base with search."
        ),
        expected_min_tables=10,
        expected_min_endpoints=20,
        should_request_clarification=False,
        description="500+ word spec with 40+ features and 8 roles",
    ),
]


def get_test_case(test_id: str) -> EvalTestCase | None:
    return next((tc for tc in EVAL_TEST_CASES if tc.id == test_id), None)
