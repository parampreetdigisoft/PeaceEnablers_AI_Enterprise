"""RAG document ingest — same paths as PeaceEnablers_AI_Service /api/rag/*."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import analyst_user
from app.core.security import UserContext
from app.schemas.evaluation import AnalysisResponse
from app.services.document_service import document_service

router = APIRouter(prefix="/api/rag", tags=["Rag"], dependencies=[Depends(analyst_user)])


@router.post("/process-document/{country_doc_id}", response_model=AnalysisResponse)
async def process_document(country_doc_id: int, _: UserContext = Depends(analyst_user)):
    job = await document_service.process(country_doc_id)
    verb = "already running — attached" if job.attached else "started"
    return AnalysisResponse(
        success=True,
        message=f"Document processing {verb}.",
        jobId=job.id,
        coalesced=job.attached,
    )


@router.post("/delete-document/{country_doc_id}", response_model=AnalysisResponse)
async def delete_document(country_doc_id: int, _: UserContext = Depends(analyst_user)):
    job = await document_service.delete(country_doc_id)
    return AnalysisResponse(
        success=True,
        message="Document deletion completed.",
        jobId=job.id,
        coalesced=job.attached,
    )
