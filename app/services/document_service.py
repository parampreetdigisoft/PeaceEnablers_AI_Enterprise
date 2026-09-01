"""Document ingest/delete. Coalesced by country_doc_id so two callers don't double-chunk."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings
from app.database.vector import get_vector_store
from app.jobs.key_builder import build_key
from app.jobs.manager import job_manager
from app.models.job import Job
from app.repositories.document_repository import document_repository


def _read_text(path: str, file_type: str | None) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    suffix = (file_type or p.suffix).lower()
    if suffix in {".txt", "txt"}:
        return p.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".pdf", "pdf"}:
        import pymupdf

        doc = pymupdf.open(p)
        return "\n".join(page.get_text() for page in doc)
    if suffix in {".docx", "docx"}:
        import docx

        d = docx.Document(p)
        return "\n".join(par.text for par in d.paragraphs)
    return p.read_text(encoding="utf-8", errors="ignore")


def _chunk(text: str) -> list[str]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return [c.strip() for c in chunks if c.strip()]


class DocumentService:
    async def process(self, country_doc_id: int) -> Job:
        key = build_key("document_ingest", document_id=country_doc_id)

        async def _run(job: Job) -> dict:
            doc = await document_repository.get_document(country_doc_id)
            if not doc:
                raise  (f"CountryDocument {country_doc_id} not found")
            
            text = _read_text(str(doc["FilePath"]), str(doc.get("FileType") or ""))
            pieces = _chunk(text)
            country_id = doc.get("CountryID")
            pillar_id = doc.get("PillarID")
            toc_id = await document_repository.save_toc_section(
                {
                    "path": "/",
                    "title": Path(str(doc["FilePath"])).name,
                    "level": 1,
                    "page_start": 1,
                    "page_end": 1,
                },
                country_doc_id,
                country_id,
                pillar_id,
            )
            records = [
                {
                    "chunk_id": str(uuid.uuid4()),
                    "toc_id": toc_id,
                    "chunk_index": idx,
                    "chunk_text": piece,
                }
                for idx, piece in enumerate(pieces)
            ]
            await document_repository.save_chunks(records, country_doc_id, country_id, pillar_id)
            store = get_vector_store()
            global_level = str(doc.get("DocumentLevel") or "").lower() == "global"
            name = store.collection_name(country_id=country_id, global_docs=global_level)
            store.upsert(
                name,
                ids=[r["chunk_id"] for r in records],
                documents=[r["chunk_text"] for r in records],
                metadatas=[
                    {
                        k: v
                        for k, v in {
                            "country_doc_id": country_doc_id,
                            "country_id": country_id or 0,
                            "pillar_id": pillar_id or 0,
                        }.items()
                    }
                    for _ in records
                ],
            )
            return {"chunks": len(records), "country_doc_id": country_doc_id}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="document_ingest",
            executor=_run,
            document_id=country_doc_id,
            purpose="document",
        )

    async def delete(self, country_doc_id: int) -> Job:
        key = build_key("document_delete", document_id=country_doc_id)

        async def _run(job: Job) -> dict:
            doc = await document_repository.get_document(country_doc_id)
            await document_repository.delete_document_rows(country_doc_id)
            if doc:
                store = get_vector_store()
                global_level = str(doc.get("DocumentLevel") or "").lower() == "global"
                name = store.collection_name(country_id=doc.get("CountryID"), global_docs=global_level)
                store.delete_where(name, {"country_doc_id": country_doc_id})
            return {"deleted": country_doc_id}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="document_delete",
            executor=_run,
            document_id=country_doc_id,
            purpose="document",
            wait=True,
        )


document_service = DocumentService()
