from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_story(self, manuscript_text: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts premise, characters, events, continuity facts, relationships."""
        pass

    @abstractmethod
    async def analyze_style(self, reference_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts linework, anatomy, rendering, palette, lighting, composition."""
        pass

    @abstractmethod
    async def propose_adaptation(self, story_bible_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Proposes arcs, episodes, scene breakdowns, beats with emotional progressions."""
        pass

    @abstractmethod
    async def generate_storyboard(self, episode_data: Dict[str, Any], story_bible_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates detailed panel specifications for webtoon adaptation."""
        pass

class BaseImageProvider(ABC):
    @abstractmethod
    async def generate_draft(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Generates a draft thumbnail prioritizing composition and pose."""
        pass

    @abstractmethod
    async def generate_final(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        draft_bytes: Optional[bytes] = None,
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Generates high-fidelity artwork matching style profile and character identity."""
        pass

    @abstractmethod
    async def edit_image(
        self,
        base_image_bytes: bytes,
        instruction: str,
        target_region: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Performs localized correction/inpainting."""
        pass

    @abstractmethod
    def inspect_capabilities(self) -> Dict[str, Any]:
        """Returns provider name, supported aspect ratios, inpainting support, hardware info."""
        pass

    @abstractmethod
    def estimate_cost(self, stage: str, count: int = 1) -> float:
        """Returns estimated USD cost for generation."""
        pass
