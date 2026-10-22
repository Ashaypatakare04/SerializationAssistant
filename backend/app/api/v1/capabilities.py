from typing import Dict, Any
from fastapi import APIRouter
from backend.app.providers.factory import provider_factory

router = APIRouter(tags=["System Capabilities"])

@router.get("/system/capabilities")
async def get_system_capabilities() -> Dict[str, Any]:
    return provider_factory.get_all_capabilities()
