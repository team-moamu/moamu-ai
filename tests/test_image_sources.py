from io import BytesIO
from pathlib import Path

import pytest

from moamu_ai.errors import ImageFetchFailedError
from moamu_ai.image_sources import LocalImageStore, S3ImageStore


def test_local_image_store_resolves_key_under_configured_root(tmp_path: Path):
    """로컬 저장소가 이미지 키를 설정 루트에서 찾는지 확인한다."""
    root = tmp_path / "images"
    root.mkdir()
    image = root / "proof.jpg"
    image.write_bytes(b"image bytes")

    with LocalImageStore(root).open_image("proof.jpg") as resolved:
        assert resolved == image.resolve()


def test_s3_image_store_downloads_key_to_temporary_file_and_cleans_it():
    """S3 객체를 임시 파일로 제공하고 종료 후 지우는지 확인한다."""
    body = BytesIO(b"s3-image-bytes")
    seen = {}

    class FakeS3Client:
        """정상 S3 객체 응답을 제공하는 테스트 클라이언트."""

        def get_object(self, **kwargs):
            """요청된 S3 키에 해당하는 테스트 객체를 반환한다."""
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
    """S3 조회 실패가 계약 오류로 변환되는지 확인한다."""
    class FailingS3Client:
        """S3 객체 조회 실패를 재현하는 테스트 클라이언트."""

        def get_object(self, **kwargs):
            """테스트용 S3 객체 조회 예외를 발생시킨다."""
            raise RuntimeError("private AWS detail")

    with pytest.raises(ImageFetchFailedError, match="could not be fetched"):
        with S3ImageStore(bucket="bucket", client=FailingS3Client()).open_image("proof.jpg"):
            pass
