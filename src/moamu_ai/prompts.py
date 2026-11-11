import json
from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType

from moamu_ai.prompt_versions import v1, v2, v3, v4
from moamu_ai.schemas import ConditionSnapshot


@dataclass(frozen=True)
class PromptDefinition:
    """판정 프롬프트의 버전별 지시문과 입력 구성 설정."""

    version: str
    instruction: str
    include_condition_metadata: bool = False


PROMPT_DEFINITIONS = MappingProxyType(
    {
        v1.VERSION: PromptDefinition(
            version=v1.VERSION,
            instruction=v1.INSTRUCTION,
            include_condition_metadata=True,
        ),
        v2.VERSION: PromptDefinition(version=v2.VERSION, instruction=v2.INSTRUCTION),
        v3.VERSION: PromptDefinition(version=v3.VERSION, instruction=v3.INSTRUCTION),
        v4.VERSION: PromptDefinition(version=v4.VERSION, instruction=v4.INSTRUCTION),
    }
)
SUPPORTED_PROMPT_VERSIONS = tuple(PROMPT_DEFINITIONS)
DEFAULT_PROMPT_VERSION = v4.VERSION

# Compatibility aliases for existing benchmark and provider imports.
PROMPT_VERSION = DEFAULT_PROMPT_VERSION
VERIFICATION_INSTRUCTION = PROMPT_DEFINITIONS[PROMPT_VERSION].instruction


def get_prompt_definition(version: str = DEFAULT_PROMPT_VERSION) -> PromptDefinition:
    """등록된 프롬프트 버전 정의를 반환한다.

    Args:
        version: 조회할 프롬프트 버전.

    Returns:
        해당 버전의 지시문과 입력 설정.

    Raises:
        ValueError: 지원하지 않는 프롬프트 버전인 경우.
    """
    try:
        return PROMPT_DEFINITIONS[version]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_PROMPT_VERSIONS)
        raise ValueError(
            f"Unsupported prompt version {version!r}; choose from: {supported}"
        ) from exc


def build_verification_prompt(
    conditions: Iterable[ConditionSnapshot],
    version: str = DEFAULT_PROMPT_VERSION,
) -> str:
    """조건 목록을 선택한 프롬프트 버전의 입력 문자열로 만든다.

    Args:
        conditions: 모델에 전달할 인증 조건 목록.
        version: 사용할 프롬프트 버전.

    Returns:
        지시문과 직렬화한 조건을 포함하는 프롬프트.

    Raises:
        ValueError: 등록되지 않은 프롬프트 버전을 지정한 경우.
    """
    definition = get_prompt_definition(version)
    if definition.include_condition_metadata:
        condition_data = [condition.model_dump(mode="json") for condition in conditions]
    else:
        condition_data = [
            {
                "challenge_condition_id": condition.challenge_condition_id,
                "description": condition.description,
            }
            for condition in conditions
        ]
    return (
        definition.instruction
        + "\n\nConditions:\n"
        + json.dumps(condition_data, ensure_ascii=False, separators=(",", ":"))
    )
