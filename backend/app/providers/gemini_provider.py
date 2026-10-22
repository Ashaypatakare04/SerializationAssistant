import httpx
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def inspect_capabilities(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "provider_name": "Google Gemini 1.5 Pro / Flash",
            "is_configured": configured,
            "is_real_ai": True,
            "status_message": "Ready" if configured else "Missing GEMINI_API_KEY environment variable"
        }

    async def analyze_story(self, manuscript_text: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini provider not configured with API key.")
        raise NotImplementedError("Live Gemini calls require GEMINI_API_KEY.")

    async def analyze_style(self, reference_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini provider not configured with API key.")
        raise NotImplementedError("Live Gemini calls require GEMINI_API_KEY.")

    async def propose_adaptation(self, story_bible_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini provider not configured with API key.")
        raise NotImplementedError("Live Gemini calls require GEMINI_API_KEY.")

    async def generate_storyboard(self, episode_data: Dict[str, Any], story_bible_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Gemini provider not configured with API key.")
        raise NotImplementedError("Live Gemini calls require GEMINI_API_KEY.")
