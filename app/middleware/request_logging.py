"""Log every API call to logs/requests.log (append-only). Failures include stack traces."""

from __future__ import annotations

import time
import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_audit_logger
from app.core.security import UserContext


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        user: UserContext | None = getattr(request.state, "user", None)
        user_id = user.user_id if user else "unknown"
        roles = ",".join(user.roles) if user else ""
        logger = get_audit_logger()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "method=%s endpoint=%s user_id=%s roles=%s status=%s duration_ms=%s error=%s",
                request.method,
                request.url.path,
                user_id,
                roles,
                500,
                duration_ms,
                traceback.format_exc().strip().replace("\n", " | "),
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        level = logger.error if response.status_code >= 500 else logger.info
        level(
            "method=%s endpoint=%s user_id=%s roles=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            user_id,
            roles,
            response.status_code,
            duration_ms,
        )
        return response
