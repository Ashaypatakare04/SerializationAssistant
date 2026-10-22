from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.style import ReferenceAsset, CharacterReference
from backend.app.schemas.style import ReferenceAssetResponse, CharacterReferenceCreate, CharacterReferenceResponse
from backend.app.services.storage import storage_service

router = APIRouter(tags=["References"])

@router.post("/projects/{project_id}/references", response_model=ReferenceAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference(
    project_id: str,
    file: UploadFile = File(...),
    role: str = Form("visual_style"),  # visual_style, character_identity, layout_composition, environment
    label: str = Form(""),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found.")

    raw_bytes = await file.read()
    if len(raw_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Reference image too large. Max size is 20MB.")

    storage_key, checksum, file_size = storage_service.save_bytes("references", file.filename or "ref.png", raw_bytes)
    
    # Inspect image dimensions
    try:
        width, height, fmt = storage_service.inspect_image(storage_key)
    except Exception:
        width, height, fmt = 800, 1000, "png"

    ref = ReferenceAsset(
        project_id=project_id,
        filename=file.filename or "ref.png",
        storage_key=storage_key,
        role=role,
        label=label or file.filename or "Reference Image",
        description=description,
        width=width,
        height=height,
        file_size_bytes=file_size,
        mime_type=file.content_type or f"image/{fmt}",
        is_active=True
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    return ref

@router.get("/projects/{project_id}/references", response_model=List[ReferenceAssetResponse])
async def list_references(
    project_id: str,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ReferenceAsset).where(
        ReferenceAsset.project_id == project_id,
        ReferenceAsset.is_active == True
    )
    if role:
        stmt = stmt.where(ReferenceAsset.role == role)
    stmt = stmt.order_by(ReferenceAsset.created_at.desc())

    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/projects/{project_id}/character-references", response_model=CharacterReferenceResponse)
async def link_character_reference(
    project_id: str,
    data: CharacterReferenceCreate,
    db: AsyncSession = Depends(get_db)
):
    char_ref = CharacterReference(
        character_id=data.character_id,
        reference_asset_id=data.reference_asset_id,
        character_version_id=data.character_version_id,
        relevance_notes=data.relevance_notes,
        is_primary_sheet=data.is_primary_sheet
    )
    db.add(char_ref)
    await db.commit()
    await db.refresh(char_ref)
    return char_ref
