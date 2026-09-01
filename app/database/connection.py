"""SQL Server + vector + graph connection factories. Repositories never open connections themselves."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Generator

import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from app.core.config import settings

logger = logging.getLogger(__name__)

pyodbc.pooling = True
executor = ThreadPoolExecutor(max_workers=20)


def build_odbc_string() -> str:
    base = (
        f"DRIVER={{{settings.db_odbc_driver}}};"
        f"SERVER={settings.db_server};"
        f"DATABASE={settings.db_name};"
    )
    if settings.db_use_windows_auth:
        return base + "Trusted_Connection=yes;"
    return base + f"UID={settings.db_username};PWD={settings.db_password};"


def build_sqlalchemy_url() -> URL:
    query = {"driver": settings.db_odbc_driver}
    if settings.db_use_windows_auth:
        query["Trusted_Connection"] = "yes"
        return URL.create(
            "mssql+pyodbc",
            host=settings.db_server,
            database=settings.db_name,
            query=query,
        )
    return URL.create(
        "mssql+pyodbc",
        username=settings.db_username,
        password=settings.db_password,
        host=settings.db_server,
        database=settings.db_name,
        query=query,
    )


@contextmanager
def get_connection(timeout: int = 30) -> Generator[pyodbc.Connection, None, None]:
    conn = None
    try:
        conn = pyodbc.connect(build_odbc_string(), timeout=timeout)
        yield conn
    finally:
        if conn:
            conn.close()


class SQLServerEngine:
    def __init__(self) -> None:
        self._sa: Engine | None = None

    @property
    def sa_engine(self) -> Engine:
        if self._sa is None:
            self._sa = create_engine(
                build_sqlalchemy_url(),
                fast_executemany=True,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=10,
            )
        return self._sa

    def test_connection(self) -> bool:
        try:
            with get_connection() as conn:
                conn.cursor().execute("SELECT 1")
            return True
        except Exception as exc:
            logger.warning("SQL Server connection failed: %s", exc)
            return False

    def fetch_dicts(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params) if params else cursor.execute(query)
            if cursor.description is None:
                return []
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_write(
        self,
        query: str,
        params: tuple | list = (),
        *,
        fetch_one: bool = False,
        executemany: bool = False,
    ) -> Any:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                if executemany:
                    cursor.fast_executemany = True
                    cursor.executemany(query, params)
                    result = None
                else:
                    cursor.execute(query, params)
                    result = cursor.fetchone() if fetch_one else None
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def execute_sp(self, sp_query: str, params: tuple) -> None:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.fast_executemany = True
                cursor.execute(sp_query, params)
                conn.commit()
            except Exception:
                conn.rollback()
                raise


sql_engine = SQLServerEngine()
