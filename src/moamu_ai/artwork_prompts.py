import json
from dataclasses import dataclass
from types import MappingProxyType

from moamu_ai.artwork_prompt_versions import v1
from moamu_ai.schemas import ArtworkGenerationRequest


@dataclass(frozen=True)
class ArtworkPromptDefinition:
    """명화 편집 프롬프트의 버전을 나타낸다."""

    version: str
    instruction: str


ARTWORK_PROMPT_DEFINITIONS = MappingProxyType(
    {
        v1.VERSION: ArtworkPromptDefinition(
            version=v1.VERSION,
            instruction=v1.INSTRUCTION,
        )
    }
)
DEFAULT_ARTWORK_PROMPT_VERSION = v1.VERSION


def get_artwork_prompt_definition(
    version: str = DEFAULT_ARTWORK_PROMPT_VERSION,
) -> ArtworkPromptDefinition:
    """등록된 명화 편집 프롬프트를 반환한다."""
    try:
        return ARTWORK_PROMPT_DEFINITIONS[version]
    except KeyError as exc:
        supported = ", ".join(ARTWORK_PROMPT_DEFINITIONS)
        raise ValueError(
            f"Unsupported artwork prompt version {version!r}; choose from: {supported}"
        ) from exc


def build_artwork_edit_prompt(
    request: ArtworkGenerationRequest,
    version: str = DEFAULT_ARTWORK_PROMPT_VERSION,
) -> str:
    """목표와 사진 기준을 명화 편집 요청 데이터로 구성한다."""
    definition = get_artwork_prompt_definition(version)
    payload = {
        "normalizedGoal": request.normalized_goal,
        "categoryPath": request.category_path.model_dump(mode="json"),
        "conditions": request.conditions,
        "photoGuide": request.photo_guide,
    }
    return (
        definition.instruction
        + "\n\nRequest data (JSON):\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
