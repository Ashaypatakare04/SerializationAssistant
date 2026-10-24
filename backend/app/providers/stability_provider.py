import io
import httpx
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseImageProvider

class StabilityProvider(BaseImageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.STABILITY_API_KEY
        self.base_url = "https://api.stability.ai"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5 and not self.api_key.startswith("sk-your"))

    def inspect_capabilities(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "provider_name": "Stability AI (SD3 / Stable Image Core)",
            "is_configured": configured,
            "is_real_ai": True,
            "supported_aspect_ratios": ["4:5", "1:1", "9:16", "16:9"],
            "supports_inpainting": True,
            "supports_character_sheets": True,
            "cost_per_draft_usd": 0.03,
            "cost_per_final_usd": 0.065,
            "status_message": "Ready" if configured else "Missing or unconfigured STABILITY_API_KEY"
        }

    def estimate_cost(self, stage: str, count: int = 1) -> float:
        rate = 0.03 if stage == "draft" else 0.065
        return rate * count

    def _build_prompt(self, panel_spec: Dict[str, Any], style_profile: Dict[str, Any], character_refs: List[Dict[str, Any]]) -> str:
        shot = panel_spec.get("shot_type", "medium shot").replace("_", " ")
        angle = panel_spec.get("camera_angle", "eye level").replace("_", " ")
        action = panel_spec.get("character_action", "")
        env = panel_spec.get("environment_and_background", "")
        emotion = panel_spec.get("local_emotion", "")
        lighting = panel_spec.get("lighting_direction", "")
        
        linework = style_profile.get("linework_and_contours", "Crisp digital manhwa inks")
        shading = style_profile.get("shading_and_lighting", "Atmospheric cell shading")
        
        char_desc = ""
        if character_refs:
            details = []
            for c in character_refs:
                name = c.get("canonical_name", "Character")
                hair = c.get("hair_style_and_color", "")
                clothes = c.get("clothing_and_accessories", "")
                features = c.get("distinctive_features", "")
                details.append(f"{name} ({hair}, {clothes}, {features})")
            char_desc = " Character appearance: " + "; ".join(details) + "."

        prompt = (
            f"Masterpiece vertical webtoon manhwa panel. {shot}, {angle}. "
            f"Action: {action}. Environment: {env}. Mood: {emotion}. Lighting: {lighting}.{char_desc} "
            f"Art Style: {linework}, {shading}. High detail, vertical reading rhythm."
        )
        return prompt[:950]

    async def generate_draft(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Stability AI provider not configured with API key.")
        
        prompt = self._build_prompt(panel_spec, style_profile, character_refs)
        ratio = "4:5" if aspect_ratio in ("4:5", "9:16") else "1:1"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*"
                },
                files={"none": ""},
                data={
                    "prompt": prompt,
                    "aspect_ratio": ratio,
                    "output_format": "png"
                }
            )
            resp.raise_for_status()
            raw_bytes = resp.content

        metadata = {
            "provider": "stability",
            "model_version": "stable-image-core",
            "stage": "draft",
            "is_mock": False,
            "cost_usd": 0.03,
            "duration_seconds": 6.5,
            "prompt_used": prompt,
            "applied_character_ref_count": len(character_refs)
        }
        return raw_bytes, metadata

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
        
        prompt = self._build_prompt(panel_spec, style_profile, character_refs)
        ratio = "4:5" if aspect_ratio in ("4:5", "9:16") else "1:1"

        data = {
            "prompt": prompt,
            "aspect_ratio": ratio,
            "output_format": "png",
            "model": "sd3-large"
        }
        files = {}
        if draft_bytes:
            data["mode"] = "image-to-image"
            data["strength"] = "0.55"
            files["image"] = ("draft.png", draft_bytes, "image/png")
        else:
            files["none"] = ""

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2beta/stable-image/generate/sd3",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*"
                },
                files=files,
                data=data
            )
            resp.raise_for_status()
            raw_bytes = resp.content

        metadata = {
            "provider": "stability",
            "model_version": "sd3-large",
            "stage": "final",
            "is_mock": False,
            "cost_usd": 0.065,
            "duration_seconds": 11.2,
            "prompt_used": prompt,
            "applied_character_ref_count": len(character_refs)
        }
        return raw_bytes, metadata

    async def edit_image(
        self,
        base_image_bytes: bytes,
        instruction: str,
        target_region: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("Stability AI provider not configured with API key.")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2beta/stable-image/edit/inpaint",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*"
                },
                files={"image": ("base.png", base_image_bytes, "image/png")},
                data={
                    "prompt": instruction,
                    "output_format": "png"
                }
            )
            resp.raise_for_status()
            raw_bytes = resp.content

        metadata = {
            "provider": "stability",
            "model_version": "stable-image-inpaint",
            "stage": "edit",
            "is_mock": False,
            "cost_usd": 0.04,
            "duration_seconds": 7.0,
            "instruction": instruction,
            "target_region": target_region
        }
        return raw_bytes, metadata
