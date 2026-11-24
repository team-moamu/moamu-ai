import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from moamu_ai.config import Settings
from moamu_ai.errors import ImageStoreConfigurationError
from moamu_ai.image_sources import S3ImageStore, create_image_store
from moamu_ai.providers.base import ArtworkEditor, ArtworkEditResult
from moamu_ai.providers.gemini_artwork import GeminiArtworkEditor
from moamu_ai.schemas import ArtworkGenerationRequest


def create_argument_parser() -> argparse.ArgumentParser:
    """로컬 명화 편집 실행에 필요한 인자를 정의한다."""
    parser = argparse.ArgumentParser(
        description="Gemini로 원본 명화를 편집해 로컬 파일로 저장합니다."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=Path, help="로컬 원본 명화 이미지 경로")
    source.add_argument(
        "--source-s3-key",
        help="S3 원본 명화 객체 키 (예: original/woman_reading_a_letter.jpg)",
    )
    parser.add_argument("--goal", required=True, help="사진으로 인증할 자유목표")
    parser.add_argument("--major", required=True, help="목표 대분류")
    parser.add_argument("--middle", required=True, help="목표 중분류")
    parser.add_argument("--minor", required=True, help="목표 소분류")
    parser.add_argument(
        "--condition",
        action="append",
        required=True,
        help="이미지에 보여야 할 인증 조건. 여러 번 지정할 수 있습니다.",
    )
    parser.add_argument("--photo-guide", required=True, help="이미지 촬영 가이드")
    parser.add_argument("--output", type=Path, required=True, help="생성 이미지를 저장할 경로")
    return parser


def run_local_artwork_generation(
    source_path: Path,
    request: ArtworkGenerationRequest,
    output_path: Path,
    editor: ArtworkEditor,
) -> ArtworkEditResult:
    """편집 이미지를 생성해 사용자가 지정한 로컬 경로에 저장한다."""
    result = editor.edit(source_path, request)
    expected_suffix = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }[result.content_type]
    valid_suffixes = {expected_suffix}
    if expected_suffix == ".jpg":
        valid_suffixes.add(".jpeg")
    if output_path.suffix.lower() not in valid_suffixes:
        raise ValueError(f"output path must use the {expected_suffix} extension")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.image_bytes)
    return result


def main(argv: Optional[Sequence[str]] = None) -> None:
    """명화 편집 결과를 로컬 파일로 저장하는 명령을 실행한다."""
    args = create_argument_parser().parse_args(argv)
    request = ArtworkGenerationRequest.model_validate(
        {
            "taskId": 1,
            "taskVersion": 1,
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=2),
            "normalizedGoal": args.goal,
            "categoryPath": {
                "major": args.major,
                "middle": args.middle,
                "minor": args.minor,
            },
            "conditions": args.condition,
            "photoGuide": args.photo_guide,
        }
    )
    settings = Settings()
    editor = GeminiArtworkEditor(
        api_key=settings.gemini_token_api_key,
        model=settings.gemini_artwork_model,
        timeout_seconds=settings.ai_artwork_provider_timeout_seconds,
        prompt_version=settings.ai_artwork_prompt_version,
    )
    if args.source is not None:
        result = run_local_artwork_generation(args.source, request, args.output, editor)
    else:
        image_store = create_image_store(settings)
        if not isinstance(image_store, S3ImageStore):
            raise ImageStoreConfigurationError(
                "S3 source keys require AI_IMAGE_SOURCE=s3"
            )
        with image_store.open_image(args.source_s3_key) as source_path:
            result = run_local_artwork_generation(
                source_path, request, args.output, editor
            )
    print(
        json.dumps(
            {
                "model": result.model,
                "contentType": result.content_type,
                "sizeBytes": len(result.image_bytes),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
