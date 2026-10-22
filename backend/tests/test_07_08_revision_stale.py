import pytest
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_07_targeted_revision(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Targeted Revision Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun looked at Soo-jin.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    panels = ep_res.json()["scenes"][0]["beats"][0]["panels"]
    p1 = panels[0]
    p2 = panels[1]

    # Approve panel 2
    await client.post(
        f"/api/v1/artifacts/{p2['id']}/approvals",
        json={"artifact_type": "panel", "artifact_id": p2["id"], "artifact_version": p2["version"], "approved_by": "creator"}
    )

    # Change panel 1 composition
    patch_res = await client.patch(
        f"/api/v1/panels/{p1['id']}",
        json={"shot_type": "extreme_close_up", "camera_angle": "dutch_angle"}
    )
    assert patch_res.status_code == 200
    updated_p1 = patch_res.json()
    assert updated_p1["version"] == p1["version"] + 1
    assert updated_p1["is_approved"] is False

    # Panel 2 remains unchanged and approved
    ep_check = await client.get(f"/api/v1/episodes/{episode_id}")
    p2_check = [p for p in ep_check.json()["scenes"][0]["beats"][0]["panels"] if p["id"] == p2["id"]][0]
    assert p2_check["is_approved"] is True

@pytest.mark.asyncio
async def test_08_stale_job_protection(client: AsyncClient):
    from backend.app.services.versioning import versioning_service
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.models.adaptation import Panel

    res = await client.post("/api/v1/projects", json={"title": "Stale Job Protection Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Event happens here.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    panel = ep_res.json()["scenes"][0]["beats"][0]["panels"][0]

    # Panel is version 1. Creator modifies it to version 2.
    await client.patch(f"/api/v1/panels/{panel['id']}", json={"focal_point": "New revised focal point"})

    # Check stale job guard: An incoming job targeting old version 1 must be rejected!
    async with AsyncSessionLocal() as session:
        is_safe = await versioning_service.check_stale_job_overwrite_guard(
            db=session,
            panel_id=panel["id"],
            incoming_target_panel_version=1
        )
        assert is_safe is False, "Stale job targeting outdated panel version 1 should be blocked."
