import base64
import io
import pytest
from PIL import Image
from sqlalchemy import select
from backend.app.export.webtoon_exporter import wrap_dialogue_text, composite_dialogue_bubbles, webtoon_exporter
from backend.app.models.adaptation import DialogueSegment, Panel, Episode, Scene, Beat, AdaptationPlan
from backend.app.models.asset import Asset, AssetVersion
from backend.app.models.style import CharacterReference, ReferenceAsset
from backend.app.models.bible import Character, CharacterVersion
from backend.app.providers.mock_provider import MockImageProvider
from backend.app.providers.stability_provider import StabilityProvider
from backend.app.providers.openai_provider import OpenAIProvider
from backend.app.db.session import AsyncSessionLocal


def test_wrap_dialogue_text():
    short_text = "Hello Min-jun!"
    wrapped_short = wrap_dialogue_text(short_text, max_chars_per_line=30)
    assert len(wrapped_short) == 1
    assert wrapped_short[0] == "Hello Min-jun!"

    long_text = "We cannot afford to let the syndicate discover what is hidden in the southern district vault before midnight!"
    wrapped_long = wrap_dialogue_text(long_text, max_chars_per_line=28)
    assert len(wrapped_long) >= 3
    for line in wrapped_long:
        assert len(line) <= 35


def test_composite_dialogue_bubbles():
    img = Image.new("RGB", (800, 1000), color=(20, 24, 30))
    d1 = DialogueSegment(
        panel_id="p1",
        order_in_panel=1,
        speaker_name="Min-jun",
        text_content="Stay alert. The rain is masking their footsteps.",
        segment_type="speech_bubble"
    )
    d2 = DialogueSegment(
        panel_id="p1",
        order_in_panel=2,
        speaker_name="Min-jun",
        text_content="If they find the ledger, it's over for all of us.",
        segment_type="thought"
    )
    d3 = DialogueSegment(
        panel_id="p1",
        order_in_panel=3,
        speaker_name=None,
        text_content="Seoul, District 4. Midnight.",
        segment_type="caption"
    )
    d4 = DialogueSegment(
        panel_id="p1",
        order_in_panel=4,
        speaker_name=None,
        text_content="CRASH!",
        segment_type="sfx"
    )

    composite_dialogue_bubbles(img, [d1, d2, d3, d4], panel_top_y=10)
    assert img.size == (800, 1000)
    # The first speech bubble is drawn at (30, 34). Check that balloon pixels are rendered
    balloon_sample = img.getpixel((50, 45))
    assert balloon_sample == (255, 255, 255)


@pytest.mark.asyncio
async def test_mock_image_provider_with_character_references_and_mask():
    provider = MockImageProvider()
    
    # 1. Test draft generation with character references
    char_refs = [{
        "canonical_name": "Min-jun",
        "hair": "Jet black undercut",
        "clothing": "Charcoal trench coat",
        "appearance": "Tall, sharp jawline",
        "distinctive_features": "Faint scar over left eyebrow",
        "primary_reference_bytes": None
    }]
    raw_draft, meta = await provider.generate_draft(
        panel_spec={"shot_type": "close_up", "camera_angle": "eye_level", "character_action": "Speaking urgently", "local_emotion": "Tense"},
        style_profile={"linework_and_contours": "Crisp manhwa inks", "palette_and_colors": ["#1A1D24", "#2E3A4D"]},
        character_refs=char_refs
    )
    assert len(raw_draft) > 1000
    assert meta["applied_character_ref_count"] == 1

    # 2. Test edit_image with localized binary mask
    mask_img = Image.new("L", (800, 1000), color=0)
    # Paint white rectangle in center
    for x in range(300, 500):
        for y in range(400, 600):
            mask_img.putpixel((x, y), 255)
    mask_buf = io.BytesIO()
    mask_img.save(mask_buf, format="PNG")
    mask_bytes = mask_buf.getvalue()

    edited_bytes, edit_meta = await provider.edit_image(
        base_image_bytes=raw_draft,
        instruction="Refine eyes and remove extra shading",
        mask_bytes=mask_bytes
    )
    assert len(edited_bytes) > 1000
    assert edit_meta["has_mask"] is True


def test_provider_prompt_character_conditioning():
    stab = StabilityProvider()
    panel_spec = {
        "shot_type": "medium_shot",
        "camera_angle": "low_angle",
        "character_action": "Drawing his dagger",
        "environment_and_background": "Rainy alleyway",
        "local_emotion": "Determination",
        "lighting_direction": "Neon backlight"
    }
    style_profile = {"linework_and_contours": "Bold digital ink", "shading_and_lighting": "Dynamic rim light"}
    char_refs = [{
        "canonical_name": "Min-jun",
        "hair": "Dark tousled hair",
        "clothing": "Leather jacket",
        "appearance": "Athletic build",
        "distinctive_features": "Silver earring"
    }]

    prompt = stab._build_prompt(panel_spec, style_profile, char_refs)
    assert "Min-jun" in prompt
    assert "Dark tousled hair" in prompt
    assert "Leather jacket" in prompt

    openai_p = OpenAIProvider()
    oai_prompt = openai_p._build_image_prompt(panel_spec, style_profile, char_refs)
    assert "Min-jun" in oai_prompt
    assert "Dark tousled hair" in oai_prompt


@pytest.mark.asyncio
async def test_panel_inpaint_endpoint_with_mask(client):
    from backend.tests.conftest import wait_for_job

    # 1. Setup project up to storyboard
    res = await client.post("/api/v1/projects", json={"title": "Inpaint Mask Pipeline Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun paused at the entrance.", "filename": "story.txt"}
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

    # 2. Generate initial draft
    gen_res = await client.post(
        f"/api/v1/panels/{panel['id']}/generation-jobs",
        json={"stage": "draft"}
    )
    assert gen_res.status_code == 202
    await wait_for_job(client, gen_res.json()["id"])

    # 3. Approve panel
    await client.post(
        f"/api/v1/artifacts/{panel['id']}/approvals",
        json={"artifact_type": "panel", "artifact_id": panel["id"], "artifact_version": panel["version"], "approved_by": "creator"}
    )

    # 4. Inpaint with custom base64 mask
    dummy_mask = Image.new("L", (100, 100), color=255)
    buf = io.BytesIO()
    dummy_mask.save(buf, format="PNG")
    mask_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    inpaint_res = await client.post(
        f"/api/v1/panels/{panel['id']}/inpaint",
        json={
            "instruction": "Fix left hand fingers and remove blur",
            "target_region": "face",
            "mask_base64": mask_b64
        }
    )
    assert inpaint_res.status_code == 202
    job_id = inpaint_res.json()["id"]
    finished = await wait_for_job(client, job_id)
    assert finished["status"] == "completed"

    # 5. Check panel approval was invalidated upon inpainting
    check_res = await client.get(f"/api/v1/episodes/{episode_id}")
    updated_panel = check_res.json()["scenes"][0]["beats"][0]["panels"][0]
    assert updated_panel["is_approved"] is False

    # 6. Verify edited asset version was created
    assets_res = await client.get(f"/api/v1/panels/{panel['id']}/assets")
    assert len(assets_res.json()) > 0
    versions = assets_res.json()[0]["versions"]
    assert any(v["stage"] == "edit" for v in versions)

