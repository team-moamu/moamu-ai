from pathlib import Path

from moamu_ai.errors import (
    ImageNotFoundError,
    ImagePathNotAllowedError,
    ImageRootUnavailableError,
    ImageUnreadableError,
)


def resolve_image_path(image_path: str, allowed_root: Path) -> Path:
    """허용된 로컬 루트 안에 있는 읽을 수 있는 이미지 경로를 확인한다.

    Args:
        image_path: 루트 기준 상대 경로 또는 이미지 절대 경로.
        allowed_root: 접근 가능한 경로로 제한할 최상위 디렉터리.

    Returns:
        존재하고 읽을 수 있는 이미지 파일의 절대 경로.

    Raises:
        ImageRootUnavailableError: 루트 디렉터리를 사용할 수 없는 경우.
        ImageNotFoundError: 이미지 파일이 존재하지 않는 경우.
        ImagePathNotAllowedError: 이미지가 허용 루트 바깥에 있는 경우.
        ImageUnreadableError: 경로 확인 또는 파일 읽기에 실패한 경우.

    이미지 형식과 용량 검사는 백엔드 업로드 경계에서 수행한다.
    """
    try:
        root = Path(allowed_root).expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ImageRootUnavailableError("configured image root is unavailable") from exc

    if not root.is_dir():
        raise ImageRootUnavailableError("configured image root is not a directory")

    requested_path = Path(image_path).expanduser()
    candidate = requested_path if requested_path.is_absolute() else root / requested_path

    try:
        resolved_path = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ImageNotFoundError("image path does not exist") from exc
    except OSError as exc:
        raise ImageUnreadableError("image path cannot be resolved") from exc

    try:
        resolved_path.relative_to(root)
    except ValueError as exc:
        raise ImagePathNotAllowedError("image path is outside the configured image root") from exc

    if not resolved_path.is_file():
        raise ImageNotFoundError("image path is not a regular file")

    try:
        with resolved_path.open("rb") as image_file:
            image_file.read(1)
    except OSError as exc:
        raise ImageUnreadableError("image path is not readable") from exc

    return resolved_path
