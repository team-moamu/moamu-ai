import json
from contextlib import contextmanager
from pathlib import Path

from moamu_ai.artwork_cli import main, run_local_artwork_generation
from moamu_ai.providers.base import ArtworkEditResult
from moamu_ai.schemas import ArtworkGenerationRequest


class StaticArtworkEditor:
    """테스트 이미지 바이트를 반환하는 편집기 대역."""

    def __init__(self, result):
        self.result = result
        self.received = None

    def edit(self, image_path: Path, request: ArtworkGenerationRequest):
        self.received = (image_path, request)
        return self.result


def test_local_artwork_generation_saves_result_bytes(tmp_path: Path):
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    output = tmp_path / "results" / "artwork.jpg"
    result = ArtworkEditResult(
        image_bytes=b"\xff\xd8\xffedited",
        content_type="image/jpeg",
        model="gemini-test-image",
        latency_ms=12.0,
    )
    editor = StaticArtworkEditor(result)
    request = ArtworkGenerationRequest.model_validate(
        {
            "taskId": 1,
            "taskVersion": 1,
            "expiresAt": "2026-11-23T04:02:00Z",
            "normalizedGoal": "매일 영어 표현 적기",
            "categoryPath": {"major": "학습", "middle": "어학", "minor": "영어"},
            "conditions": ["영어 표현이 필기된 노트가 보여야 한다"],
            "photoGuide": "노트 필기가 읽히도록 촬영",
        }
    )

    saved = run_local_artwork_generation(source, request, output, editor)

    assert saved == result
    assert output.read_bytes() == result.image_bytes
    assert editor.received == (source, request)


def test_cli_builds_request_and_prints_local_output(monkeypatch, tmp_path: Path, capsys):
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    output = tmp_path / "generated.jpg"
    result = ArtworkEditResult(
        image_bytes=b"\xff\xd8\xffgenerated",
        content_type="image/jpeg",
        model="gemini-test-image",
        latency_ms=12.0,
    )
    created = {}

    class FakeEditor:
        def __init__(self, **kwargs):
            created["settings"] = kwargs

        def edit(self, image_path, request):
            created["source"] = image_path
            created["request"] = request
            return result

    class FakeSettings:
        gemini_token_api_key = None
        gemini_artwork_model = "gemini-test-image"
        ai_artwork_provider_timeout_seconds = 90.0
        ai_artwork_prompt_version = "artwork-edit-v1"

    monkeypatch.setattr("moamu_ai.artwork_cli.Settings", FakeSettings)
    monkeypatch.setattr("moamu_ai.artwork_cli.GeminiArtworkEditor", FakeEditor)

    main(
        [
            "--source",
            str(source),
            "--goal",
            "매일 영어 표현 적기",
            "--major",
            "학습",
            "--middle",
            "어학",
            "--minor",
            "영어",
            "--condition",
            "영어 표현이 적힌 노트가 보여야 한다",
            "--condition",
            "손글씨 기록이 보여야 한다",
            "--photo-guide",
            "노트를 위에서 촬영한다",
            "--output",
            str(output),
        ]
    )

    assert output.read_bytes() == result.image_bytes
    assert created["request"].normalized_goal == "매일 영어 표현 적기"
    assert len(created["request"].conditions) == 2
    assert created["source"] == source
    assert created["settings"]["model"] == "gemini-test-image"
    assert json.loads(capsys.readouterr().out) == {
        "model": "gemini-test-image",
        "contentType": "image/jpeg",
        "sizeBytes": len(result.image_bytes),
        "output": str(output),
    }


def test_cli_reads_s3_source_and_saves_result_locally(
    monkeypatch, tmp_path: Path, capsys
):
    source = tmp_path / "s3-source.jpg"
    source.write_bytes(b"source")
    output = tmp_path / "generated.jpg"
    result = ArtworkEditResult(
        image_bytes=b"\xff\xd8\xffgenerated",
        content_type="image/jpeg",
        model="gemini-test-image",
        latency_ms=12.0,
    )
    created = {}

    class FakeS3ImageStore:
        @contextmanager
        def open_image(self, image_key):
            created["image_key"] = image_key
            yield source

    class FakeEditor:
        def __init__(self, **kwargs):
            created["settings"] = kwargs

        def edit(self, image_path, request):
            created["source"] = image_path
            created["request"] = request
            return result

    class FakeSettings:
        gemini_token_api_key = None
        gemini_artwork_model = "gemini-test-image"
        ai_artwork_provider_timeout_seconds = 90.0
        ai_artwork_prompt_version = "artwork-edit-v1"

    monkeypatch.setattr("moamu_ai.artwork_cli.Settings", FakeSettings)
    monkeypatch.setattr("moamu_ai.artwork_cli.GeminiArtworkEditor", FakeEditor)
    monkeypatch.setattr("moamu_ai.artwork_cli.S3ImageStore", FakeS3ImageStore)
    monkeypatch.setattr(
        "moamu_ai.artwork_cli.create_image_store",
        lambda settings: FakeS3ImageStore(),
    )

    main(
        [
            "--source-s3-key",
            "original/woman_reading_a_letter.jpg",
            "--goal",
            "매일 영어 표현 적기",
            "--major",
            "학습",
            "--middle",
            "어학",
            "--minor",
            "영어",
            "--condition",
            "영어 표현이 적힌 노트가 보여야 한다",
            "--photo-guide",
            "노트를 위에서 촬영한다",
            "--output",
            str(output),
        ]
    )

    assert output.read_bytes() == result.image_bytes
    assert created["image_key"] == "original/woman_reading_a_letter.jpg"
    assert created["source"] == source
    assert json.loads(capsys.readouterr().out)["output"] == str(output)
