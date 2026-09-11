"""Streaming access to Bangumi Archive subject records."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile


@dataclass(frozen=True, slots=True)
class AnimeCandidate:
    subject_id: int
    name: str
    name_cn: str
    date: str | None
    rank: int | None
    score: float
    favorites: int
    tags: tuple[str, ...]


def iter_anime_candidates(
    archive_path: Path,
    *,
    minimum_favorites: int = 500,
) -> Iterator[AnimeCandidate]:
    """Yield safe anime candidates without extracting the archive."""

    with ZipFile(archive_path) as archive, archive.open("subject.jsonlines") as stream:
        for raw_line in stream:
            item: Any = json.loads(raw_line)
            if item.get("type") != 2 or item.get("nsfw") is not False:
                continue
            favorite = item.get("favorite") or {}
            favorites = sum(
                int(favorite.get(key, 0)) for key in ("wish", "done", "doing", "on_hold", "dropped")
            )
            name = str(item.get("name") or "").strip()
            name_cn = str(item.get("name_cn") or "").strip()
            if not (name or name_cn) or favorites < minimum_favorites:
                continue
            tags = tuple(
                str(tag.get("name"))
                for tag in item.get("tags", ())
                if isinstance(tag, dict) and tag.get("name")
            )
            rank_value = item.get("rank")
            yield AnimeCandidate(
                subject_id=int(item["id"]),
                name=name,
                name_cn=name_cn,
                date=item.get("date"),
                rank=int(rank_value) if rank_value is not None else None,
                score=float(item.get("score") or 0),
                favorites=favorites,
                tags=tags,
            )
