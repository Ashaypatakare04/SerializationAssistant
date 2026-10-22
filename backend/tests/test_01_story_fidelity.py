import pytest
from httpx import AsyncClient
from backend.tests.conftest import wait_for_job

SAMPLE_MANUSCRIPT = """# Chapter 1: The Midnight Meeting

Min-jun adjusted the collar of his trench coat against the heavy rain. 
The streetlight above the alleyway flickered, illuminating the puddle at his feet.

Soo-jin emerged from the doorway of the vintage cafe. "You're seven minutes late," she said.
"The bridge was blocked by police checkpoints," Min-jun whispered, pulling the sealed dossier from inside his jacket.

"Did you read what's inside?" Soo-jin frowned, her knuckles tightening around her umbrella.
"I didn't need to," Min-jun murmured. "Your name is on the second page."
"""

@pytest.mark.asyncio
async def test_01_story_fidelity_preservation(client: AsyncClient):
    # 1. Create Project
    res = await client.post("/api/v1/projects", json={
        "title": "Midnight Meeting Adaptation",
        "description": "Urban mystery vertical webtoon pilot"
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Upload Manuscript
    res = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": SAMPLE_MANUSCRIPT, "filename": "chapter1.md"}
    )
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["extraction_status"] == "extracted"
    assert len(doc_data["sections"]) >= 1

    # 3. Trigger Story Analysis
    job_res = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    assert job_res.status_code == 202
    job_data = await wait_for_job(client, job_res.json()["id"])
    assert job_data["status"] == "completed"

    # 4. Fetch Story Bible
    bible_res = await client.get(f"/api/v1/projects/{project_id}/story-bible")
    assert bible_res.status_code == 200
    bible = bible_res.json()

    # Verify character preservation
    char_names = [c["canonical_name"] for c in bible["characters"]]
    assert "Min-jun" in char_names
    assert "Soo-jin" in char_names

    # Verify events and source locators
    assert len(bible["events"]) >= 2
    for event in bible["events"]:
        assert event["source_locator"] is not None
        assert len(event["summary"]) > 0

    # Verify continuity facts
    assert len(bible["continuity_facts"]) >= 1
    assert any("timeline" in f["category"] or "rule" in f["category"] for f in bible["continuity_facts"])
