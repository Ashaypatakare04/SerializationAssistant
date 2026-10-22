import pytest
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_06_approval_gate_enforcement(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Approval Enforcement Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun waited. Soo-jin arrived.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    plan = plans_res.json()[0]
    episode_id = plan["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    panel = ep_res.json()["scenes"][0]["beats"][0]["panels"][0]
    panel_id = panel["id"]
    assert panel["is_approved"] is False

    # 1. Attempt final generation without approval -> MUST FAIL
    fail_res = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "final"}
    )
    assert fail_res.status_code == 400
    assert "Approval gate failure" in fail_res.json()["detail"]

    # 2. Try automated/AI approval -> MUST FAIL (AI cannot approve its own work)
    ai_approval_res = await client.post(
        f"/api/v1/artifacts/{panel_id}/approvals",
        json={
            "artifact_type": "panel",
            "artifact_id": panel_id,
            "artifact_version": panel["version"],
            "approved_by": "ai_agent"
        }
    )
    assert ai_approval_res.status_code == 400

    # 3. Creator approves panel -> MUST SUCCEED
    creator_approval_res = await client.post(
        f"/api/v1/artifacts/{panel_id}/approvals",
        json={
            "artifact_type": "panel",
            "artifact_id": panel_id,
            "artifact_version": panel["version"],
            "approved_by": "lead_creator_patak",
            "comments": "Framing and dialogue approved for final render."
        }
    )
    assert creator_approval_res.status_code == 201

    # 4. Now final generation MUST SUCCEED
    final_gen_res = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "final"}
    )
    assert final_gen_res.status_code == 202
    await wait_for_job(client, final_gen_res.json()["id"])
