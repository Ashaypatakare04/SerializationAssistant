from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.services.storage import storage_service
from backend.app.core.security import get_safe_storage_path, validate_safe_filename, get_current_user_id, verify_project_access
from backend.app.core.config import settings

router = APIRouter(tags=["Assets & Storage"])

ALLOWED_STORAGE_CATEGORIES = {"references", "assets", "exports"}

@router.get("/storage/{category}/{filename}")
async def serve_stored_file(
    category: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    if category not in ALLOWED_STORAGE_CATEGORIES:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Direct unauthenticated retrieval of this storage category is not permitted."
        )
    
    clean_filename = validate_safe_filename(filename)
    rel_key = f"{category}/{clean_filename}"
    
    # Enforce object-level authorization by resolving the associated project
    project_id = None
    if category == "references":
        from backend.app.models.style import ReferenceAsset
        stmt = select(ReferenceAsset.project_id).where(ReferenceAsset.storage_key == rel_key)
        res = await db.execute(stmt)
        project_id = res.scalar_one_or_none()
    elif category == "assets":
        from backend.app.models.asset import AssetVersion, Asset
        stmt = (
            select(Asset.project_id)
            .join(AssetVersion, AssetVersion.asset_id == Asset.id)
            .where(AssetVersion.storage_key == rel_key)
        )
        res = await db.execute(stmt)
        project_id = res.scalar_one_or_none()
    elif category == "exports":
        from backend.app.models.asset import Export
        stmt = select(Export.project_id).where(Export.storage_key == rel_key)
        res = await db.execute(stmt)
        project_id = res.scalar_one_or_none()

    if project_id:
        await verify_project_access(project_id, user_id, db)

    try:
        abs_path = storage_service.get_absolute_path(rel_key)
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")
        
        # Determine media type
        suffix = abs_path.suffix.lower()
        media_type = "image/png"
        if suffix in (".jpg", ".jpeg"):
            media_type = "image/jpeg"
        elif suffix == ".zip":
            media_type = "application/zip"
        elif suffix == ".txt":
            media_type = "text/plain"

        return FileResponse(path=str(abs_path), media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

