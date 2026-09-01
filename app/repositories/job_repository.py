"""Optional SQL snapshot of jobs. Live coalescing always uses the in-memory registry."""

from __future__ import annotations

import json
import logging

from app.database.session import db_session
from app.models.job import Job

logger = logging.getLogger(__name__)

_CREATE = """
IF OBJECT_ID(N'dbo.AiJobs', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.AiJobs (
        JobId            NVARCHAR(64)  NOT NULL PRIMARY KEY,
        CoalescingKey    NVARCHAR(512) NOT NULL,
        ResourceType     NVARCHAR(64)  NOT NULL,
        Status           NVARCHAR(32)  NOT NULL,
        CountryId        INT           NULL,
        PillarId         INT           NULL,
        QuestionId       INT           NULL,
        DocumentId       INT           NULL,
        [Year]           INT           NULL,
        AttachedUserIds  NVARCHAR(MAX) NULL,
        CreatedBy        NVARCHAR(128) NULL,
        Provider         NVARCHAR(64)  NULL,
        Model            NVARCHAR(128) NULL,
        Purpose          NVARCHAR(64)  NULL,
        CreatedAt        DATETIME2     NOT NULL,
        StartedAt        DATETIME2     NULL,
        CompletedAt      DATETIME2     NULL,
        Error            NVARCHAR(MAX) NULL
    );
    CREATE INDEX IX_AiJobs_CoalescingKey ON dbo.AiJobs (CoalescingKey);
    CREATE INDEX IX_AiJobs_Status ON dbo.AiJobs (Status);
END
"""

_UPDATE = """
UPDATE dbo.AiJobs SET
    Status = ?, AttachedUserIds = ?, Provider = ?, Model = ?,
    StartedAt = ?, CompletedAt = ?, Error = ?
WHERE JobId = ?
"""


class JobRepository:
    _ready = False

    async def ensure_table(self) -> None:
        if self._ready:
            return
        try:
            await db_session.execute_write(_CREATE)
            self._ready = True
        except Exception as exc:
            logger.warning("AiJobs table not available (memory-only jobs): %s", exc)

    async def save(self, job: Job) -> None:
        await self.ensure_table()
        if not self._ready:
            return
        users = json.dumps(job.attached_user_ids)
        try:
            await db_session.execute_write(
                _UPDATE,
                (
                    job.status.value,
                    users,
                    job.provider,
                    job.model,
                    job.started_at,
                    job.completed_at,
                    job.error,
                    job.id,
                ),
            )
            # INSERT when the row is new. A failed UPDATE still succeeds with 0 rows.
            await db_session.execute_write(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.AiJobs WHERE JobId = ?)
                BEGIN
                    INSERT INTO dbo.AiJobs (
                        JobId, CoalescingKey, ResourceType, Status, CountryId, PillarId, QuestionId,
                        DocumentId, [Year], AttachedUserIds, CreatedBy, Provider, Model, Purpose,
                        CreatedAt, StartedAt, CompletedAt, Error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                END
                """,
                (
                    job.id,
                    job.id,
                    job.coalescing_key,
                    job.resource_type,
                    job.status.value,
                    job.country_id,
                    job.pillar_id,
                    job.question_id,
                    job.document_id,
                    job.year,
                    users,
                    job.created_by,
                    job.provider,
                    job.model,
                    job.purpose,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    job.error,
                ),
            )
        except Exception as exc:
            logger.warning("Failed to persist job %s: %s", job.id, exc)


job_repository = JobRepository()
