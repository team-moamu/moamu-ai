from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

from moamu_ai.schemas import (
    ArtworkGenerationRequest,
    ConditionResult,
    ConditionSnapshot,
    GoalAnalysisOutput,
    GoalVerifiabilityRequest,
)


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


@dataclass(frozen=True)
class ArtworkEditResult:
    """명화 편집 결과 이미지와 공급자 정보를 보관한다."""

    image_bytes: bytes
    content_type: str
    model: str
    latency_ms: float


class PhotoJudge(Protocol):
    """이미지와 인증 조건을 받아 판정하는 모델 인터페이스."""

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        """이미지를 판정해 각 조건에 대한 결과와 사용량을 반환한다."""


class GoalAnalyzer(Protocol):
    """자유목표의 사진 인증 가능성을 분석하는 모델 인터페이스."""

    def analyze(self, request: GoalVerifiabilityRequest) -> GoalAnalysisOutput:
        """목표 분석 결과를 반환한다."""


class ArtworkEditor(Protocol):
    """원본 명화와 도전 정보를 받아 편집 이미지를 만드는 공급자 인터페이스."""

    def edit(self, image_path: Path, request: ArtworkGenerationRequest) -> ArtworkEditResult:
        """원본 명화를 목표와 인증 기준에 맞게 편집한다."""


JudgeFactory = Callable[[], PhotoJudge]
