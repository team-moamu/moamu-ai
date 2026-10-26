from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

from moamu_ai.schemas import ConditionResult, ConditionSnapshot


@dataclass(frozen=True)
class InferenceUsage:
    model: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass(frozen=True)
class InferenceResult:
    results: list[ConditionResult]
    usage: InferenceUsage


class PhotoJudge(Protocol):
    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        """Return exactly one status per supplied condition."""


JudgeFactory = Callable[[], PhotoJudge]
