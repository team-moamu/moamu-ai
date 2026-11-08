from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

from moamu_ai.schemas import ConditionResult, ConditionSnapshot


@dataclass(frozen=True)
class InferenceUsage:
    """모델 이름, 지연 시간, 토큰 사용량을 보관한다."""

    model: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    thinking_tokens: Optional[int] = None


@dataclass(frozen=True)
class InferenceResult:
    """조건별 모델 판정과 추론 사용량을 묶어 반환한다."""

    results: list[ConditionResult]
    usage: InferenceUsage


class PhotoJudge(Protocol):
    """이미지와 인증 조건을 받아 판정하는 모델 인터페이스."""

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        """이미지를 판정해 각 조건에 대한 결과와 사용량을 반환한다."""


JudgeFactory = Callable[[], PhotoJudge]
