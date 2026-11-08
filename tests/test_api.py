from pathlib import Path

from fastapi.testclient import TestClient

from moamu_ai.app import create_app
from moamu_ai.config import Settings
from moamu_ai.image_sources import LocalImageStore
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionResult, ConditionStatus


class StaticJudge:
    def evaluate(self, image_path: Path, conditions):
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
    image_root = tmp_path / "images"
    image_root.mkdir()
    (image_root / "proof.jpg").write_bytes(b"test")

    class IncompleteJudge:
        def evaluate(self, image_path, conditions):
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
