"""
Consume identity from the .NET API. This service never issues tokens.

Headers (configurable in app/config/rbac.yaml):
  X-API-Key      service-to-service shared secret
  X-User-Id      calling user (logged on every request and every job)
  X-User-Roles   comma-separated: Admin, Analyst, Viewer
  X-User-Email   optional
"""

from __future__ import annotations

from dataclasses import dataclass, field
from contextvars import ContextVar
from typing import Iterable

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError

user_context_var: ContextVar["UserContext | None"] = ContextVar("user_context", default=None)


@dataclass(frozen=True)
class UserContext:
    user_id: str
    roles: tuple[str, ...] = ()
    email: str | None = None
    api_key_valid: bool = False

    def has_role(self, *needed: str) -> bool:
        have = {r.lower() for r in self.roles}
        return any(n.lower() in have for n in needed)


def current_user() -> UserContext:
    ctx = user_context_var.get()
    if ctx is None:
        return UserContext(user_id="anonymous", roles=())
    return ctx


def parse_roles(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        default = (settings.rbac.get("legacy_default_role") or "").strip()
        return (default,) if default else ()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts)


def validate_api_key(provided: str | None) -> None:
    expected = settings.api_key
    if not expected:
        raise UnauthorizedError("API key is not configured on the AI service")
    if not provided:
        raise UnauthorizedError("API key is missing. Provide X-API-Key.")
    if provided != expected:
        raise UnauthorizedError("Invalid API key.")


def require_roles(*roles: str) -> UserContext:
    user = current_user()
    # if not user.has_role(*roles):
    #     raise ForbiddenError(f"Requires one of roles: {', '.join(roles)}")
    return user


def set_user_context(ctx: UserContext):
    return user_context_var.set(ctx)


def reset_user_context(token) -> None:
    user_context_var.reset(token)
