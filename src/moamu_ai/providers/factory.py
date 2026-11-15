from moamu_ai.config import Settings
from moamu_ai.errors import ProviderConfigurationError
from moamu_ai.providers.base import GoalAnalyzer, PhotoJudge
from moamu_ai.providers.gemini import GeminiGoalAnalyzer, GeminiPhotoJudge
from moamu_ai.providers.ollama import OllamaGoalAnalyzer, OllamaPhotoJudge


def create_photo_judge(settings: Settings) -> PhotoJudge:
    """설정된 공급자에 맞는 사진 판정기를 생성한다.

    Args:
        settings: 공급자, 모델, 인증 정보가 담긴 앱 설정.

    Returns:
        Gemini 또는 Ollama 판정기.

    Raises:
        ProviderConfigurationError: 인증 키가 없거나 공급자를 지원하지 않는 경우.
    """
    if settings.ai_provider == "gemini":
        if settings.gemini_token_api_key is None:
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        return GeminiPhotoJudge(
            api_key=settings.gemini_token_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
            prompt_version=settings.ai_prompt_version,
            thinking_level=settings.gemini_thinking_level,
        )
    if settings.ai_provider == "ollama":
        return OllamaPhotoJudge(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
            prompt_version=settings.ai_prompt_version,
        )
    raise ProviderConfigurationError("configured AI provider is not supported")


def create_goal_analyzer(settings: Settings) -> GoalAnalyzer:
    """설정된 공급자에 맞는 자유목표 분석기를 생성한다.

    Args:
        settings: 공급자, 모델, 인증 정보가 담긴 앱 설정.

    Returns:
        Gemini 또는 Ollama 분석기.

    Raises:
        ProviderConfigurationError: Gemini 인증 키가 없거나 공급자가 올바르지 않은 경우.
    """
    if settings.ai_provider == "gemini":
        if settings.gemini_token_api_key is None:
            raise ProviderConfigurationError("GEMINI_TOKEN_API_KEY is not configured")
        return GeminiGoalAnalyzer(
            api_key=settings.gemini_token_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
            prompt_version=settings.ai_goal_prompt_version,
            thinking_level=settings.gemini_thinking_level,
        )
    if settings.ai_provider == "ollama":
        return OllamaGoalAnalyzer(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ai_provider_timeout_seconds,
            prompt_version=settings.ai_goal_prompt_version,
        )
    raise ProviderConfigurationError("configured AI provider is not supported")
