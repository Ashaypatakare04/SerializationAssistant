import pytest
from httpx import AsyncClient
from backend.app.core.security import create_access_token, verify_token_payload, verify_token
from backend.tests.conftest import wait_for_job


@pytest.mark.asyncio
async def test_auth_token_issuance_and_me_endpoint(client: AsyncClient):
    # 1. Issue token for art director
    res = await client.post(
        "/api/v1/auth/token",
        json={"user_id": "director_min", "role": "art_director", "expires_in": 3600}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user_id"] == "director_min"
    assert data["role"] == "art_director"
    token = data["access_token"]

    # 2. Verify with Bearer header on /auth/me
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user_id"] == "director_min"
    assert me_data["role"] == "art_director"

    # 3. Verify with X-Studio-Auth header
    me_res2 = await client.get("/api/v1/auth/me", headers={"X-Studio-Auth": token})
    assert me_res2.status_code == 200
    assert me_res2.json()["user_id"] == "director_min"


@pytest.mark.asyncio
async def test_rbac_approval_enforcement(client: AsyncClient):
    # Setup project and panel
    creator_token = create_access_token("studio_owner", role="owner")
    headers_owner = {"Authorization": f"Bearer {creator_token}"}

    res = await client.post("/api/v1/projects", json={"title": "RBAC Security Project"}, headers=headers_owner)
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun smiled.", "filename": "story.txt"},
        headers=headers_owner
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=headers_owner)
    await wait_for_job(client, analysis_job.json()["id"], headers=headers_owner)

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers_owner)
    await wait_for_job(client, plan_job.json()["id"], headers=headers_owner)

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers_owner)
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs", headers=headers_owner)
    await wait_for_job(client, storyboard_job.json()["id"], headers=headers_owner)

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}", headers=headers_owner)
    panel = ep_res.json()["scenes"][0]["beats"][0]["panels"][0]

    # Register project team members
    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "script_writer_lee", "role": "writer"},
        headers=headers_owner
    )
    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "art_director_park", "role": "art_director"},
        headers=headers_owner
    )

    # Writer token attempts to approve -> Blocked with HTTP 403 Forbidden!
    writer_token = create_access_token("script_writer_lee", role="writer")
    writer_headers = {"Authorization": f"Bearer {writer_token}"}

    fail_appr = await client.post(
        f"/api/v1/artifacts/{panel['id']}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel["id"], "artifact_version": panel["version"], "approved_by": "writer"},
        headers=writer_headers
    )
    assert fail_appr.status_code == 403
    assert "not authorized to approve" in fail_appr.json()["detail"].lower()

    # Art director token attempts to approve -> Succeeds with HTTP 201 Created!
    director_token = create_access_token("art_director_park", role="art_director")
    director_headers = {"Authorization": f"Bearer {director_token}"}

    success_appr = await client.post(
        f"/api/v1/artifacts/{panel['id']}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel["id"], "artifact_version": panel["version"], "approved_by": "director"},
        headers=director_headers
    )
    assert success_appr.status_code == 201
    assert success_appr.json()["is_revoked"] is False
    assert success_appr.json()["approved_by"] == "director"

    # Verify panel is now marked approved
    check_ep = await client.get(f"/api/v1/episodes/{episode_id}", headers=headers_owner)
    p_check = check_ep.json()["scenes"][0]["beats"][0]["panels"][0]
    assert p_check["is_approved"] is True


@pytest.mark.asyncio
async def test_quota_tracking_and_limit_enforcement(client: AsyncClient):
    from backend.app.services.quota_service import quota_service
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.models.asset import Job

    creator_token = create_access_token("quota_user", role="owner")
    headers = {"Authorization": f"Bearer {creator_token}"}

    res = await client.post("/api/v1/projects", json={"title": "Quota Test Project"}, headers=headers)
    project_id = res.json()["id"]

    # Check quota reporting endpoint
    quota_res = await client.get(f"/api/v1/auth/quota/{project_id}", headers=headers)
    assert quota_res.status_code == 200
    q_data = quota_res.json()
    assert q_data["project_id"] == project_id
    assert q_data["daily_used_generations"] == 0
    assert q_data["daily_quota_limit"] >= 50

    # Test quota exceeded barrier
    async with AsyncSessionLocal() as session:
        # Check quota with a low threshold
        with pytest.raises(Exception) as exc_info:
            # Simulate 1 job already present
            job = Job(
                project_id=project_id,
                job_type="draft_generation",
                status="completed",
                progress_percentage=100,
                stage_description="Done",
                payload={},
                result_data={}
            )
            session.add(job)
            await session.commit()
            
            # Should fail if limit is 1
            await quota_service.check_generation_quota(project_id, session, limit=1)
        assert "429" in str(exc_info.value) or "quota exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_approval_resolves_real_project_id(client: AsyncClient):
    owner_token = create_access_token("approval_owner", role="owner")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    res = await client.post("/api/v1/projects", json={"title": "Approval FK Project"}, headers=owner_headers)
    assert res.status_code == 201
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun walked in the rain.", "filename": "ch1.txt"},
        headers=owner_headers,
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=owner_headers)
    await wait_for_job(client, analysis_job.json()["id"], headers=owner_headers)

    bible_res = await client.get(f"/api/v1/projects/{project_id}/story-bible", headers=owner_headers)
    bible = bible_res.json()

    # Owner approval resolves and stores the real project_id (not 'default')
    owner_appr = await client.post(
        f"/api/v1/artifacts/{bible['id']}/approvals",
        json={
            "artifact_type": "story_bible",
            "artifact_id": bible["id"],
            "artifact_version": bible["version"],
            "approved_by": "owner",
        },
        headers=owner_headers,
    )
    assert owner_appr.status_code == 201
    assert owner_appr.json()["project_id"] == project_id
