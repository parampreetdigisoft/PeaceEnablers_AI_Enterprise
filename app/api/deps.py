"""FastAPI dependencies: role gates."""

from __future__ import annotations

from app.core.security import UserContext, require_roles


def analyst_user() -> UserContext:
    return require_roles("Analyst", "Admin")


def admin_user() -> UserContext:
    return require_roles("Admin")
