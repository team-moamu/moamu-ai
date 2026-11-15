import json
from dataclasses import dataclass
from types import MappingProxyType

from moamu_ai.goal_prompt_versions import v1
from moamu_ai.schemas import GoalVerifiabilityRequest


@dataclass(frozen=True)
class GoalPromptDefinition:
    """자유목표 분석 프롬프트 버전을 나타낸다."""

    version: str
    instruction: str


GOAL_PROMPT_DEFINITIONS = MappingProxyType(
    {v1.VERSION: GoalPromptDefinition(version=v1.VERSION, instruction=v1.INSTRUCTION)}
)
DEFAULT_GOAL_PROMPT_VERSION = v1.VERSION


def get_goal_prompt_definition(
    version: str = DEFAULT_GOAL_PROMPT_VERSION,
) -> GoalPromptDefinition:
    """등록된 자유목표 분석 프롬프트를 반환한다.

    Args:
        version: 조회할 프롬프트 버전.

    Returns:
        요청한 버전의 프롬프트.

    Raises:
        ValueError: 지원하지 않는 프롬프트 버전인 경우.
    """
    try:
        return GOAL_PROMPT_DEFINITIONS[version]
    except KeyError as exc:
        supported = ", ".join(GOAL_PROMPT_DEFINITIONS)
        raise ValueError(
            f"Unsupported goal prompt version {version!r}; choose from: {supported}"
        ) from exc


def build_goal_analysis_prompt(
    request: GoalVerifiabilityRequest,
    version: str = DEFAULT_GOAL_PROMPT_VERSION,
) -> str:
    """목표와 선택적 기존 분류 경로를 프롬프트 데이터로 구성한다.

    Args:
        request: 사진 인증 가능 여부를 분석할 목표.
        version: 사용할 프롬프트 버전.

    Returns:
        지시문과 JSON 형식 목표 데이터를 포함하는 프롬프트.
    """
    definition = get_goal_prompt_definition(version)
    payload = {
        "goal": request.goal,
        "categoryPath": (
            request.category_path.model_dump(mode="json")
            if request.category_path is not None
            else None
        ),
    }
    return (
        definition.instruction
        + "\n\nRequest data:\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
