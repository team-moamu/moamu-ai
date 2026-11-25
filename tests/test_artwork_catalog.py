import pytest

from moamu_ai.artwork_catalog import (
    ARTWORK_CATALOG,
    find_artwork_source,
    select_artwork_source,
)
from moamu_ai.schemas import ArtworkGenerationRequest


def _request(task_id: int, task_version: int = 1) -> ArtworkGenerationRequest:
    return ArtworkGenerationRequest.model_validate(
        {
            "taskId": task_id,
            "taskVersion": task_version,
            "expiresAt": "2026-11-24T04:02:00Z",
            "normalizedGoal": "매일 기타 연습하기",
            "categoryPath": {"major": "취미", "middle": "음악", "minor": "기타"},
            "conditions": ["기타가 보여야 한다"],
            "photoGuide": "기타를 연주하는 손이 보여야 한다",
        }
    )


def test_catalog_contains_unique_rights_verified_s3_artworks():
    work_ids = [entry.work_id for entry in ARTWORK_CATALOG]
    s3_keys = [entry.s3_key for entry in ARTWORK_CATALOG]

    assert len(ARTWORK_CATALOG) == 6
    assert len(work_ids) == len(set(work_ids))
    assert len(s3_keys) == len(set(s3_keys))
    assert all(entry.rights_code == "PUBLIC_DOMAIN" for entry in ARTWORK_CATALOG)
    assert all(entry.s3_key.startswith("original/") for entry in ARTWORK_CATALOG)
    assert all(entry.source_metadata().rights_code == "PUBLIC_DOMAIN" for entry in ARTWORK_CATALOG)


def test_source_selection_is_stable_for_same_task_and_rotates_for_new_tasks():
    first = select_artwork_source(_request(task_id=1))
    first_retry = select_artwork_source(_request(task_id=1))
    second = select_artwork_source(_request(task_id=2))

    assert first is first_retry
    assert first.s3_key == "original/the_geographer.jpg"
    assert second.s3_key == "original/the_little_schoolmistress.jpg"


def test_source_selection_changes_for_a_new_task_version():
    first_attempt = select_artwork_source(_request(task_id=1, task_version=1))
    retry = select_artwork_source(_request(task_id=1, task_version=2))

    assert retry.s3_key != first_attempt.s3_key


def test_source_selection_rejects_an_empty_public_domain_catalog():
    with pytest.raises(ValueError, match="no public-domain artworks"):
        select_artwork_source(_request(task_id=1), catalog=())


def test_find_artwork_source_returns_matching_catalog_entry():
    entry = find_artwork_source("original/young_girl_reading.jpg")

    assert entry is not None
    assert entry.title == "Young Girl Reading"
    assert entry.rights_code == "PUBLIC_DOMAIN"


def test_find_artwork_source_returns_none_for_unregistered_key():
    assert find_artwork_source("original/not-in-catalog.jpg") is None
