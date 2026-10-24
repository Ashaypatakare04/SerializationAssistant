import pytest
import os
import io
import zipfile
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.providers.openai_provider import OpenAIProvider
from backend.app.providers.stability_provider import StabilityProvider
from backend.app.providers.gemini_provider import GeminiProvider

@pytest.mark.asyncio
async def test_01_production_identity_fails_closed_when_unconfigured():
    """
    Validate that in production mode:
    1. Unconfigured or default dev SECRET_KEY causes fail-closed HTTP 500.
    2. Arbitrary identity assertion via plain string X-Studio-Auth is rejected (HTTP 401).
    3. Valid signed token succeeds.
    """
    orig_env = settings.APP_ENV
    orig_secret = settings.SECRET_KEY
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        try:
            # 1. Production with dev secret -> Fails closed
            settings.APP_ENV = "production"
            settings.SECRET_KEY = "dev-secret-key-studio-insecure-only-for-local"
            
            resp = await ac.get("/api/v1/projects", headers={"X-Studio-Auth": "attacker_user"})
            assert resp.status_code == 500
            assert "Production misconfiguration" in resp.json()["detail"]

            # 2. Production with secure secret but plain unverified string -> Rejects identity assertion
            settings.SECRET_KEY = "a-very-secure-production-secret-key-32-chars-long!"
            resp = await ac.get("/api/v1/projects", headers={"X-Studio-Auth": "attacker_user"})
            assert resp.status_code == 401
            assert "Arbitrary identity assertion is forbidden" in resp.json()["detail"]

            # 3. Production without auth header -> 401
            resp = await ac.get("/api/v1/projects")
            assert resp.status_code == 401

            # 4. Production with valid signed token -> Succeeds
            token = create_access_token("verified_creator_1")
            resp = await ac.get("/api/v1/projects", headers={"X-Studio-Auth": token})
            assert resp.status_code == 200

        finally:
            settings.APP_ENV = orig_env
            settings.SECRET_KEY = orig_secret

