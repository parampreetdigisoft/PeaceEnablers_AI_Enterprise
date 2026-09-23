"""Attach X-User-Id / X-User-Roles from the .NET gateway onto request.state and a ContextVar."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    UserContext,
    parse_roles,
    reset_user_context,
    set_user_context,
    validate_api_key,
)


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

            user_id = (request.headers.get(user_id_header) or "").strip()
            roles_raw = (request.headers.get(roles_header) or "").strip()

            # Required for all protected routes (chat + jobs). Background callers
            # must send system identity from .NET AiGateway.
            if not user_id:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "message": f"Missing required header {user_id_header}.",
                    },
                )
            if not roles_raw:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "message": f"Missing required header {roles_header}.",
                    },
                )

            ctx = UserContext(
                user_id=user_id,
                roles=parse_roles(roles_raw),
                email=(request.headers.get(email_header) or None),
                api_key_valid=True,
            )
        else:
            ctx = UserContext(
                user_id="anonymous",
                roles=(),
                email=None,
                api_key_valid=False,
            )

        request.state.user = ctx
        token = set_user_context(ctx)
        try:
            return await call_next(request)
        finally:
            reset_user_context(token)
