"""PEM Aevum AI service — Phase 1 FastAPI application."""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from app.api.routes.admin import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.rag import router as rag_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_audit_logger, setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.user_context import UserContextMiddleware

setup_logging()
logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PEM Aevum AI service starting")
    yield
    logger.info("PEM Aevum AI service shutting down")


app = FastAPI(
    title="PEM Aevum AI Service",
    description=(
        "AI layer for PEM Aevum. Identity is owned by the ASP.NET Core API. "
        "Pass X-API-Key, X-User-Id, and X-User-Roles on every call."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(UserContextMiddleware)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="PEM Aevum AI Service",
        version="1.0.0",
        description="Analysis API with API key + role headers from the .NET gateway",
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    excluded = {"/health", "/docs", "/redoc", "/openapi.json", "/"}
    for path, item in schema["paths"].items():
        if path not in excluded:
            for method in item.values():
                if isinstance(method, dict) and "security" not in method:
                    method["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="PEM Aevum AI Service",
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True, "filter": True},
    )


@app.get("/redoc", include_in_schema=False)
async def redoc():
    return get_redoc_html(openapi_url="/openapi.json", title="PEM Aevum AI Service")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "path": request.url.path})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    user = getattr(request.state, "user", None)
    get_audit_logger().error(
        "method=%s endpoint=%s user_id=%s roles=%s status=500 error=%s",
        request.method,
        request.url.path,
        getattr(user, "user_id", "unknown"),
        ",".join(getattr(user, "roles", ()) or ()),
        traceback.format_exc().strip().replace("\n", " | "),
    )
    logger.error("Unhandled exception at %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc), "path": request.url.path},
    )


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(evaluation_router)
app.include_router(rag_router)
app.include_router(jobs_router)
app.include_router(admin_router)


@app.get("/", tags=["General"])
async def root():
    return {
        "service": "PEM Aevum AI Service",
        "phase": 1,
        "status": "running",
        "routes": {
            "health": "/health",
            "docs": "/docs",
            "chat": "/api/chat",
            "evaluation": "/api/countries-score-analysis",
            "rag": "/api/rag",
            "jobs": "/api/jobs",
            "admin": "/api/admin",
        },
    }
