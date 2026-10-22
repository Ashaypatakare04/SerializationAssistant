import pytest
import io
from PIL import Image
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_02_reference_isolation(client: AsyncClient):
    # 1. Create Project
    res = await client.post("/api/v1/projects", json={
        "title": "Reference Isolation Test",
        "description": "Ensure style reference content does not contaminate adaptation canon."
    })
    project_id = res.json()["id"]

    # 2. Upload source manuscript
    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Jin-woo entered the silent dungeon. Kang-dae waited with weapons drawn.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    # 3. Create dummy image bytes for reference
    img = Image.new("RGB", (400, 600), color=(50, 60, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    # Upload reference with external characters mentioned in label/description
    upload_res = await client.post(
        f"/api/v1/projects/{project_id}/references",
        files={"file": ("cyber_manga_ref.png", img_bytes, "image/png")},
        data={
            "role": "visual_style",
            "label": "Neon City reference from unrelated comic featuring Detective Vance",
            "description": "Shows heavy ink lines and cyber shadows. Vance is fighting a dragon in Tokyo."
        }
    )
    assert upload_res.status_code == 201

    # 4. Trigger Style Analysis
    style_job = await client.post(f"/api/v1/projects/{project_id}/style-analysis-jobs")
    assert style_job.status_code == 202
    await wait_for_job(client, style_job.json()["id"])

    # 5. Fetch Style Profile
    prof_res = await client.get(f"/api/v1/projects/{project_id}/style-profile")
    assert prof_res.status_code == 200
    profile = prof_res.json()
    ver = profile["versions"][0]

    # Verify visual attributes extracted
    assert len(ver["linework_and_contours"]) > 0
    assert len(ver["palette_and_colors"]) > 0
    assert "reference_isolation_notes" in ver
    assert "No reference characters" in ver["reference_isolation_notes"]

    # 6. Verify Story Bible does not contain Vance or Tokyo dragon
    bible_res = await client.get(f"/api/v1/projects/{project_id}/story-bible")
    bible = bible_res.json()
    char_names = [c["canonical_name"].lower() for c in bible["characters"]]
    assert "vance" not in char_names
    assert "detective vance" not in char_names
