"""File + console logging. Request lines are append-only; do not rewrite history."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import ROOT_DIR, settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    cfg = settings.logging_yaml
    file_cfg = cfg.get("file") or {}
    console_cfg = cfg.get("console") or {}

    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    if console_cfg.get("enabled", True):
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, str(console_cfg.get("level", "INFO")).upper(), logging.INFO))
        console.setFormatter(fmt)
        root.addHandler(console)

    request_path = ROOT_DIR / file_cfg.get("path", "logs/requests.log")
    error_path = ROOT_DIR / file_cfg.get("error_path", "logs/errors.log")
    max_bytes = int(file_cfg.get("max_bytes", 10_485_760))
    backup_count = int(file_cfg.get("backup_count", 14))
    encoding = file_cfg.get("encoding", "utf-8")

    request_handler = RotatingFileHandler(
        request_path, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding
    )
    request_handler.setLevel(logging.INFO)
    request_handler.setFormatter(fmt)
    logging.getLogger("app.audit").addHandler(request_handler)
    logging.getLogger("app.audit").setLevel(logging.INFO)
    logging.getLogger("app.audit").propagate = False

    error_handler = RotatingFileHandler(
        error_path, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    root.addHandler(error_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("pyodbc").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)

    _configured = True


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("app.audit")
