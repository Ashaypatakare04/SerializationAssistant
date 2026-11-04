import pytest
import base64
import asyncio
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.core.security import create_access_token
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.asset import Asset, AssetVersion, Job, Approval
from backend.app.models.adaptation import Panel, DialogueSegment
from backend.app.export.webtoon_exporter import wrap_dialogue_text, composite_dialogue_bubbles
from backend.app.workers.job_runner import job_runner
from backend.tests.conftest import wait_for_job


@pytest.mark.asyncio
async def test_scenario_inpainting_validation_and_failures(client: AsyncClient):
    """
    Scenario 6: Inpainting Input Validation & Fail-Safes
    Tests:
    1. Corrupted base64 mask -> 400 Bad Request
    2. Non-existent panel ID -> 404 Not Found
    3. Panel with no active asset -> 400 Bad Request
    """
    owner_token = create_access_token("painter_user", role="owner")
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Setup project and panel (without generated asset)
    res = await client.post("/api/v1/projects", json={"title": "Inpaint Edge Cases"}, headers=headers)
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "A warrior stands in the rain.", "filename": "story.txt"},
        headers=headers
    )
    an_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=headers)
    await wait_for_job(client, an_job.json()["id"], headers=headers)
    pl_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers)
    await wait_for_job(client, pl_job.json()["id"], headers=headers)
    plans = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers)
    ep_id = plans.json()[0]["episodes"][0]["id"]
    sb_job = await client.post(f"/api/v1/episodes/{ep_id}/storyboard-jobs", headers=headers)
    await wait_for_job(client, sb_job.json()["id"], headers=headers)

    ep_info = await client.get(f"/api/v1/episodes/{ep_id}", headers=headers)
    panel = ep_info.json()["scenes"][0]["beats"][0]["panels"][0]
    panel_id = panel["id"]

    # 1. Non-existent panel ID -> 404 Not Found
    fake_panel_res = await client.post(
        "/api/v1/panels/non-existent-panel-uuid/inpaint",
        json={"instruction": "Fix background", "mask_base64": "data:image/png;base64,AA=="},
        headers=headers
    )
    assert fake_panel_res.status_code == 404

    # 2. Panel with no generated asset yet -> 400 Bad Request
    no_asset_res = await client.post(
        f"/api/v1/panels/{panel_id}/inpaint",
        json={"instruction": "Fix background", "mask_base64": "data:image/png;base64,AA=="},
        headers=headers
    )
    assert no_asset_res.status_code == 400
    assert "no generated artwork yet" in no_asset_res.json()["detail"].lower()

    # Now generate a draft asset so the panel has active artwork
    gen_job = await client.post(
        f"/api/v1/panels/{panel_id}/generation-jobs",
        json={"stage": "draft"},
        headers=headers
    )
    assert gen_job.status_code == 202
    await wait_for_job(client, gen_job.json()["id"], headers=headers)

    # 3. Corrupted base64 mask string -> 400 Bad Request
    corrupt_mask_res = await client.post(
        f"/api/v1/panels/{panel_id}/inpaint",
        json={"instruction": "Fix background", "mask_base64": "data:image/png;base64,CORRUPTED_NOT_VALID_BASE64_???"},
        headers=headers
    )
    assert corrupt_mask_res.status_code == 400
    assert "invalid base64" in corrupt_mask_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scenario_inpainting_approval_invalidation_lifecycle(client: AsyncClient):
    """
    Scenario 7: Inpainting Invalidation Lifecycle
    Verifies that editing/inpainting an approved panel revokes approval and prevents final generation.
    """
    owner_token = create_access_token("studio_lead", role="owner")
    headers = {"Authorization": f"Bearer {owner_token}"}

    res = await client.post("/api/v1/projects", json={"title": "Approval Invalidation Demo"}, headers=headers)
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "The dragon awakened.", "filename": "dragon.txt"},
        headers=headers
    )
    an_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs", headers=headers)
    await wait_for_job(client, an_job.json()["id"], headers=headers)
    pl_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers)
    await wait_for_job(client, pl_job.json()["id"], headers=headers)
    plans = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans", headers=headers)
    ep_id = plans.json()[0]["episodes"][0]["id"]
    sb_job = await client.post(f"/api/v1/episodes/{ep_id}/storyboard-jobs", headers=headers)
    await wait_for_job(client, sb_job.json()["id"], headers=headers)

    ep_info = await client.get(f"/api/v1/episodes/{ep_id}", headers=headers)
    panel = ep_info.json()["scenes"][0]["beats"][0]["panels"][0]
    panel_id = panel["id"]

    # Generate draft
    gen_job = await client.post(f"/api/v1/panels/{panel_id}/generation-jobs", json={"stage": "draft"}, headers=headers)
    assert gen_job.status_code == 202
    await wait_for_job(client, gen_job.json()["id"], headers=headers)

    # Approve panel as owner/director
    appr = await client.post(
        f"/api/v1/artifacts/{panel_id}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel_id, "artifact_version": 1, "approved_by": "studio_lead"},
        headers=headers
    )
    assert appr.status_code == 201

    # Verify panel is approved
    ep_check = await client.get(f"/api/v1/episodes/{ep_id}", headers=headers)
    assert ep_check.json()["scenes"][0]["beats"][0]["panels"][0]["is_approved"] is True

    # Inpaint panel
    valid_mask = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82").decode('utf-8')
    inpaint_res = await client.post(
        f"/api/v1/panels/{panel_id}/inpaint",
        json={"instruction": "Adjust dragon scales", "mask_base64": valid_mask},
        headers=headers
    )
    assert inpaint_res.status_code == 202
    await wait_for_job(client, inpaint_res.json()["id"], headers=headers)

    # Verify panel approval is invalidated
    ep_check2 = await client.get(f"/api/v1/episodes/{ep_id}", headers=headers)
    assert ep_check2.json()["scenes"][0]["beats"][0]["panels"][0]["is_approved"] is False

    # Attempting final generation must fail due to unapproved state
    fail_final = await client.post(f"/api/v1/panels/{panel_id}/generation-jobs", json={"stage": "final"}, headers=headers)
    assert fail_final.status_code == 400
    assert "approval" in fail_final.json()["detail"].lower()


