from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.app.services.storage import storage_service
from backend.app.core.security import get_safe_storage_path
from backend.app.core.config import settings

router = APIRouter(tags=["Assets & Storage"])

@router.get("/storage/{category}/{filename}")
async def serve_stored_file(category: str, filename: str):
    rel_key = f"{category}/{filename}"
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
