from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConditionStatus(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    UNCERTAIN = "UNCERTAIN"


class ConditionSnapshot(BaseModel):
    """Evaluation manifest metadata, separate from the runtime API request."""

    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=100)
    condition_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    # These fields are retained for benchmark cases; the current backend
    # condition table and runtime request do not provide this metadata.
    required: bool | Literal["Y", "N"] = True
    sort_order: int = Field(ge=0)

    @property
    def is_required(self) -> bool:
        return self.required is True or self.required == "Y"


class PhotoVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_task_id: str = Field(min_length=1, max_length=100)
    verification_id: str = Field(min_length=1, max_length=100)
    image_key: str = Field(min_length=1, max_length=4096)
    conditions: list["VerificationCondition"] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_condition_codes(self):
        codes = [item.code for item in self.conditions]
        if len(set(codes)) != len(codes):
            raise ValueError("condition codes must be unique")
        return self


class VerificationCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)


class ConditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int
    status: ConditionStatus
    reason: str = Field(max_length=500)

    @field_validator("challenge_condition_id")
    @classmethod
    def validate_positive_condition_id(cls, value: int) -> int:
        if value < 1:
            raise ValueError("challenge_condition_id must be positive")
        return value


class PhotoVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_task_id: str = Field(min_length=1, max_length=100)
    verification_id: str = Field(min_length=1, max_length=100)
    processing_status: Literal["SUCCEEDED"]
    checks: list["ConditionCheck"] = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=50)


class ConditionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    status: ConditionStatus
    reason: str = Field(max_length=500)


class ModelJudgmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ConditionResult] = Field(min_length=1)


class ApiErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)


class PhotoVerificationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_task_id: Optional[str] = Field(default=None, max_length=100)
    verification_id: Optional[str] = Field(default=None, max_length=100)
    processing_status: Literal["ERROR"]
    error: ApiErrorDetail


class ExpectedConditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int = Field(gt=0)
    status: ConditionStatus
    label_basis: Literal[
        "human_verified_positive",
        "human_verified_negative",
        "manual_review",
    ]


class BenchmarkCase(BaseModel):
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
        condition_ids = {item.challenge_condition_id for item in self.conditions}
        expected_ids = [item.challenge_condition_id for item in self.expected_results]
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("expected result IDs must be unique")
        if not set(expected_ids).issubset(condition_ids):
            raise ValueError("expected result IDs must exist in conditions")
        return self
