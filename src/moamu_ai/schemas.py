from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConditionStatus(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    UNCERTAIN = "UNCERTAIN"


class ConditionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=100)
    condition_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    required: bool = True
    sort_order: int = Field(ge=0)


class PhotoVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_path: str = Field(min_length=1, max_length=4096)
    conditions: list[ConditionSnapshot] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def validate_condition_ids(self):
        identifiers = [item.challenge_condition_id for item in self.conditions]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("challenge_condition_id values must be unique")
        if sum(1 for item in self.conditions if item.required) < 2:
            raise ValueError("at least two conditions must be required")
        return self


class ConditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_condition_id: int
    status: ConditionStatus

    @field_validator("challenge_condition_id")
    @classmethod
    def validate_positive_condition_id(cls, value: int) -> int:
        if value < 1:
            raise ValueError("challenge_condition_id must be positive")
        return value


class PhotoVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ConditionResult] = Field(min_length=2, max_length=3)


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
    conditions: list[ConditionSnapshot] = Field(min_length=2, max_length=3)
    expected_results: list[ExpectedConditionResult] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_expected_results(self):
        condition_ids = {item.challenge_condition_id for item in self.conditions}
        expected_ids = [item.challenge_condition_id for item in self.expected_results]
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("expected result IDs must be unique")
        if not set(expected_ids).issubset(condition_ids):
            raise ValueError("expected result IDs must exist in conditions")
        return self
