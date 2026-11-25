from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from moamu_ai.schemas import ArtworkGenerationRequest, ArtworkSourceMetadata


@dataclass(frozen=True)
class ArtworkCatalogEntry:
    """권리와 S3 위치가 확인된 원본 명화 한 점을 나타낸다."""

    work_id: str
    title: str
    artist: str
    s3_key: str
    source_url: str
    rights_code: str
    rights_url: str
    checked_at: datetime

    def source_metadata(self) -> ArtworkSourceMetadata:
        """내부 API 응답에 포함할 작품·권리 정보를 반환한다."""
        return ArtworkSourceMetadata(
            workId=self.work_id,
            title=self.title,
            sourceUrl=self.source_url,
            rightsCode=self.rights_code,
            rightsUrl=self.rights_url,
            checkedAt=self.checked_at,
        )


_RIGHTS_CHECKED_AT = datetime(2026, 11, 24, 2, 54, 4, tzinfo=timezone.utc)

ARTWORK_CATALOG: tuple[ArtworkCatalogEntry, ...] = (
    ArtworkCatalogEntry(
        work_id="staedel-1149",
        title="The Geographer",
        artist="Johannes Vermeer",
        s3_key="original/the_geographer.jpg",
        source_url="https://sammlung.staedelmuseum.de/en/work/the-geographer",
        rights_code="PUBLIC_DOMAIN",
        rights_url="https://sammlung.staedelmuseum.de/en/work/the-geographer",
        checked_at=_RIGHTS_CHECKED_AT,
    ),
    ArtworkCatalogEntry(
        work_id="nga-1937.1.91",
        title="The Little Schoolmistress",
        artist="Jean Siméon Chardin",
        s3_key="original/the_little_schoolmistress.jpg",
        source_url="https://www.nga.gov/artworks/98-little-schoolmistress",
        rights_code="PUBLIC_DOMAIN",
        rights_url="https://www.nga.gov/artworks/98-little-schoolmistress",
        checked_at=_RIGHTS_CHECKED_AT,
    ),
    ArtworkCatalogEntry(
        work_id="rijksmuseum-sk-a-2344",
        title="The Milkmaid",
        artist="Johannes Vermeer",
        s3_key="original/the_milkmaid.jpg",
        source_url=(
            "https://www.rijksmuseum.nl/en/collection/object/"
            "The-Milkmaid--42dd0e658c2979aec8e144d2357c55c0"
        ),
        rights_code="PUBLIC_DOMAIN",
        rights_url=(
            "https://www.rijksmuseum.nl/en/collection/object/"
            "The-Milkmaid--42dd0e658c2979aec8e144d2357c55c0"
        ),
        checked_at=_RIGHTS_CHECKED_AT,
    ),
    ArtworkCatalogEntry(
        work_id="nga-1942.9.97",
        title="Woman Holding a Balance",
        artist="Johannes Vermeer",
        s3_key="original/woman_holding_a_balance.jpg",
        source_url="https://www.nga.gov/artworks/1236-woman-holding-balance",
        rights_code="PUBLIC_DOMAIN",
        rights_url="https://www.nga.gov/artworks/1236-woman-holding-balance",
        checked_at=_RIGHTS_CHECKED_AT,
    ),
    ArtworkCatalogEntry(
        work_id="rijksmuseum-sk-c-251",
        title="Woman Reading a Letter",
        artist="Johannes Vermeer",
        s3_key="original/woman_reading_a_letter.jpg",
        source_url=(
            "https://www.rijksmuseum.nl/en/collection/object/"
            "Woman-Reading-a-Letter--8e9e02c8045362ffb2171b2fb52953ba"
        ),
        rights_code="PUBLIC_DOMAIN",
        rights_url=(
            "https://www.rijksmuseum.nl/en/collection/object/"
            "Woman-Reading-a-Letter--8e9e02c8045362ffb2171b2fb52953ba"
        ),
        checked_at=_RIGHTS_CHECKED_AT,
    ),
    ArtworkCatalogEntry(
        work_id="nga-1961.16.1",
        title="Young Girl Reading",
        artist="Jean Honoré Fragonard",
        s3_key="original/young_girl_reading.jpg",
        source_url="https://www.nga.gov/artworks/46303-young-girl-reading",
        rights_code="PUBLIC_DOMAIN",
        rights_url="https://www.nga.gov/artworks/46303-young-girl-reading",
        checked_at=_RIGHTS_CHECKED_AT,
    ),
)


def select_artwork_source(
    request: ArtworkGenerationRequest,
    catalog: Sequence[ArtworkCatalogEntry] = ARTWORK_CATALOG,
) -> ArtworkCatalogEntry:
    """작업 ID와 버전에 따라 권리 확인된 원본을 일관되게 순환 선택한다."""
    eligible = tuple(
        entry for entry in catalog if entry.rights_code == "PUBLIC_DOMAIN"
    )
    if not eligible:
        raise ValueError("no public-domain artworks are available")

    index = (request.task_id + request.task_version - 2) % len(eligible)
    return eligible[index]


def find_artwork_source(s3_key: str) -> Optional[ArtworkCatalogEntry]:
    """S3 키로 카탈로그 원본을 찾고, 등록되지 않은 키면 None을 반환한다."""
    return next((entry for entry in ARTWORK_CATALOG if entry.s3_key == s3_key), None)
