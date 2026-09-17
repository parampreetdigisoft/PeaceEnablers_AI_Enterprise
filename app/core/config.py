"""
Loads .env + YAML policy files.

core/config.py is Python. app/config/*.yaml is what operators edit to change
coalescing granularity or LLM routing without touching code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "app"
CONFIG_DIR = APP_DIR / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"

    application_auth_api_key: str = Field(default="", alias="APPLICATION_AUTH_API_KEY")
    # Accept the legacy env name from PeaceEnablers_AI_Service
    application_auth_api_key_legacy: str = Field(default="", alias="Application_Auth_API_KEY")

    db_server: str = "localhost\\SQLEXPRESS"
    db_name: str = "PeaceEnablerDB"
    db_use_windows_auth: bool = True
    db_username: str = ""
    db_password: str = ""
    db_odbc_driver: str = "ODBC Driver 17 for SQL Server"

    vector_db: str = "chroma"
    vector_persist_path: str = "./chroma_store"
    vector_collection_prefix: str = "pem"
    vector_embedding_model: str = "all-MiniLM-L6-v2"
    vector_embedding_normalize: bool = False

    # Pinecone — unused while VECTOR_DB=chroma. Fill these before go-live.
    pinecone_api_key: str = ""
    pinecone_index_name: str = "pem-vectors"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3"

    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5

    @property
    def api_key(self) -> str:
        return self.application_auth_api_key or self.application_auth_api_key_legacy

    @property
    def job_coalescing(self) -> dict[str, Any]:
        return _load_yaml("job_coalescing.yaml")

    @property
    def llm_routing(self) -> dict[str, Any]:
        return _load_yaml("llm_routing.yaml")

    @property
    def logging_yaml(self) -> dict[str, Any]:
        return _load_yaml("logging.yaml")

    @property
    def rbac(self) -> dict[str, Any]:
        return _load_yaml("rbac.yaml")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
