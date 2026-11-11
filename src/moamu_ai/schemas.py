from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConditionStatus(str, Enum):
    """인증 조건별 판정 결과 상태."""

    MET = "MET"
    NOT_MET = "NOT_MET"
    UNCERTAIN = "UNCERTAIN"


class ConditionSnapshot(BaseModel):
    """평가 manifest에서 사용하는 조건 정보 모델."""

    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=100)
    condition_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    # 벤치마크 사례 보관용이며 현재 백엔드 조건 테이블과 API 요청에는 없다.
    required: bool | Literal["Y", "N"] = True
    sort_order: int = Field(ge=0)

    @property
    def is_required(self) -> bool:
        """조건이 필수 인증 항목인지 반환한다."""
        return self.required is True or self.required == "Y"


class PhotoVerificationRequest(BaseModel):
    """백엔드가 사진 판정을 요청할 때 사용하는 입력 모델."""

    model_config = ConfigDict(extra="forbid")

    ai_task_id: str = Field(min_length=1, max_length=100)
    verification_id: str = Field(min_length=1, max_length=100)
    image_key: str = Field(min_length=1, max_length=4096)
    conditions: list["VerificationCondition"] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_condition_codes(self):
        """요청 안의 인증 조건 코드가 서로 다른지 확인한다."""
        codes = [item.code for item in self.conditions]
        if len(set(codes)) != len(codes):
            raise ValueError("condition codes must be unique")
        return self


class VerificationCondition(BaseModel):
    """요청에 포함되는 인증 조건 코드와 설명."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)


class ConditionResult(BaseModel):
    """모델이 반환하는 단일 인증 조건 판정."""

    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int
    status: ConditionStatus
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("challenge_condition_id")
    @classmethod
    def validate_positive_condition_id(cls, value: int) -> int:
        """인증 조건 식별자가 양수인지 확인한다."""
        if value < 1:
            raise ValueError("challenge_condition_id must be positive")
        return value


class PhotoVerificationResponse(BaseModel):
    """사진 인증 API의 성공 응답 모델."""

    model_config = ConfigDict(extra="forbid")

    ai_task_id: str = Field(min_length=1, max_length=100)
    verification_id: str = Field(min_length=1, max_length=100)
    processing_status: Literal["SUCCEEDED"]
    checks: list["ConditionCheck"] = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=50)


class ConditionCheck(BaseModel):
    """API 응답에 담기는 조건 코드별 판정 결과."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    status: ConditionStatus
    reason: str = Field(min_length=1, max_length=500)


class ModelJudgmentResponse(BaseModel):
    """판정 모델이 반환해야 하는 JSON 응답 형식."""

    model_config = ConfigDict(extra="forbid")

    results: list[ConditionResult] = Field(min_length=1)


class ApiErrorDetail(BaseModel):
    """API 오류 코드와 사용자에게 전달할 메시지."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)


class PhotoVerificationErrorResponse(BaseModel):
    """사진 인증 API의 오류 응답 모델."""

    model_config = ConfigDict(extra="forbid")

    ai_task_id: Optional[str] = Field(default=None, max_length=100)
    verification_id: Optional[str] = Field(default=None, max_length=100)
    processing_status: Literal["ERROR"]
    error: ApiErrorDetail


class ExpectedConditionResult(BaseModel):
    """평가 데이터에서 정답 상태와 라벨 근거를 보관한다."""

    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int = Field(gt=0)
    status: ConditionStatus
    label_basis: Literal[
        "human_verified_positive",
        "human_verified_negative",
        "manual_review",
    ]


class BenchmarkCase(BaseModel):
    """이미지, 인증 조건, 정답 라벨을 포함하는 평가 사례."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=200)
    goal_template_code: str = Field(min_length=1, max_length=100)
    dataset_name: str = Field(min_length=1, max_length=200)
    dataset_version: str = Field(min_length=1, max_length=100)
    dataset_split: Optional[str] = Field(default=None, max_length=100)
    dataset_image_id: str = Field(min_length=1, max_length=200)
    image_license: str = Field(min_length=1, max_length=500)
    image_source_url: str = Field(default="", max_length=2000)
    split: Literal["dev", "held_out"]
    image_path: str = Field(min_length=1, max_length=4096)
    conditions: list[ConditionSnapshot] = Field(min_length=2, max_length=5)
    expected_results: list[ExpectedConditionResult] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_expected_results(self):
        """정답 조건 ID가 중복되지 않고 사례 조건에 포함되는지 확인한다."""
        condition_ids = {item.challenge_condition_id for item in self.conditions}
        expected_ids = [item.challenge_condition_id for item in self.expected_results]
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("expected result IDs must be unique")
        if not set(expected_ids).issubset(condition_ids):
            raise ValueError("expected result IDs must exist in conditions")
        return self
