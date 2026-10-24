import io
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from backend.app.db.session import AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.asset import AssetVersion, AssetDependency
from backend.app.providers.factory import provider_factory
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_01_cross_user_project_access_blocked(client: AsyncClient):
    """
    SEC-01 Regression Test:
    Verify that Broken Object-Level Authorization (BOLA/IDOR) is blocked.
    User B must NOT be able to access, modify, or upload to User A's project.
    """
    auth_a = {"X-Studio-Auth": "creator_alice"}
    auth_b = {"X-Studio-Auth": "creator_bob"}

    # 1. Alice creates Project A
    res = await client.post("/api/v1/projects", json={
        "title": "Alice's Secret Mystery",
        "description": "Private manuscript not for Bob"
    }, headers=auth_a)
    assert res.status_code == 201
    project_a_id = res.json()["id"]

    # 2. Bob attempts to view Alice's Project -> MUST RETURN 403
    bob_view = await client.get(f"/api/v1/projects/{project_a_id}", headers=auth_b)
    assert bob_view.status_code == 403
    assert "Access denied" in bob_view.json()["detail"]

    # 3. Bob attempts to patch Alice's Project -> MUST RETURN 403
    bob_patch = await client.patch(
        f"/api/v1/projects/{project_a_id}",
        json={"title": "Hacked Title"},
        headers=auth_b
    )
    assert bob_patch.status_code == 403

    # 4. Bob attempts to upload a document to Alice's Project -> MUST RETURN 403
    bob_upload = await client.post(
        f"/api/v1/projects/{project_a_id}/documents",
        data={"raw_text": "Bob's malicious payload", "filename": "test.txt"},
        headers=auth_b
    )
    assert bob_upload.status_code == 403

    # 5. Alice can view her own project normally -> MUST RETURN 200
    alice_view = await client.get(f"/api/v1/projects/{project_a_id}", headers=auth_a)
    assert alice_view.status_code == 200
    assert alice_view.json()["title"] == "Alice's Secret Mystery"

@pytest.mark.asyncio
async def test_02_storage_private_document_category_blocked(client: AsyncClient):
    """
    SEC-02 Regression Test:
    Verify that raw private manuscripts in storage/documents cannot be downloaded
    directly via the public storage endpoint.
    """
    res = await client.get("/api/v1/storage/documents/confidential_novel.txt")
    assert res.status_code == 403
    assert "not permitted" in res.json()["detail"]

@pytest.mark.asyncio
async def test_03_unconfigured_real_provider_fails_honestly(client: AsyncClient, monkeypatch):
    """
    SEC-03 & Principle 2.F Regression Test:
    Requesting an unconfigured real provider must raise an explicit error
    rather than silently returning a mock provider.
    """
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "STABILITY_API_KEY", "")
    with pytest.raises(RuntimeError) as exc_info:
        provider_factory.get_llm_provider("openai")
    assert "OPENAI_API_KEY is not configured" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_img:
        provider_factory.get_image_provider("stability")
    assert "STABILITY_API_KEY is not configured" in str(exc_img.value)

@pytest.mark.asyncio
async def test_04_export_enforces_approval_by_default(client: AsyncClient):
    """
    SEC-04 & Principle 2.5 Regression Test:
    Calling episode export without query parameters defaults to require_all_approved=True,
    blocking unapproved panels from being exported.
    """
    res = await client.post("/api/v1/projects", json={"title": "Strict Export Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun smiled. Soo-jin frowned.", "filename": "ch1.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    # Export without require_all_approved parameter (defaults to True) -> MUST FAIL in background job
    export_job_res = await client.post(f"/api/v1/episodes/{episode_id}/export-jobs")
    assert export_job_res.status_code == 202
    job_id = export_job_res.json()["id"]

    job_data = await wait_for_job(client, job_id)
    assert job_data["status"] == "failed"
    assert "explicit creator approval" in job_data["error_message"]

@pytest.mark.asyncio
async def test_05_character_reference_propagation(client: AsyncClient):
    """
    Priority 1 & Section 13 Regression Test:
    Verify that uploaded character sheets are actually passed to generation
    and recorded in asset dependencies.
    """
    res = await client.post("/api/v1/projects", json={"title": "Character Propagation Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun looked at the stars.", "filename": "ch1.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    # Fetch character
    bible_res = await client.get(f"/api/v1/projects/{project_id}/story-bible")
    minjun_id = bible_res.json()["characters"][0]["id"]

    # Upload character reference sheet
    img = Image.new("RGB", (300, 400), color=(80, 100, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    ref_res = await client.post(
        f"/api/v1/projects/{project_id}/references",
        files={"file": ("minjun_sheet.png", img_bytes, "image/png")},
        data={"role": "character_identity", "label": "Min-jun Turnaround Sheet"}
    )
    assert ref_res.status_code == 201
    ref_asset_id = ref_res.json()["id"]

    # Link character reference
    link_res = await client.post(
        f"/api/v1/projects/{project_id}/character-references",
        json={
            "character_id": minjun_id,
            "reference_asset_id": ref_asset_id,
            "is_primary_sheet": True,
            "relevance_notes": "Canonical trench coat and hair"
        }
    )
    assert link_res.status_code == 200

    # Create storyboard
    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    panel = ep_res.json()["scenes"][0]["beats"][0]["panels"][0]

    # Assign character to panel
    await client.patch(f"/api/v1/panels/{panel['id']}", json={"character_ids": [minjun_id]})

    # Trigger draft generation
    gen_res = await client.post(
        f"/api/v1/panels/{panel['id']}/generation-jobs",
        json={"stage": "draft"}
    )
    assert gen_res.status_code == 202
    await wait_for_job(client, gen_res.json()["id"])

    # Verify AssetVersion and AssetDependency records
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AssetVersion)
            .order_by(AssetVersion.created_at.desc())
        )
        ver_res = await session.execute(stmt)
        latest_ver = ver_res.scalars().first()
        assert latest_ver is not None
        assert link_res.json()["id"] in latest_ver.character_reference_ids

        # Check dependencies table
        dep_stmt = select(AssetDependency).where(
            AssetDependency.asset_version_id == latest_ver.id,
            AssetDependency.dependency_type == "character_ref"
        )
        dep_res = await session.execute(dep_stmt)
        deps = dep_res.scalars().all()
        assert len(deps) >= 1
        dep_ids = [d.dependency_id for d in deps]
        assert ref_asset_id in dep_ids
        assert minjun_id in dep_ids


