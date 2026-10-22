from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.project import Project, SourceDocument
from backend.app.schemas.project import SourceDocumentResponse
from backend.app.services.source_ingestion import source_ingestion_service

router = APIRouter(tags=["Source Documents"])

@router.post("/projects/{project_id}/documents", response_model=SourceDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # Verify project exists
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if file:
        content = await file.read()
        fname = file.filename or "manuscript.txt"
        mime = file.content_type or "text/plain"
    elif raw_text:
        content = raw_text.encode("utf-8")
        fname = filename or "manuscript_direct_entry.txt"
        mime = "text/plain"
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file upload or raw_text form field.")

    # Size limitation check (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    doc = await source_ingestion_service.ingest_document(
        db=db,
        project_id=project_id,
        filename=fname,
        raw_bytes=content,
        mime_type=mime
    )

    # Re-fetch with sections loaded
    doc_stmt = select(SourceDocument).options(selectinload(SourceDocument.sections)).where(SourceDocument.id == doc.id)
    doc_res = await db.execute(doc_stmt)
    return doc_res.scalar_one()

@router.get("/projects/{project_id}/documents", response_model=List[SourceDocumentResponse])
async def list_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(SourceDocument)
        .options(selectinload(SourceDocument.sections))
        .where(SourceDocument.project_id == project_id)
        .order_by(SourceDocument.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
