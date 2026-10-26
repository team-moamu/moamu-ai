from pathlib import Path

from moamu_ai.errors import (
    ImageNotFoundError,
    ImagePathNotAllowedError,
    ImageRootUnavailableError,
    ImageUnreadableError,
)


def resolve_image_path(image_path: str, allowed_root: Path) -> Path:
    """Resolve a readable image file under the configured local test volume.

    File format and size are intentionally left to the backend upload boundary.
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
