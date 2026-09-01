"""Async wrappers around the SQL Server engine so services stay async."""

from __future__ import annotations

import asyncio
from typing import Any

from app.database.connection import executor, sql_engine


class DatabaseSession:
    async def fetch_dicts(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, sql_engine.fetch_dicts, query, params)

    async def execute_write(
        self,
        query: str,
        params: tuple | list = (),
        *,
        fetch_one: bool = False,
        executemany: bool = False,
    ) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            executor,
            lambda: sql_engine.execute_write(
                query, params, fetch_one=fetch_one, executemany=executemany
            ),
        )

    async def execute_sp(self, sp_query: str, params: tuple) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, sql_engine.execute_sp, sp_query, params)

    async def test_connection(self) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, sql_engine.test_connection)


db_session = DatabaseSession()
