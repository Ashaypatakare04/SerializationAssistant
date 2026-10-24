import io
import json
import base64
import httpx
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseLLMProvider, BaseImageProvider

class OpenAIProvider(BaseLLMProvider, BaseImageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5 and not self.api_key.startswith("sk-your"))

    def inspect_capabilities(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "provider_name": "OpenAI (GPT-4o & DALL-E 3)",
            "is_configured": configured,
            "is_real_ai": True,
            "supported_aspect_ratios": ["1024x1024", "1024x1792", "1792x1024"],
            "supports_inpainting": False,
            "supports_character_sheets": False,
            "cost_per_draft_usd": 0.04,
            "cost_per_final_usd": 0.08,
            "status_message": "Ready" if configured else "Missing or unconfigured OPENAI_API_KEY"
        }

    def estimate_cost(self, stage: str, count: int = 1) -> float:
        rate = 0.04 if stage == "draft" else 0.08
        return rate * count

    def _build_image_prompt(self, panel_spec: Dict[str, Any], style_profile: Dict[str, Any], character_refs: List[Dict[str, Any]]) -> str:
        shot = panel_spec.get("shot_type", "medium shot").replace("_", " ")
        angle = panel_spec.get("camera_angle", "eye level").replace("_", " ")
        action = panel_spec.get("character_action", "")
        env = panel_spec.get("environment_and_background", "")
        emotion = panel_spec.get("local_emotion", "")
        lighting = panel_spec.get("lighting_direction", "")
        
        linework = style_profile.get("linework_and_contours", "Clean manhwa ink lines")
        shading = style_profile.get("shading_and_lighting", "Cell shading with rim lights")
        
        char_desc = ""
        if character_refs:
            details = []
            for c in character_refs:
                name = c.get("canonical_name", "Character")
                hair = c.get("hair_style_and_color", "")
                clothes = c.get("clothing_and_accessories", "")
                features = c.get("distinctive_features", "")
                details.append(f"{name} ({hair}, wearing {clothes}, {features})")
            char_desc = " Featuring characters: " + "; ".join(details) + "."

        prompt = (
            f"Art-directed vertical manhwa webtoon panel illustration. {shot}, {angle}. "
            f"Scene action: {action}. Setting: {env}. Emotion/Atmosphere: {emotion}. "
            f"Lighting: {lighting}.{char_desc} "
            f"Style: {linework}, {shading}. Professional vertical webtoon digital art, high aesthetic quality, masterpiece."
        )
        return prompt[:950]

    async def analyze_story(self, manuscript_text: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        system_prompt = (
            "You are a master story editor adapting literary manuscripts into vertical webtoon story bibles. "
            "Output JSON with keys: premise, canonical_characters, major_events, relationships, continuity_rules."
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Extract story bible from manuscript:\n\n{manuscript_text[:4000]}"}
                    ],
                    "response_format": {"type": "json_object"}
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return json.loads(data["choices"][0]["message"]["content"])

    async def analyze_style(self, reference_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        system_prompt = (
            "Analyze artistic style properties from reference descriptions. "
            "Output JSON with keys: linework_and_contours, anatomy_and_proportions, facial_features_and_expressions, "
            "palette_and_colors, shading_and_lighting, texture_and_rendering, background_treatment, degree_of_stylization."
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Reference descriptions:\n{json.dumps(reference_descriptions)}"}
                    ],
                    "response_format": {"type": "json_object"}
                }
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])

    async def propose_adaptation(self, story_bible_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "Propose webtoon adaptation arc and episodes in JSON format."},
                        {"role": "user", "content": json.dumps(story_bible_data)}
                    ],
                    "response_format": {"type": "json_object"}
                }
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])

    async def generate_storyboard(self, episode_data: Dict[str, Any], story_bible_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "Generate sequential webtoon panels list in JSON with key 'panels'."},
                        {"role": "user", "content": json.dumps({"episode": episode_data, "bible": story_bible_data})}
                    ],
                    "response_format": {"type": "json_object"}
                }
            )
            resp.raise_for_status()
            result = json.loads(resp.json()["choices"][0]["message"]["content"])
            return result.get("panels", [])

    async def generate_draft(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        prompt = self._build_image_prompt(panel_spec, style_profile, character_refs)
        size = "1024x1792" if aspect_ratio in ("4:5", "9:16") else "1024x1024"

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": "standard",
                    "response_format": "b64_json"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            b64_data = data["data"][0]["b64_json"]
            raw_bytes = base64.b64decode(b64_data)

        metadata = {
            "provider": "openai",
            "model_version": "dall-e-3",
            "stage": "draft",
            "is_mock": False,
            "cost_usd": 0.04,
            "duration_seconds": 12.0,
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
            raise RuntimeError("OpenAI provider not configured with API key.")
        
        prompt = self._build_image_prompt(panel_spec, style_profile, character_refs)
        size = "1024x1792" if aspect_ratio in ("4:5", "9:16") else "1024x1024"

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": "hd",
                    "response_format": "b64_json"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            b64_data = data["data"][0]["b64_json"]
            raw_bytes = base64.b64decode(b64_data)

        metadata = {
            "provider": "openai",
            "model_version": "dall-e-3-hd",
            "stage": "final",
            "is_mock": False,
            "cost_usd": 0.08,
            "duration_seconds": 18.0,
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
            raise RuntimeError("OpenAI provider not configured with API key.")
        raise NotImplementedError("OpenAI DALL-E 3 does not support localized inpainting or editing. Use Stability AI for inpainting.")
