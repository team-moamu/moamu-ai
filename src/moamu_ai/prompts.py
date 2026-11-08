import json
from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType

from moamu_ai.prompt_versions import v2, v3
from moamu_ai.schemas import ConditionSnapshot


@dataclass(frozen=True)
class PromptDefinition:
    version: str
    instruction: str


PROMPT_DEFINITIONS = MappingProxyType(
    {
        v2.VERSION: PromptDefinition(version=v2.VERSION, instruction=v2.INSTRUCTION),
        v3.VERSION: PromptDefinition(version=v3.VERSION, instruction=v3.INSTRUCTION),
    }
)
PROMPT_VERSION = v3.VERSION
VERIFICATION_INSTRUCTION = PROMPT_DEFINITIONS[PROMPT_VERSION].instruction


def get_prompt_definition(version: str = PROMPT_VERSION) -> PromptDefinition:
    try:
        return PROMPT_DEFINITIONS[version]
    except KeyError as exc:
        supported = ", ".join(PROMPT_DEFINITIONS)
        raise ValueError(
            f"Unsupported prompt version {version!r}; choose from: {supported}"
        ) from exc


def build_verification_prompt(
    conditions: Iterable[ConditionSnapshot],
    version: str = PROMPT_VERSION,
) -> str:
    condition_data = [
        {
            "challenge_condition_id": item.challenge_condition_id,
            "code": item.code,
            "description": item.description,
        }
        for item in conditions
    ]
    return (
        get_prompt_definition(version).instruction
        + "\n\nConditions:\n"
        + json.dumps(condition_data, ensure_ascii=False, separators=(",", ":"))
    )
