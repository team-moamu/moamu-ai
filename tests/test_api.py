from pathlib import Path

from fastapi.testclient import TestClient

from moamu_ai.app import create_app
from moamu_ai.config import Settings
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import (
    ConditionResult,
    ConditionStatus,
)


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
                )
                for condition in conditions
            ],
            usage=InferenceUsage(model="fake", latency_ms=0),
        )


def payload(image_path: str):
    return {
        "image_path": image_path,
        "conditions": [
            {
                "challenge_condition_id": 1,
                "code": "OBJECT_VISIBLE",
                "condition_type": "OBJECT_VISIBLE",
                "description": "A bottle is visible",
                "required": True,
                "sort_order": 1,
            },
            {
                "challenge_condition_id": 2,
                "code": "ACTION_VISIBLE",
                "condition_type": "ACTION_VISIBLE",
                "description": "The user is drinking water",
                "required": True,
                "sort_order": 2,
            },
        ],
    }


def test_endpoint_returns_per_condition_status_only(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    image = image_root / "proof.jpg"
    image.write_bytes(b"test")
    app = create_app(settings=Settings(ai_image_root=image_root), judge=StaticJudge())

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json=payload("proof.jpg"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"challenge_condition_id": 1, "status": "MET"},
            {"challenge_condition_id": 2, "status": "UNCERTAIN"},
        ]
    }


def test_endpoint_returns_not_found_for_missing_image_path(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    app = create_app(settings=Settings(ai_image_root=image_root), judge=StaticJudge())

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json=payload("missing.jpg"),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "IMAGE_NOT_FOUND"


def test_path_is_validated_before_missing_gemini_key(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    app = create_app(settings=Settings(ai_image_root=image_root))

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json=payload("missing.jpg"),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "IMAGE_NOT_FOUND"


def test_endpoint_rejects_a_path_outside_the_configured_root(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    outside_image = tmp_path / "private.jpg"
    outside_image.write_bytes(b"not an uploaded image")
    app = create_app(settings=Settings(ai_image_root=image_root), judge=StaticJudge())

    response = TestClient(app).post(
        "/internal/photo-verifications",
        json=payload(str(outside_image)),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "IMAGE_PATH_NOT_ALLOWED"


def test_health_endpoint_does_not_require_provider_credentials():
    app = create_app(settings=Settings())

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
