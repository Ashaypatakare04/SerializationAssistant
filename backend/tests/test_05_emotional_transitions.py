import pytest
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_05_emotional_transitions_beat_level(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Emotional Transitions Test"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun laughed nervously. Then the smile vanished as Soo-jin revealed the grave truth.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    plan = plans_res.json()[0]
    episode_id = plan["episodes"][0]["id"]

    ep_res = await client.get(f"/api/v1/episodes/{episode_id}")
    episode = ep_res.json()
    beats = episode["scenes"][0]["beats"]

    assert len(beats) >= 2
    beat1 = beats[0]
    beat2 = beats[1]

    # Beat 1 has comedic/awkward tone
    assert "awkward" in beat1["dominant_emotion"].lower() or "comedic" in str(beat1["secondary_emotion"]).lower()
    # Beat 2 transitions to serious tension
    assert "tension" in beat2["dominant_emotion"].lower() or "serious" in str(beat2["secondary_emotion"]).lower()
    # Intensity shifts
    assert beat2["emotional_intensity"] > beat1["emotional_intensity"]
    # Global story bible version remains constant
    assert plan["story_bible_version"] == 1
