import pytest
import io
from PIL import Image
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_03_style_consistency_and_versioning(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Style Consistency Project"})
    project_id = res.json()["id"]

    # Upload reference
    img = Image.new("RGB", (400, 500), color=(30, 40, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    await client.post(
        f"/api/v1/projects/{project_id}/references",
        files={"file": ("style_ref.png", buf.getvalue(), "image/png")},
        data={"role": "visual_style", "label": "Dark Atmospheric Manhwa"}
    )

    # Style Analysis
    style_job = await client.post(f"/api/v1/projects/{project_id}/style-analysis-jobs")
    await wait_for_job(client, style_job.json()["id"])

    prof_res = await client.get(f"/api/v1/projects/{project_id}/style-profile")
    profile = prof_res.json()
    assert profile["current_version"] == 1
    assert len(profile["versions"]) == 1

    # Modify style profile version
    patch_res = await client.patch(
        f"/api/v1/style-profiles/{profile['id']}/versions/1",
        json={"linework_and_contours": "Ultra-bold dynamic contours with sharp tapered nibs"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["linework_and_contours"] == "Ultra-bold dynamic contours with sharp tapered nibs"

@pytest.mark.asyncio
async def test_04_character_consistency_tracking(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Character Consistency Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun looked at Soo-jin. Soo-jin nodded back.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    plan = plans_res.json()[0]
    episode_id = plan["episodes"][0]["id"]

    # Generate storyboard
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    # Fetch episode and verify panels track character appearance versions
    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    episode = ep_res.json()
    panels = []
    for s in episode["scenes"]:
        for b in s["beats"]:
            panels.extend(b["panels"])

    assert len(panels) >= 2
    for p in panels:
        assert len(p["character_ids"]) > 0
        assert isinstance(p["character_appearance_versions"], dict)
