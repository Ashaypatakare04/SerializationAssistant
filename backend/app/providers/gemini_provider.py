import json
import httpx
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5 and not self.api_key.startswith("your-gemini"))

    def inspect_capabilities(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "provider_name": "Google Gemini 1.5 Pro / Flash",
            "is_configured": configured,
            "is_real_ai": True,
            "status_message": "Ready" if configured else "Missing or unconfigured GEMINI_API_KEY"
        }

    async def _generate_content_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini provider not configured with API key.")
        
        url = f"{self.base_url}/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.4
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)

    async def analyze_story(self, manuscript_text: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        system = "You are a webtoon adaptation editor. Extract story bible JSON with keys: premise, canonical_characters, major_events, relationships."
        return await self._generate_content_json(manuscript_text[:4000], system)

    async def analyze_style(self, reference_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        system = "Analyze visual manhwa style and return JSON with keys: linework_and_contours, palette_and_colors, shading_and_lighting, background_treatment."
        return await self._generate_content_json(json.dumps(reference_descriptions), system)

    async def propose_adaptation(self, story_bible_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        system = "Propose webtoon episode adaptation breakdown JSON with keys: arcs, episodes."
        return await self._generate_content_json(json.dumps(story_bible_data), system)

    async def generate_storyboard(self, episode_data: Dict[str, Any], story_bible_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        system = "Generate webtoon panels JSON list under key 'panels' with shot_type, camera_angle, character_action, environment_and_background, local_emotion."
        res = await self._generate_content_json(json.dumps({"episode": episode_data, "bible": story_bible_data}), system)
        return res.get("panels", [])
