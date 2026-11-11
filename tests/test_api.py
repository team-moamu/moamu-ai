from pathlib import Path

from fastapi.testclient import TestClient

from moamu_ai.app import create_app
from moamu_ai.config import Settings
from moamu_ai.image_sources import LocalImageStore
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionResult, ConditionStatus


class StaticJudge:
    """API 테스트에서 고정 판정 결과를 제공하는 대역."""

    def evaluate(self, image_path: Path, conditions):
        """요청 조건마다 지정된 테스트 판정을 반환한다."""
        return InferenceResult(
            results=[
                ConditionResult(
                    challenge_condition_id=condition.challenge_condition_id,
                    status=(
                        ConditionStatus.MET
                        if condition.challenge_condition_id == 1
                        else ConditionStatus.UNCERTAIN
                    ),
                    reason="사진에서 조건을 확인했습니다.",
                )
                for condition in conditions
            ],
            usage=InferenceUsage(model="gemini-3.5-flash-lite", latency_ms=0),
        )


def payload(image_key: str = "proof.jpg"):
    """사진 인증 API 테스트용 요청 데이터를 만든다."""
    return {
        "ai_task_id": "task-1",
        "verification_id": "verification-1",
        "image_key": image_key,
        "conditions": [
            {"code": "C1", "description": "A bottle is visible"},
            {"code": "C2", "description": "A hand is holding the bottle"},
        ],
    }


def test_endpoint_returns_backend_contract_with_condition_reasons(tmp_path: Path):
    """정상 요청이 백엔드 성공 응답 형식으로 반환되는지 확인한다."""
    image_root = tmp_path / "images"
    image_root.mkdir()
    (image_root / "proof.jpg").write_bytes(b"test")
    app = create_app(
        settings=Settings(_env_file=None, ai_image_root=image_root),
        judge=StaticJudge(),
        image_store=LocalImageStore(image_root),
    )

    response = TestClient(app).post("/internal/photo-verifications", json=payload())

    assert response.status_code == 200
    assert response.json() == {
        "ai_task_id": "task-1",
        "verification_id": "verification-1",
        "processing_status": "SUCCEEDED",
        "checks": [
            {"code": "C1", "status": "MET", "reason": "사진에서 조건을 확인했습니다."},
            {
                "code": "C2",
                "status": "UNCERTAIN",
                "reason": "사진에서 조건을 확인했습니다.",
            },
        ],
        "model_version": "photo-verifier-v1",
    }


def test_endpoint_returns_error_envelope_for_invalid_request():
    """잘못된 요청이 공통 오류 응답으로 변환되는지 확인한다."""
    app = create_app(settings=Settings(_env_file=None), judge=StaticJudge())

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json={**payload(), "conditions": []},
    )

    assert response.status_code == 400
    assert response.json() == {
        "ai_task_id": "task-1",
        "verification_id": "verification-1",
        "processing_status": "ERROR",
        "error": {
            "code": "INVALID_REQUEST",
            "message": "요청 형식 또는 필수 값이 올바르지 않습니다.",
        },
    }


def test_endpoint_returns_fetch_error_when_image_key_does_not_exist(tmp_path: Path):
    """이미지 조회 실패가 계약된 오류 코드로 반환되는지 확인한다."""
    image_root = tmp_path / "images"
    image_root.mkdir()
    app = create_app(
        settings=Settings(_env_file=None, ai_image_root=image_root),
        judge=StaticJudge(),
        image_store=LocalImageStore(image_root),
    )

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json=payload("missing.jpg"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_FETCH_FAILED"
    assert response.json()["processing_status"] == "ERROR"


def test_endpoint_returns_model_unavailable_for_invalid_model_response(tmp_path: Path):
    """잘못된 모델 결과가 모델 사용 불가 오류로 처리되는지 확인한다."""
    image_root = tmp_path / "images"
    image_root.mkdir()
    (image_root / "proof.jpg").write_bytes(b"test")

    class IncompleteJudge:
        """조건이 빠진 모델 응답을 흉내 내는 테스트 대역."""

        def evaluate(self, image_path, conditions):
            """조건 일부가 누락된 테스트 판정을 반환한다."""
            return InferenceResult(
                results=[],
                usage=InferenceUsage(model="gemini-test", latency_ms=0),
            )

    app = create_app(
        settings=Settings(_env_file=None, ai_image_root=image_root),
        judge=IncompleteJudge(),
        image_store=LocalImageStore(image_root),
    )

    response = TestClient(app).post("/internal/photo-verifications", json=payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
