"""Domain exceptions mapped to HTTP in main.py."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, status_code=404)


class JobCancelledError(AppError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job {job_id} was cancelled", status_code=409)
        self.job_id = job_id


class ProviderUnavailableError(AppError):
    def __init__(self, message: str = "No LLM provider available") -> None:
        super().__init__(message, status_code=503)