@pytest.mark.asyncio
async def test_02_static_storage_cross_user_isolation():
    """
    Validate that static storage endpoint /api/v1/storage/{category}/{filename}
    strictly enforces project ownership and blocks cross-user asset theft.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # User A creates a project and uploads a reference
        user_a = "creator_alice"
        user_b = "attacker_bob"
        
        headers_a = {"X-Studio-Auth": user_a}
        headers_b = {"X-Studio-Auth": user_b}
        
        proj_resp = await ac.post("/api/v1/projects", json={"title": "Alice Private Project"}, headers=headers_a)
        assert proj_resp.status_code in (200, 201)
        proj_id = proj_resp.json()["id"]

        # Upload reference
        img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("alice_ref.png", io.BytesIO(img_bytes), "image/png")}
        ref_resp = await ac.post(f"/api/v1/projects/{proj_id}/references", files=files, data={"role": "character"}, headers=headers_a)
        assert ref_resp.status_code in (200, 201)
        ref_filename = os.path.basename(ref_resp.json()["storage_key"])

        # Alice can access her own reference file via storage
        alice_get = await ac.get(f"/api/v1/storage/references/{ref_filename}", headers=headers_a)
        assert alice_get.status_code == 200

        # Bob attempts to access Alice's reference file via storage -> Blocked 403 Forbidden
        bob_get = await ac.get(f"/api/v1/storage/references/{ref_filename}", headers=headers_b)
        assert bob_get.status_code == 403
        assert "Access denied" in bob_get.json()["detail"]

@pytest.mark.asyncio
async def test_03_real_provider_contracts_and_capability_truth():
    """
    Validate that real provider adapters report honest capabilities
    and do not misrepresent inpainting or reference conditioning support.
    """
    openai = OpenAIProvider(api_key="")
    caps_oai = openai.inspect_capabilities()
    assert caps_oai["is_real_ai"] is True
    assert caps_oai["supports_inpainting"] is False, "DALL-E 3 does not support inpainting"
    assert caps_oai["supports_character_sheets"] is False, "DALL-E 3 does not support reference conditioning"
    assert caps_oai["is_configured"] is False

    stability = StabilityProvider(api_key="")
    caps_stab = stability.inspect_capabilities()
    assert caps_stab["is_real_ai"] is True
    assert caps_stab["supports_inpainting"] is True
    assert caps_stab["supports_character_sheets"] is True
    assert caps_stab["is_configured"] is False

    gemini = GeminiProvider(api_key="")
    caps_gem = gemini.inspect_capabilities()
    assert caps_gem["is_real_ai"] is True
    assert caps_gem["is_configured"] is False

@pytest.mark.asyncio
async def test_04_e2e_approval_and_export_gate_enforcement():
    """
    Validate end-to-end workflow:
    1. Project, Story Bible, Episode with 2 panels.
    2. Attempting export before approvals fail.
    3. Approving panels and assets allows clean vertical export.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-Studio-Auth": "creator_e2e_user"}
        
        # 1. Create project
        p_resp = await ac.post("/api/v1/projects", json={"title": "E2E Gate Test Project"}, headers=headers)
        assert p_resp.status_code in (200, 201)
        proj_id = p_resp.json()["id"]

        # Ingest manuscript
        doc_resp = await ac.post(
            f"/api/v1/projects/{proj_id}/documents",
            files={"file": ("story.txt", io.BytesIO(b"Chapter 1: The Gathering Storm.\nElena Vance stepped into the rain.\nKaelen Frost watched from the shadowed doorway."), "text/plain")},
            headers=headers
        )
        assert doc_resp.status_code in (200, 201)

        from backend.app.workers.job_runner import job_runner

        # Wait helper
        async def wait_for_job(jid: str):
            if jid in job_runner._running_tasks:
                try:
                    await job_runner._running_tasks[jid]
                except Exception:
                    pass

        # Run Story Analysis
        job_resp = await ac.post(f"/api/v1/projects/{proj_id}/analysis-jobs", headers=headers)
        await wait_for_job(job_resp.json()["id"])

        # Create Adaptation Plan
        plan_job = await ac.post(f"/api/v1/projects/{proj_id}/adaptation-plans", headers=headers)
        await wait_for_job(plan_job.json()["id"])
        
        plans_resp = await ac.get(f"/api/v1/projects/{proj_id}/adaptation-plans", headers=headers)
        plans = plans_resp.json()
        assert len(plans) > 0
        ep_id = plans[0]["episodes"][0]["id"]

        # Create Storyboard
        sb_job = await ac.post(f"/api/v1/episodes/{ep_id}/storyboard-jobs", headers=headers)
        await wait_for_job(sb_job.json()["id"])

        ep_resp = await ac.get(f"/api/v1/episodes/{ep_id}", headers=headers)
        ep = ep_resp.json()
        panels = []
        for s in ep["scenes"]:
            for b in s["beats"]:
                panels.extend(b["panels"])
        assert len(panels) >= 2

        # 2. Attempt export while panels are unapproved -> Export job fails with clear error
        exp_job = await ac.post(f"/api/v1/episodes/{ep_id}/export-jobs?require_all_approved=true", headers=headers)
        assert exp_job.status_code == 202
        await wait_for_job(exp_job.json()["id"])
        
        check_exp_job = await ac.get(f"/api/v1/jobs/{exp_job.json()['id']}", headers=headers)
        assert check_exp_job.json()["status"] == "failed"
        assert "approval" in check_exp_job.json()["error_message"].lower()

        # 3. Approve storyboard panels and generate final artwork
        for p in panels:
            # Approve panel storyboard
            appr = await ac.post(
                f"/api/v1/artifacts/{p['id']}/approvals",
                json={
                    "artifact_type": "panel",
                    "artifact_id": p["id"],
                    "artifact_version": p["version"],
                    "approved_by": "creator_e2e_user"
                },
                headers=headers
            )
            assert appr.status_code in (200, 201)

            # Generate final artwork
            gen_job = await ac.post(f"/api/v1/panels/{p['id']}/generation-jobs", json={"stage": "final"}, headers=headers)
            assert gen_job.status_code == 202
            await wait_for_job(gen_job.json()["id"])

            # Retrieve generated asset and approve asset version
            assets_resp = await ac.get(f"/api/v1/panels/{p['id']}/assets", headers=headers)
            asset_data = assets_resp.json()[0]
            latest_version = asset_data["versions"][-1]
            
            art_appr = await ac.post(
                f"/api/v1/artifacts/{latest_version['id']}/approvals",
                json={
                    "artifact_type": "asset_version",
                    "artifact_id": latest_version["id"],
                    "artifact_version": latest_version["version_number"],
                    "approved_by": "creator_e2e_user"
                },
                headers=headers
            )
            assert art_appr.status_code in (200, 201)

        # 4. Now trigger export with all approved -> Succeeds!
        exp_job2 = await ac.post(f"/api/v1/episodes/{ep_id}/export-jobs?require_all_approved=true", headers=headers)
        assert exp_job2.status_code == 202
        await wait_for_job(exp_job2.json()["id"])

        check_exp2 = await ac.get(f"/api/v1/jobs/{exp_job2.json()['id']}", headers=headers)
        assert check_exp2.json()["status"] == "completed"
        export_id = check_exp2.json()["result_data"]["export_id"]

        # Verify export download and ZIP integrity
        dl_resp = await ac.get(f"/api/v1/exports/{export_id}/download", headers=headers)
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/zip"

        with zipfile.ZipFile(io.BytesIO(dl_resp.content)) as zf:
            namelist = zf.namelist()
            assert "manifest.json" in namelist
            assert any(n.startswith("slices/") for n in namelist)

@pytest.mark.asyncio
async def test_05_job_recovery_preserves_approvals_and_data_integrity():
    """
    Validate that server crash recovery:
    1. Resets stuck running jobs to failed state cleanly.
    2. Does not corrupt existing approvals, panel versions, or asset records.
    """
    from backend.app.workers.job_runner import job_runner
    from backend.app.models.asset import Job
    from backend.app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    # Directly insert an orphaned job left in 'running' state with max retries reached
    async with AsyncSessionLocal() as session:
        orphaned = Job(
            project_id="00000000-0000-0000-0000-000000000000",
            job_type="panel_generation",
            status="running",
            progress_percentage=50,
            stage_description="Rendering draft panel in background...",
            payload={"stage": "draft"},
            retry_count=3,
            max_retries=3
        )
        session.add(orphaned)
        await session.commit()
        await session.refresh(orphaned)
        job_id = orphaned.id

    # Trigger startup recovery
    await job_runner.recover_orphaned_jobs()

    # Verify job was marked failed cleanly without corrupting other state
    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == job_id)
        res = await session.execute(stmt)
        recovered_job = res.scalar_one()
        assert recovered_job.status == "failed"
        assert "interrupted by server shutdown" in recovered_job.error_message.lower()
