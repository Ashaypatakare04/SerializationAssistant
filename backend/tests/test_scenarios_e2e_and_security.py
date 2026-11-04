import pytest
import time
import base64
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy import select, update
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.asset import Job, Asset, Approval, Export
from backend.app.models.adaptation import Panel
from backend.app.models.project import Project, ProjectMember
from backend.app.services.quota_service import quota_service
from backend.tests.conftest import wait_for_job


@pytest.mark.asyncio
async def test_scenario_full_studio_production_lifecycle(client: AsyncClient):
    """
    Scenario 1: Comprehensive E2E Studio Production Pipeline
    From novel text ingestion to storyboard generation, draft creation, inpainting mask editing,
    approval gating by Art Director, final asset generation, and lettered webtoon slice export.
    """
    owner_token = create_access_token("studio_owner_vip", role="owner")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 1. Project Creation
    res = await client.post("/api/v1/projects", json={"title": "Neo Tokyo Chronicles"}, headers=owner_headers)
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Ingest Novel Text Document
    novel_text = (
        "Chapter 1: Rain on Neon.\n"
        "Min-jun stepped into the alleyway as acid rain dripped from the glowing signs. "
        "'They know we're here,' whispered Hana, her ocular implant flickering amber. "
        "Suddenly, a corporate drone descended, spotlights cutting through the smoke!"
    )
    doc_res = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": novel_text, "filename": "chapter_1.txt"},
        headers=owner_headers
    )
    assert doc_res.status_code == 201

    # 3. Trigger Script Analysis Job
    analysis_res = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=owner_headers)
    assert analysis_res.status_code == 202
    await wait_for_job(client, analysis_res.json()["id"], headers=owner_headers)

    # 4. Trigger Adaptation Plan Job
    plan_res = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans", headers=owner_headers)
    assert plan_res.status_code == 202
    await wait_for_job(client, plan_res.json()["id"], headers=owner_headers)

    plans_list = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans", headers=owner_headers)
    assert len(plans_list.json()) > 0
    episode_id = plans_list.json()[0]["episodes"][0]["id"]

    # 5. Trigger Storyboard Job
    sb_res = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs", headers=owner_headers)
    assert sb_res.status_code == 202
    await wait_for_job(client, sb_res.json()["id"], headers=owner_headers)

    ep_data = await client.get(f"/api/v1/episodes/{episode_id}", headers=owner_headers)
    assert ep_data.status_code == 200
    panel = ep_data.json()["scenes"][0]["beats"][0]["panels"][0]
    panel_id = panel["id"]

    # 6. Add Team Members (Art Director and Writer)
    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "yuna_art_director", "role": "art_director"},
        headers=owner_headers
    )
    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "jin_writer", "role": "writer"},
        headers=owner_headers
    )

    # 7. Generate Draft Asset
    draft_trigger = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "draft", "prompt_override": "Cyberpunk alleyway with neon reflections"},
        headers=owner_headers
    )
    assert draft_trigger.status_code == 202
    draft_job_id = draft_trigger.json()["id"]
    await wait_for_job(client, draft_job_id, headers=owner_headers)

    # Verify active asset exists
    check_panel_res = await client.get(f"/api/v1/episodes/{episode_id}", headers=owner_headers)
    updated_panel = check_panel_res.json()["scenes"][0]["beats"][0]["panels"][0]
    assert updated_panel["active_asset_id"] is not None

    # 8. Interactive Inpainting with Mask
    mask_b64 = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82").decode('utf-8')
    inpaint_trigger = await client.post(
        f"/api/v1/panels/{panel_id}/inpaint",
        json={"instruction": "Add more lens flare and smoke in bottom left", "mask_base64": mask_b64},
        headers=owner_headers
    )
    assert inpaint_trigger.status_code == 202
    await wait_for_job(client, inpaint_trigger.json()["id"], headers=owner_headers)

    # Verify inpainting unapproves panel
    check_panel_res2 = await client.get(f"/api/v1/episodes/{episode_id}", headers=owner_headers)
    assert check_panel_res2.json()["scenes"][0]["beats"][0]["panels"][0]["is_approved"] is False

    # 9. Verify Final Generation is GATED behind approval
    fail_final = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "final"},
        headers=owner_headers
    )
    assert fail_final.status_code == 400
    assert "approval" in fail_final.json()["detail"].lower()

    # 10. Art Director Signs Off Approval
    director_token = create_access_token("yuna_art_director", role="art_director")
    director_headers = {"Authorization": f"Bearer {director_token}"}
    appr_res = await client.post(
        f"/api/v1/artifacts/{panel_id}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel_id, "artifact_version": updated_panel["version"], "approved_by": "yuna_art_director"},
        headers=director_headers
    )
    assert appr_res.status_code == 201

    # 11. Final Generation Now SUCCEEDS
    final_trigger = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "final"},
        headers=owner_headers
    )
    assert final_trigger.status_code == 202
    await wait_for_job(client, final_trigger.json()["id"], headers=owner_headers)

    # 12. Export Full Webtoon with Lettering Compositor
    export_trigger = await client.post(
        f"/api/v1/episodes/{episode_id}/export-jobs?require_all_approved=false",
        json={"export_format": "vertical_webtoon_zip", "include_speech_bubbles": True},
        headers=owner_headers
    )
    assert export_trigger.status_code == 202
    export_job = await wait_for_job(client, export_trigger.json()["id"], headers=owner_headers)
    assert export_job["status"] == "completed"

    # Verify Export database record
    async with AsyncSessionLocal() as session:
        exp_stmt = select(Export).where(Export.episode_id == episode_id)
        exp_res = await session.execute(exp_stmt)
        export_record = exp_res.scalars().first()
        assert export_record is not None
        assert export_record.is_verified is True
        assert export_record.slice_count >= 1
        assert "panels" in export_record.manifest_data
        assert export_record.manifest_data["include_speech_bubbles"] is True
        assert export_record.manifest_data["slice_count"] >= 1


