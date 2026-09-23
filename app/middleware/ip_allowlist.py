"""
Allow only configured caller IPs (ASP.NET API hosts) to reach this service.

Configure via ALLOWED_CALLER_IPS in .env, e.g.:
  ALLOWED_CALLER_IPS=127.0.0.1,::1,10.0.0.15,192.168.1.50

When the list is empty, all callers are allowed (local/dev). Set at least one
production IP so only the .NET Web API server(s) can call AI endpoints.
"""

from __future__ import annotations

import ipaddress
import logging

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Health/docs remain reachable for ops even when IP allowlist is on.
# Set ALLOWED_CALLER_IPS_PROTECT_PUBLIC=true to lock those down too.
PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def _parse_allowed_ips(raw: str) -> set[str]:
    allowed: set[str] = set()
    for part in (raw or "").split(","):
        value = part.strip()
        if not value:
            continue
        try:
            # Normalize IPv4/IPv6 (e.g. ::ffff:127.0.0.1 → comparable forms)
            addr = ipaddress.ip_address(value)
            allowed.add(str(addr))
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
                allowed.add(str(addr.ipv4_mapped))
            if isinstance(addr, ipaddress.IPv4Address):
                allowed.add(str(ipaddress.IPv6Address(f"::ffff:{addr}")))
        except ValueError:
            logger.warning("Ignoring invalid ALLOWED_CALLER_IPS entry: %s", value)
    return allowed


def _client_ip(request: Request) -> str | None:
    """Prefer direct socket peer (ASP.NET → Python). Optional X-Forwarded-For for reverse proxies."""
    if settings.allowed_caller_trust_forwarded_for:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first

    if request.client and request.client.host:
        return request.client.host
    return None


def _normalize_ip(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        addr = ipaddress.ip_address(raw.strip())
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        return str(addr)
    except ValueError:
        return raw.strip()


class IpAllowlistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        allowed = _parse_allowed_ips(settings.allowed_caller_ips)
        if not allowed:
            # Empty list = open (dev). Production must set ALLOWED_CALLER_IPS.
            return await call_next(request)

        path = request.url.path
        is_public = any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES) or path == "/"
        if is_public and not settings.allowed_caller_protect_public:
            return await call_next(request)

        client = _normalize_ip(_client_ip(request))
        if client and client in allowed:
            return await call_next(request)

        # Also accept if normalized mapped form is in the set
        if client:
            for entry in allowed:
                try:
                    if ipaddress.ip_address(client) == ipaddress.ip_address(entry):
                        return await call_next(request)
                except ValueError:
                    continue

        logger.warning(
            "Blocked AI request from IP=%s path=%s (allowlist has %s entries)",
            client or "unknown",
            path,
            len(allowed),
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": "Caller IP is not allowed to access the AI service.",
                "path": path,
            },
        )
