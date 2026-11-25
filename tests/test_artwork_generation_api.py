import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from time import monotonic, sleep

from fastapi.testclient import TestClient
from pydantic import SecretStr

from moamu_ai.app import create_app
from moamu_ai.config import Settings
from moamu_ai.providers.base import ArtworkEditResult

TOKEN = "test-internal-service-token"
JPEG_BYTES = b"\xff\xd8\xffgenerated-image"


def artwork_payload(**overrides):
    """명화 생성 API 테스트용 요청 데이터를 만든다."""
    payload = {
        "taskId": 91,
        "taskVersion": 1,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
        "normalizedGoal": "매일 물 마시기",
        "categoryPath": {"major": "건강", "middle": "생활 습관", "minor": "수분 섭취"},
        "conditions": ["물이 컵에 담겨 보여야 한다", "인물이 물을 마시는 모습이 보여야 한다"],
        "photoGuide": "컵과 사람이 함께 보이도록 촬영한다.",
    }
    payload.update(overrides)
    return payload


class FakeArtworkStorage:
    """S3 접근 없이 원본과 결과 객체를 제공한다."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.uploaded = {}

    @contextmanager
    def open_image(self, image_key: str):
        """카탈로그 원본 키에 대응하는 로컬 테스트 파일을 제공한다."""
        yield self.source_path

    def get_image_if_exists(self, image_key: str):
        """객체가 이미 저장돼 있으면 바이트와 MIME을 반환한다."""
        return self.uploaded.get(image_key)

    def upload_image(self, image_key: str, image_bytes: bytes, content_type: str):
        """결과 객체를 작업 키별로 저장한다."""
        self.uploaded[image_key] = (image_bytes, content_type)


class FakeArtworkEditor:
    """고정 이미지 결과와 완료 이벤트를 제공한다."""

    def __init__(self, failure=None):
        self.calls = 0
        self.failure = failure

    def edit(self, image_path: Path, request):
        """Gemini 편집 호출을 흉내 낸다."""
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return ArtworkEditResult(
            image_bytes=JPEG_BYTES,
            content_type="image/jpeg",
            model="gemini-test",
            latency_ms=1,
        )


def create_test_app(tmp_path, editor=None, include_token=True):
    """인증 토큰, SQLite 파일과 테스트 이미지 저장소가 주입된 앱을 만든다."""
    source_path = tmp_path / "source.jpg"
    source_path.write_bytes(b"source painting")
    return create_app(
        settings=Settings(
            _env_file=None,
            ai_internal_api_token=SecretStr(TOKEN) if include_token else None,
            ai_artwork_task_db_path=tmp_path / "artwork-tasks.sqlite3",
        ),
        artwork_editor=editor or FakeArtworkEditor(),
        artwork_image_storage=FakeArtworkStorage(source_path),
    )


def wait_for_status(client, expected_status):
    """조회 API가 목표 작업 상태를 반환할 때까지 제한 시간 동안 기다린다."""
    deadline = monotonic() + 3
    while monotonic() < deadline:
        response = client.get(
            "/internal/artwork-generations/91/versions/1",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        if response.status_code == 200 and response.json()["data"]["status"] == expected_status:
            return response.json()
        sleep(0.01)
    raise AssertionError(f"task did not reach {expected_status}")


def test_post_accepts_task_then_status_returns_s3_result(tmp_path):
    """접수는 202를 반환하고 상태 조회는 생성·업로드 결과를 반환한다."""
    editor = FakeArtworkEditor()
    app = create_test_app(tmp_path, editor)

    with TestClient(app) as client:
        accepted = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        result = wait_for_status(client, "SUCCEEDED")

    assert accepted.status_code == 202
    assert accepted.json() == {
        "success": True,
        "data": {"taskId": 91, "taskVersion": 1, "status": "PENDING"},
    }
    assert result["data"]["image"]["key"] == "generated-artworks/91/1/result.jpg"
    assert result["data"]["image"]["contentType"] == "image/jpeg"
    assert result["data"]["image"]["sizeBytes"] == len(JPEG_BYTES)
    assert len(result["data"]["image"]["sha256"]) == 64
    assert result["data"]["source"]["rightsCode"] == "PUBLIC_DOMAIN"
    assert result["data"]["reuseAllowed"] is True
    assert editor.calls == 1


def test_status_lookup_returns_running_while_editor_is_processing(tmp_path):
    """상태 조회가 이미지 편집 중 RUNNING을 반환한다."""
    editor_started = Event()
    release_editor = Event()

    class BlockingEditor:
        """테스트가 RUNNING 상태를 조회할 때까지 편집을 대기시킨다."""

        def edit(self, image_path, request):
            """테스트 대기 해제 후 고정 JPEG 결과를 반환한다."""
            editor_started.set()
            assert release_editor.wait(3)
            return ArtworkEditResult(
                image_bytes=JPEG_BYTES,
                content_type="image/jpeg",
                model="gemini-test",
                latency_ms=1,
            )

    app = create_test_app(tmp_path, editor=BlockingEditor())
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with TestClient(app) as client:
        try:
            accepted = client.post(
                "/internal/artwork-generations",
                json=artwork_payload(),
                headers=headers,
            )
            assert accepted.status_code == 202
            assert editor_started.wait(2)
            running = client.get(
                "/internal/artwork-generations/91/versions/1", headers=headers
            )
        finally:
            release_editor.set()
        completed = wait_for_status(client, "SUCCEEDED")

    assert running.json()["data"]["status"] == "RUNNING"
    assert completed["data"]["status"] == "SUCCEEDED"


def test_status_lookup_returns_failure_fields_after_editor_error(tmp_path):
    """편집기 실패 후 상태 조회가 errorCode와 retryable을 반환한다."""
    editor = FakeArtworkEditor(failure=RuntimeError("private"))
    app = create_test_app(tmp_path, editor=editor)
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with TestClient(app) as client:
        accepted = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(),
            headers=headers,
        )
        failed = wait_for_status(client, "FAILED")

    assert accepted.status_code == 202
    assert failed["data"]["errorCode"] == "ARTWORK_GENERATION_FAILED"
    assert failed["data"]["retryable"] is True


def test_post_returns_conflict_for_same_key_with_different_body(tmp_path):
    """같은 작업 ID·버전에 다른 본문을 전달하면 409를 반환한다."""
    app = create_test_app(tmp_path)
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with TestClient(app) as client:
        first = client.post(
            "/internal/artwork-generations", json=artwork_payload(), headers=headers
        )
        conflict = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(normalizedGoal="매일 차 마시기"),
            headers=headers,
        )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json() == {
        "success": False,
        "error": {
            "code": "ARTWORK_TASK_PAYLOAD_CONFLICT",
            "message": "같은 작업 ID와 버전에 이미 다른 요청이 접수되었습니다.",
        },
    }


def test_post_is_idempotent_and_does_not_repeat_model_call(tmp_path):
    """같은 본문 재접수는 기존 작업을 반환하고 모델을 중복 호출하지 않는다."""
    editor = FakeArtworkEditor()
    app = create_test_app(tmp_path, editor)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = artwork_payload()

    with TestClient(app) as client:
        first = client.post("/internal/artwork-generations", json=payload, headers=headers)
        second = client.post("/internal/artwork-generations", json=payload, headers=headers)
        wait_for_status(client, "SUCCEEDED")

    assert first.status_code == second.status_code == 202
    assert second.json()["data"]["taskId"] == 91
    assert editor.calls == 1


def test_post_rejects_wrong_bearer_token(tmp_path):
    """설정된 토큰과 다른 Bearer 토큰은 접수하지 않는다."""
    app = create_test_app(tmp_path)

    with TestClient(app) as client:
        response = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(),
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_post_returns_service_unavailable_when_token_is_not_configured(tmp_path):
    """내부 인증 토큰이 설정되지 않았으면 API를 사용할 수 없다고 알린다."""
    app = create_test_app(tmp_path, include_token=False)

    with TestClient(app) as client:
        response = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "INTERNAL_AUTH_NOT_CONFIGURED"


def test_get_status_requires_bearer_token(tmp_path):
    """상태 조회도 내부 서비스 Bearer 인증을 요구한다."""
    app = create_test_app(tmp_path)

    with TestClient(app) as client:
        response = client.get("/internal/artwork-generations/91/versions/1")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_post_returns_error_envelope_when_task_store_is_unavailable(monkeypatch, tmp_path):
    """SQLite 저장 실패를 내부 API 오류 형식으로 반환한다."""
    app = create_test_app(tmp_path)

    def fail_accept(_payload):
        raise sqlite3.OperationalError("private database detail")

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.artwork_task_store, "accept", fail_accept)
        response = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "error": {
            "code": "ARTWORK_TASK_STORE_UNAVAILABLE",
            "message": "명화 생성 작업 저장소에 접근할 수 없습니다.",
        },
    }


def test_get_returns_error_envelope_when_task_store_is_unavailable(monkeypatch, tmp_path):
    """상태 조회 중 SQLite 오류를 내부 API 오류 형식으로 반환한다."""
    app = create_test_app(tmp_path)

    def fail_get(_task_id, _task_version):
        raise sqlite3.OperationalError("private database detail")

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.artwork_task_store, "get", fail_get)
        response = client.get(
            "/internal/artwork-generations/91/versions/1",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ARTWORK_TASK_STORE_UNAVAILABLE"


def test_post_rejects_an_already_expired_request(tmp_path):
    """접수 시 이미 만료된 작업은 저장하지 않고 400을 반환한다."""
    app = create_test_app(tmp_path)
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()

    with TestClient(app) as client:
        response = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(expiresAt=expired),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_get_returns_not_found_for_unknown_task_version(tmp_path):
    """저장되지 않은 작업 버전 조회는 404 계약 오류를 반환한다."""
    app = create_test_app(tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/internal/artwork-generations/91/versions/2",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARTWORK_TASK_VERSION_NOT_FOUND"


def test_status_lookup_openapi_path_matches_backend_contract(tmp_path):
    """Swagger 경로 매개변수 이름이 백엔드 명세와 같아야 한다."""
    app = create_test_app(tmp_path)

    assert (
        "/internal/artwork-generations/{taskId}/versions/{taskVersion}"
        in app.openapi()["paths"]
    )


def test_request_validation_uses_artwork_error_envelope(tmp_path):
    """필드 검증 실패는 명화 생성 API의 공통 오류 형식으로 반환한다."""
    app = create_test_app(tmp_path)

    with TestClient(app) as client:
        response = client.post(
            "/internal/artwork-generations",
            json=artwork_payload(conditions=[]),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": {
            "code": "INVALID_REQUEST",
            "message": "요청 형식 또는 필수 값이 올바르지 않습니다.",
        },
    }
