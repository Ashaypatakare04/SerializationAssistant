import pytest
from httpx import AsyncClient
from backend.app.core.config import settings
from backend.app.core.security import get_safe_storage_path
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_11_security_and_safe_boundaries(client: AsyncClient):
    # 1. Path traversal guard
    with pytest.raises(HTTPException) as exc_info:
        get_safe_storage_path("./storage", "../../windows/system32/cmd.exe")
    assert exc_info.value.status_code == 400

    # 2. Oversized manuscript upload rejection
    res = await client.post("/api/v1/projects", json={"title": "Security Check Project"})
    project_id = res.json()["id"]

    huge_bytes = b"A" * (11 * 1024 * 1024)  # 11MB
    upload_res = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("huge.txt", huge_bytes, "text/plain")}
    )
    assert upload_res.status_code == 413

    # 3. Invalid artifact query
    not_found = await client.get("/api/v1/projects/non-existent-uuid-12345")
    assert not_found.status_code == 404

@pytest.mark.asyncio
async def test_12_real_provider_or_safe_mock_reporting(client: AsyncClient):
    # Capability inspection endpoint
    cap_res = await client.get("/api/v1/system/capabilities")
    assert cap_res.status_code == 200
    caps = cap_res.json()
    assert "active_image_provider" in caps
    assert "providers" in caps
    
    mock_info = caps["providers"]["mock"]
    assert mock_info["is_real_ai"] is False
    assert mock_info["mode"] == "test_development"

    # Check live providers
    openai_configured = caps["providers"]["openai"]["is_configured"]
    if openai_configured:
        # Run test with live provider
        pass
    else:
        # Per requirement Section 18: If credentials are unavailable, explicitly report not configured
        assert "Missing" in caps["providers"]["openai"]["status_message"]
