from typing import Dict, Any, Tuple
from backend.app.core.config import settings
from backend.app.providers.base import BaseLLMProvider, BaseImageProvider
from backend.app.providers.mock_provider import mock_llm_provider, mock_image_provider
from backend.app.providers.openai_provider import OpenAIProvider
from backend.app.providers.gemini_provider import GeminiProvider
from backend.app.providers.stability_provider import StabilityProvider

class ProviderFactory:
    @staticmethod
    def get_llm_provider(provider_name: str = None) -> BaseLLMProvider:
        name = (provider_name or settings.LLM_PROVIDER).lower()
        if name == "openai":
            p = OpenAIProvider()
            if p.is_configured():
                return p
        elif name == "gemini":
            p = GeminiProvider()
            if p.is_configured():
                return p
        return mock_llm_provider

    @staticmethod
    def get_image_provider(provider_name: str = None) -> BaseImageProvider:
        name = (provider_name or settings.IMAGE_PROVIDER).lower()
        if name == "openai":
            p = OpenAIProvider()
            if p.is_configured():
                return p
        elif name == "stability":
            p = StabilityProvider()
            if p.is_configured():
                return p
        return mock_image_provider

    @classmethod
    def get_all_capabilities(cls) -> Dict[str, Any]:
        return {
            "active_llm_provider": settings.LLM_PROVIDER,
            "active_image_provider": settings.IMAGE_PROVIDER,
            "providers": {
                "mock": mock_image_provider.inspect_capabilities(),
                "openai": OpenAIProvider().inspect_capabilities(),
                "stability": StabilityProvider().inspect_capabilities(),
                "gemini": GeminiProvider().inspect_capabilities()
            }
        }

provider_factory = ProviderFactory()