@pytest.mark.asyncio
async def test_scenario_jwt_security_and_token_boundaries(client: AsyncClient):
    """
    Scenario 2: JWT Security Boundaries
    Validates rejection of expired tokens, tampered signatures, and malformed auth headers.
    """
    orig_env = settings.APP_ENV
    orig_secret = settings.SECRET_KEY
    try:
        settings.APP_ENV = "production"
        settings.SECRET_KEY = "test-prod-secret-32-chars-long-secure!!"

        # 1. Expired Token
        expired_token = create_access_token("expired_user", role="owner", expires_in=-120)
        res_exp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res_exp.status_code == 401
        assert "Invalid, expired, or unverified" in res_exp.json()["detail"]

        # 2. Tampered Token Signature
        valid_token = create_access_token("legit_user", role="admin")
        parts = valid_token.split(".")
        tampered_sig = parts[1][:-4] + "AAAA"
        tampered_token = f"{parts[0]}.{tampered_sig}"
        res_tamp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res_tamp.status_code == 401
        assert "Invalid, expired, or unverified" in res_tamp.json()["detail"]

        # 3. Malformed Auth Headers
        res_empty_bearer = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
        assert res_empty_bearer.status_code == 401

        res_garbage = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer random-unparseable-token"})
        assert res_garbage.status_code == 401

        # 4. Valid Token in both Bearer and X-Studio-Auth
        valid_token2 = create_access_token("verified_artist", role="art_director")
        res_bearer = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {valid_token2}"})
        assert res_bearer.status_code == 200
        assert res_bearer.json()["user_id"] == "verified_artist"

        res_custom = await client.get("/api/v1/auth/me", headers={"X-Studio-Auth": valid_token2})
        assert res_custom.status_code == 200
        assert res_custom.json()["user_id"] == "verified_artist"
    finally:
        settings.APP_ENV = orig_env
        settings.SECRET_KEY = orig_secret


