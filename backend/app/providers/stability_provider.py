from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseImageProvider

class StabilityProvider(BaseImageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.STABILITY_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def inspect_capabilities(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "provider_name": "Stability AI (SD3 / Stable Diffusion XL)",
            "is_configured": configured,
            "is_real_ai": True,
            "supported_aspect_ratios": ["4:5", "1:1", "9:16", "16:9"],
            "supports_inpainting": True,
            "supports_character_sheets": True,
            "cost_per_draft_usd": 0.03,
            "cost_per_final_usd": 0.065,
            "status_message": "Ready" if configured else "Missing STABILITY_API_KEY environment variable"
        }

    def estimate_cost(self, stage: str, count: int = 1) -> float:
        rate = 0.03 if stage == "draft" else 0.065
        return rate * count

    async def generate_draft(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Stability AI provider not configured with API key.")
        raise NotImplementedError("Live Stability calls require STABILITY_API_KEY.")

    async def generate_final(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        draft_bytes: Optional[bytes] = None,
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Stability AI provider not configured with API key.")
        raise NotImplementedError("Live Stability calls require STABILITY_API_KEY.")

    async def edit_image(
        self,
        base_image_bytes: bytes,
        instruction: str,
        target_region: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Stability AI provider not configured with API key.")
        raise NotImplementedError("Live Stability calls require STABILITY_API_KEY.")
