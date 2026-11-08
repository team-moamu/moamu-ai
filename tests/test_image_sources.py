from io import BytesIO
from pathlib import Path

import pytest

from moamu_ai.errors import ImageFetchFailedError
from moamu_ai.image_sources import LocalImageStore, S3ImageStore


def test_local_image_store_resolves_key_under_configured_root(tmp_path: Path):
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"image bytes")

    with LocalImageStore(root).open_image("proof.jpg") as resolved:
        assert resolved == image.resolve()


def test_s3_image_store_downloads_key_to_temporary_file_and_cleans_it():
    body = BytesIO(b"s3-image-bytes")
    seen = {}

    class FakeS3Client:
        def get_object(self, **kwargs):
            seen.update(kwargs)
            return {"Body": body}

    store = S3ImageStore(bucket="bucket", client=FakeS3Client())
    temp_path = None
    with store.open_image("verifications/proof.jpg") as image_path:
        temp_path = image_path
        assert image_path.read_bytes() == b"s3-image-bytes"
        assert image_path.suffix == ".jpg"

    assert seen == {"Bucket": "bucket", "Key": "verifications/proof.jpg"}
    assert body.closed
    assert temp_path is not None and not temp_path.exists()


def test_s3_image_store_maps_fetch_failures_to_contract_error():
    class FailingS3Client:
        def get_object(self, **kwargs):
            raise RuntimeError("private AWS detail")

    with pytest.raises(ImageFetchFailedError, match="could not be fetched"):
        with S3ImageStore(bucket="bucket", client=FailingS3Client()).open_image("proof.jpg"):
            pass
