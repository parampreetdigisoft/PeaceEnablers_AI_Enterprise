"""CountryDocuments + chunk/TOC persistence for RAG ingest."""

from __future__ import annotations

from typing import Any

from app.database.session import db_session


class DocumentRepository:
    async def get_document(self, country_doc_id: int) -> dict[str, Any] | None:
        rows = await db_session.fetch_dicts(
            """
            SELECT CountryDocumentID, CountryID, FilePath, FileType, PillarID, DocumentLevel
            FROM CountryDocuments
            WHERE IsDeleted = 0 AND CountryDocumentID = ?
            """,
            (country_doc_id,),
        )
        return rows[0] if rows else None

    async def save_toc_section(
        self,
        section: dict,
        country_doc_id: int,
        country_id: int | None,
        pillar_id: int | None,
    ) -> int | None:
        query = """
            MERGE DocumentTOC AS target
            USING (
                SELECT ? AS CountryDocumentID, ? AS CountryID, ? AS PillarID,
                       ? AS SectionPath, ? AS SectionTitle, ? AS SectionLevel,
                       ? AS PageStart, ? AS PageEnd
            ) AS source
            ON target.CountryDocumentID = source.CountryDocumentID
            AND target.CountryID = source.CountryID
            AND (
                (target.PillarID IS NULL AND source.PillarID IS NULL)
                OR target.PillarID = source.PillarID
            )
            WHEN MATCHED THEN UPDATE SET
                SectionTitle = source.SectionTitle,
                SectionLevel = source.SectionLevel,
                PageStart = source.PageStart,
                PageEnd = source.PageEnd,
                SectionPath = source.SectionPath
            WHEN NOT MATCHED THEN INSERT
                (CountryDocumentID, CountryID, PillarID, SectionPath, SectionTitle,
                 SectionLevel, PageStart, PageEnd)
                VALUES (source.CountryDocumentID, source.CountryID, source.PillarID,
                        source.SectionPath, source.SectionTitle, source.SectionLevel,
                        source.PageStart, source.PageEnd)
            OUTPUT inserted.TOCID;
        """
        params = (
            country_doc_id,
            country_id,
            pillar_id,
            section.get("path"),
            section.get("title"),
            section.get("level"),
            section.get("page_start"),
            section.get("page_end"),
        )
        result = await db_session.execute_write(query, params, fetch_one=True)
        return result[0] if result else None

    async def save_chunks(self, chunks: list[dict], country_doc_id: int, country_id: int | None, pillar_id: int | None) -> None:
        if not chunks:
            return
        query = """
            INSERT INTO DocumentChunks
                (ChunkID, CountryDocumentID, TOCID, CountryID, PillarID, ChunkIndex, ChunkText)
            VALUES (?,?,?,?,?,?,?)
        """
        params = [
            (
                c.get("chunk_id"),
                country_doc_id,
                c.get("toc_id"),
                country_id,
                pillar_id,
                c.get("chunk_index"),
                c.get("chunk_text"),
            )
            for c in chunks
        ]
        await db_session.execute_write(query, params, executemany=True)

    async def delete_document_rows(self, country_doc_id: int) -> None:
        await db_session.execute_write(
            "DELETE FROM DocumentChunks WHERE CountryDocumentID = ?; DELETE FROM DocumentTOC WHERE CountryDocumentID = ?;",
            (country_doc_id, country_doc_id),
        )


document_repository = DocumentRepository()
