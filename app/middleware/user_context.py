"""Attach X-User-Id / X-User-Roles from the .NET gateway onto request.state and a ContextVar."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.security import UserContext, parse_roles, set_user_context, reset_user_context, validate_api_key
from app.core.exceptions import UnauthorizedError
from fastapi.responses import JSONResponse


PUBLIC_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rbac = settings.rbac
        headers_cfg = rbac.get("headers") or {}
        user_id_header = headers_cfg.get("user_id", "X-User-Id")
        roles_header = headers_cfg.get("roles", "X-User-Roles")
        email_header = headers_cfg.get("email", "X-User-Email")
        api_key_header = headers_cfg.get("api_key", "X-API-Key")

        path = request.url.path
        is_public = any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES) or path == "/"

        if not is_public:
            try:
                validate_api_key(request.headers.get(api_key_header))
            except UnauthorizedError as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"error": "Unauthorized", "message": exc.message},
                )

        ctx = UserContext(
            user_id=request.headers.get(user_id_header) or "system",
            roles=parse_roles(request.headers.get(roles_header)),
            email=request.headers.get(email_header),
            api_key_valid=not is_public,
        )
        request.state.user = ctx
        token = set_user_context(ctx)
        try:
            return await call_next(request)
        finally:
            reset_user_context(token)