@pytest.mark.asyncio
async def test_scenario_full_rbac_role_permission_matrix(client: AsyncClient):
    """
    Scenario 3: Complete Studio RBAC Permission Matrix
    Tests all roles (owner, admin, art_director, writer, storyboarder, editor) across:
    - Member invitation privilege (restricted to owner & admin)
    - Creative approval sign-off privilege (restricted to owner, admin & art_director)
    """
    owner_token = create_access_token("studio_boss", role="owner")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Setup project and panel
    p_res = await client.post("/api/v1/projects", json={"title": "Matrix Project"}, headers=owner_headers)
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # Setup roles
    roles = {
        "admin": create_access_token("admin_user", role="admin"),
        "art_director": create_access_token("director_user", role="art_director"),
        "writer": create_access_token("writer_user", role="writer"),
        "storyboarder": create_access_token("storyboarder_user", role="storyboarder"),
        "editor": create_access_token("editor_user", role="editor"),
    }

    # Add all users as project members first
    for role_name, token in roles.items():
        user_id = f"{role_name}_user"
        await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": user_id, "role": role_name},
            headers=owner_headers
        )

    # TEST MATRIX 1: Member Invitation Rights
    # Owner & Admin -> PERMITTED (201)
    admin_headers = {"Authorization": f"Bearer {roles['admin']}"}
    adm_add = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "contractor_1", "role": "editor"},
        headers=admin_headers
    )
    assert adm_add.status_code == 201

    # Art Director, Writer, Storyboarder, Editor -> FORBIDDEN (403)
    for forbidden_role in ["art_director", "writer", "storyboarder", "editor"]:
        f_headers = {"Authorization": f"Bearer {roles[forbidden_role]}"}
        res_f = await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": f"guest_{forbidden_role}", "role": "editor"},
            headers=f_headers
        )
        assert res_f.status_code == 403, f"Role {forbidden_role} should not be allowed to add members!"

    # Setup an episode & panel for approval testing
    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Hero jumps into the abyss.", "filename": "abyss.txt"},
        headers=owner_headers
    )
    an_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=owner_headers)
    await wait_for_job(client, an_job.json()["id"], headers=owner_headers)
    pl_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans", headers=owner_headers)
    await wait_for_job(client, pl_job.json()["id"], headers=owner_headers)
    plans = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans", headers=owner_headers)
    ep_id = plans.json()[0]["episodes"][0]["id"]
    sb_job = await client.post(f"/api/v1/episodes/{ep_id}/storyboard-jobs", headers=owner_headers)
    await wait_for_job(client, sb_job.json()["id"], headers=owner_headers)

    ep_info = await client.get(f"/api/v1/episodes/{ep_id}", headers=owner_headers)
    panel_id = ep_info.json()["scenes"][0]["beats"][0]["panels"][0]["id"]

    # TEST MATRIX 2: Approval Gate Rights
    # Writer, Storyboarder, Editor -> FORBIDDEN (403)
    for non_approver in ["writer", "storyboarder", "editor"]:
        na_headers = {"Authorization": f"Bearer {roles[non_approver]}"}
        appr_block = await client.post(
            f"/api/v1/artifacts/{panel_id}/approvals",
            json={"artifact_type": "panel", "artifact_id": panel_id, "artifact_version": 1, "approved_by": non_approver},
            headers=na_headers
        )
        assert appr_block.status_code == 403, f"Role {non_approver} should be forbidden from approving!"

    # Art Director -> PERMITTED (201)
    dir_headers = {"Authorization": f"Bearer {roles['art_director']}"}
    appr_dir = await client.post(
        f"/api/v1/artifacts/{panel_id}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel_id, "artifact_version": 1, "approved_by": "art_director"},
        headers=dir_headers
    )
    assert appr_dir.status_code == 201


