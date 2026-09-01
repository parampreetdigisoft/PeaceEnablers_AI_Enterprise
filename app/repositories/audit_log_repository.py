"""File-backed audit helper. Request middleware already writes the line; this is for job-level notes."""

from __future__ import annotations

from app.core.logging import get_audit_logger
from app.models.audit_log import AuditLog


class AuditLogRepository:
    def write(self, record: AuditLog) -> None:
        get_audit_logger().info(
            "method=%s endpoint=%s user_id=%s roles=%s status=%s duration_ms=%s job_id=%s error=%s",
            record.method,
            record.endpoint,
            record.user_id,
            record.roles,
            record.status_code,
            record.duration_ms,
            record.job_id,
            (record.error or "").replace("\n", " | "),
        )


audit_log_repository = AuditLogRepository()
