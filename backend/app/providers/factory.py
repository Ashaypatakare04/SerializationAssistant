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
        if name == "mock":
            return mock_llm_provider
        elif name == "openai":
            p = OpenAIProvider()
            if not p.is_configured():
                raise RuntimeError("OpenAI provider requested but OPENAI_API_KEY is not configured.")
            return p
        elif name == "gemini":
            p = GeminiProvider()
            if not p.is_configured():
                raise RuntimeError("Gemini provider requested but GEMINI_API_KEY is not configured.")
            return p
        raise ValueError(f"Unknown LLM provider requested: '{name}'. Available: mock, openai, gemini.")

    @staticmethod
    def get_image_provider(provider_name: str = None) -> BaseImageProvider:
        name = (provider_name or settings.IMAGE_PROVIDER).lower()
        if name == "mock":
            return mock_image_provider
        elif name == "openai":
            p = OpenAIProvider()
            if not p.is_configured():
                raise RuntimeError("OpenAI image provider requested but OPENAI_API_KEY is not configured.")
            return p
        elif name == "stability":
            p = StabilityProvider()
            if not p.is_configured():
                raise RuntimeError("Stability AI provider requested but STABILITY_API_KEY is not configured.")
            return p
        raise ValueError(f"Unknown Image provider requested: '{name}'. Available: mock, openai, stability.")


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
