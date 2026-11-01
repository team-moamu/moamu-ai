from moamu_ai.config import Settings
from moamu_ai.errors import ProviderConfigurationError
from moamu_ai.providers.base import PhotoJudge
from moamu_ai.providers.gemini import GeminiPhotoJudge
from moamu_ai.providers.ollama import OllamaPhotoJudge


def create_photo_judge(settings: Settings) -> PhotoJudge:
    if settings.ai_provider == "gemini":
        if settings.gemini_token_api_key is None:
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        return GeminiPhotoJudge(
            api_key=settings.gemini_token_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        )
    if settings.ai_provider == "ollama":
        return OllamaPhotoJudge(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        )
    raise ProviderConfigurationError("configured AI provider is not supported")
