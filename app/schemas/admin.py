from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    sql_server: dict[str, Any]
    vector_db: dict[str, Any]
    graph_db: dict[str, Any]
    llm: dict[str, Any]


class CancelResponse(BaseModel):
    success: bool
    message: str
    job: dict[str, Any]