@pytest.mark.asyncio
async def test_scenario_cross_tenant_isolation_and_security(client: AsyncClient):
    """
    Scenario 4: Cross-Tenant Isolation
    Validates that User B cannot access, inspect, or modify User A's private projects,
    documents, quotas, or panels.
    """
    token_a = create_access_token("tenant_alpha", role="owner")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = create_access_token("tenant_bravo", role="owner")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant Alpha creates Project Alpha
    res_a = await client.post("/api/v1/projects", json={"title": "Alpha Confidential"}, headers=headers_a)
    assert res_a.status_code == 201
    p_alpha_id = res_a.json()["id"]

    # Tenant Bravo attempts unauthorized actions against Project Alpha -> All 403 Forbidden
    # 1. Read Project
    res_read = await client.get(f"/api/v1/projects/{p_alpha_id}", headers=headers_b)
    assert res_read.status_code == 403

    # 2. Add Team Member
    res_add_member = await client.post(
        f"/api/v1/projects/{p_alpha_id}/members",
        json={"user_id": "spy", "role": "editor"},
        headers=headers_b
    )
    assert res_add_member.status_code == 403

    # 3. View Quota
    res_quota = await client.get(f"/api/v1/auth/quota/{p_alpha_id}", headers=headers_b)
    assert res_quota.status_code == 403

    # 4. Ingest Document into Alpha
    res_doc = await client.post(
        f"/api/v1/projects/{p_alpha_id}/documents",
        data={"raw_text": "Injected malicious text", "filename": "evil.txt"},
        headers=headers_b
    )
    assert res_doc.status_code == 403


@pytest.mark.asyncio
async def test_scenario_quota_rate_limiting_and_rolling_24h_window(client: AsyncClient):
    """
    Scenario 5: Quota Rate Limiting & Rolling 24-Hour Expiration
    Validates that:
    1. Reaching daily quota limit blocks generation with 429 Too Many Requests.
    2. Jobs older than 24 hours expire from the window, reopening capacity.
    """
    owner_token = create_access_token("quota_sentinel", role="owner")
    headers = {"Authorization": f"Bearer {owner_token}"}

    res = await client.post("/api/v1/projects", json={"title": "Quota Boundary Project"}, headers=headers)
    assert res.status_code == 201
    project_id = res.json()["id"]

    # Verify initial quota reports 0 used
    q_res = await client.get(f"/api/v1/auth/quota/{project_id}", headers=headers)
    assert q_res.status_code == 200
    assert q_res.json()["daily_used_generations"] == 0

    # Simulate reaching the quota limit with historical vs active jobs
    async with AsyncSessionLocal() as session:
        # Create 1 job in the active 24h window
        active_job = Job(
            project_id=project_id,
            job_type="draft_generation",
            status="completed",
            progress_percentage=100,
            stage_description="Done",
            payload={},
            result_data={}
        )
        session.add(active_job)

        # Create 1 historical job older than 24 hours (backdated created_at)
        past_time = datetime.now(timezone.utc) - timedelta(hours=25)
        expired_job = Job(
            project_id=project_id,
            job_type="draft_generation",
            status="completed",
            progress_percentage=100,
            stage_description="Done",
            payload={},
            result_data={}
        )
        session.add(expired_job)
        await session.flush()

        # Update expired_job created_at manually
        await session.execute(
            update(Job).where(Job.id == expired_job.id).values(created_at=past_time)
        )
        await session.commit()

        # Check quota count: only the active job should be counted!
        active_count = await quota_service.get_usage_count(project_id, session)
        assert active_count == 1

        # Check that quota enforcement raises 429 when limit is met
        with pytest.raises(Exception) as exc_info:
            await quota_service.check_generation_quota(project_id, session, limit=1)
        assert "429" in str(exc_info.value) or "quota exceeded" in str(exc_info.value).lower()
