from pathlib import Path

import pytest

from moamu_ai.image_paths import (
    ImageNotFoundError,
    ImagePathNotAllowedError,
    ImageUnreadableError,
    resolve_image_path,
)


def test_resolves_existing_image_inside_configured_root(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"image data")

    assert resolve_image_path(str(image), root) == image.resolve()


def test_relative_path_is_resolved_from_root(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    (root / "proof.jpg").write_bytes(b"image data")

    assert resolve_image_path("proof.jpg", root) == (root / "proof.jpg").resolve()


def test_missing_path_is_rejected(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()

    with pytest.raises(ImageNotFoundError):
        resolve_image_path("missing.jpg", root)


def test_path_outside_configured_root_is_rejected(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("not an image")

    with pytest.raises(ImagePathNotAllowedError):
        resolve_image_path(str(outside), root)


def test_image_format_and_size_are_not_checked(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    path = root / "large-unknown.bin"
    path.write_bytes(b"x" * 1024)

    assert resolve_image_path(str(path), root) == path.resolve()


def test_unreadable_path_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"image data")
    original_open = Path.open

    def raise_permission_error(path: Path, *args, **kwargs):
        if path == image.resolve():
            raise PermissionError("denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raise_permission_error)
    with pytest.raises(ImageUnreadableError):
        resolve_image_path(str(image), root)