def test_scenario_lettering_extreme_text_and_fallbacks():
    """
    Scenario 8: Lettering & Typography Edge Cases
    Validates:
    1. Super-long unbroken token wrapping without overflow
    2. Non-ASCII, Unicode, and Korean/Japanese text
    3. Empty text handling
    4. Multi-segment high-density layouts
    5. Unknown bubble type graceful fallback
    """
    # 1. Super-long unbroken word (e.g. 70 characters without spaces)
    long_token = "SUPERLONGUNBROKENTOKENWITHOUTSPACESEXTENDINGBEYONDSTANDARDCHARACTERBOUNDS"
    wrapped_token = wrap_dialogue_text(long_token, max_chars_per_line=25)
    assert len(wrapped_token) >= 3
    assert all(len(line) <= 25 for line in wrapped_token)

    # 2. Asian characters, Unicode, emojis & punctuation
    korean_text = "안녕, 민준! 서울의 밤은 차갑다."
    wrapped_korean = wrap_dialogue_text(korean_text, max_chars_per_line=20)
    assert len(wrapped_korean) >= 1

    # 3. Empty text
    empty_wrap = wrap_dialogue_text("", max_chars_per_line=25)
    assert empty_wrap == [""]

    # 4. Multi-segment composition (8 segments) on PIL canvas
    img = Image.new("RGB", (800, 1600), color=(15, 18, 24))
    segments = [
        DialogueSegment(panel_id="p", order_in_panel=i, speaker_name=f"Char {i}", text_content=f"Line of dialogue #{i}", segment_type="speech_bubble")
        for i in range(1, 7)
    ]
    # Add thought, caption, and unknown fallback style
    segments.append(DialogueSegment(panel_id="p", order_in_panel=7, speaker_name="Narrator", text_content="Unknown voice...", segment_type="alien_whisper"))
    segments.append(DialogueSegment(panel_id="p", order_in_panel=8, speaker_name=None, text_content="BOOM!", segment_type="sfx"))

    composite_dialogue_bubbles(img, segments)
    assert img.size == (800, 1600)
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_scenario_sse_telemetry_streaming(client: AsyncClient):
    """
    Scenario 9: Real-Time SSE Telemetry Endpoint
    Validates streaming progression for an existing job and 404 for invalid job.
    """
    owner_token = create_access_token("stream_user", role="owner")
    headers = {"Authorization": f"Bearer {owner_token}"}

    # 1. 404 for non-existent job
    res_404 = await client.get("/api/v1/jobs/non-existent-uuid/stream", headers=headers)
    assert res_404.status_code == 404

    # 2. Create project for user and stream a real job
    p_res = await client.post("/api/v1/projects", json={"title": "Stream Test Project"}, headers=headers)
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    async with AsyncSessionLocal() as session:
        job = Job(
            project_id=project_id,
            job_type="test_stream",
            status="completed",
            progress_percentage=100,
            stage_description="Telemetry verified",
            payload={},
            result_data={"success": True}
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Connect to stream
    res_stream = await client.get(f"/api/v1/jobs/{job_id}/stream", headers=headers)
    assert res_stream.status_code == 200
    assert "text/event-stream" in res_stream.headers.get("content-type", "")
    assert "data:" in res_stream.text
    assert job_id in res_stream.text


@pytest.mark.asyncio
async def test_scenario_database_asset_uniqueness_and_integrity():
    """
    Scenario 10: Database Asset Uniqueness & Race Prevention
    Validates that:
    1. Multiple assets for the same (panel_id, asset_type) cannot be inserted (violates constraint).
    2. Inserting assets with distinct asset_type (e.g. background vs character_sheet) succeeds.
    """
    async with AsyncSessionLocal() as session:
        panel_id = "test_panel_unique_check"
        
        # 1. Insert first asset
        asset1 = Asset(
            project_id="proj_uniq",
            panel_id=panel_id,
            asset_type="panel_illustration"
        )
        session.add(asset1)
        await session.commit()

        # 2. Attempt to insert a second asset with identical (panel_id, asset_type) -> Must raise IntegrityError
        asset2 = Asset(
            project_id="proj_uniq",
            panel_id=panel_id,
            asset_type="panel_illustration"
        )
        session.add(asset2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # 3. Inserting asset with a different asset_type for same panel -> Succeeds
        asset_bg = Asset(
            project_id="proj_uniq",
            panel_id=panel_id,
            asset_type="background"
        )
        session.add(asset_bg)
        await session.commit()
        assert asset_bg.id is not None


@pytest.mark.asyncio
async def test_scenario_standalone_worker_exception_resilience():
    """
    Scenario 11: Standalone Worker Exception Resilience
    Validates that if a job execution encounters an error, the worker catches it,
    records the failure message on the Job record, and does not crash the process.
    """
    # Create an invalid job with an unknown job type that will fail in dispatcher
    async with AsyncSessionLocal() as session:
        bad_job = Job(
            project_id="fail_test_proj",
            job_type="unsupported_fatal_type",
            status="queued",
            progress_percentage=0,
            stage_description="Queued",
            payload={"invalid": True},
            result_data={}
        )
        session.add(bad_job)
        await session.commit()
        await session.refresh(bad_job)
        bad_job_id = bad_job.id

    # Execute job directly through runner (simulating worker execution)
    await job_runner.execute_job(bad_job_id)

    # Verify job status transitioned to failed with error message recorded
    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == bad_job_id)
        res = await session.execute(stmt)
        j = res.scalar_one()
        assert j.status == "failed"
        assert j.error_message is not None
        assert "unsupported" in j.error_message.lower() or "fatal" in j.error_message.lower() or "error" in j.error_message.lower()
