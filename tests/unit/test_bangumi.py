import json
from pathlib import Path
from zipfile import ZipFile

from anime_party.bangumi import iter_anime_candidates


def test_streams_only_safe_popular_anime(tmp_path: Path) -> None:
    archive = tmp_path / "dump.zip"
    rows = [
        {
            "id": 1,
            "type": 2,
            "name": "Anime",
            "name_cn": "动画",
            "nsfw": False,
            "score": 8.0,
            "rank": 10,
            "favorite": {"wish": 200, "done": 400},
            "tags": [{"name": "校园", "count": 100}],
        },
        {
            "id": 2,
            "type": 2,
            "name": "Unsafe",
            "name_cn": "",
            "nsfw": True,
            "favorite": {"done": 1000},
        },
        {
            "id": 3,
            "type": 4,
            "name": "Game",
            "name_cn": "游戏",
            "nsfw": False,
            "favorite": {"done": 1000},
        },
    ]
    with ZipFile(archive, "w") as output:
        output.writestr("subject.jsonlines", "\n".join(json.dumps(row) for row in rows))

    candidates = list(iter_anime_candidates(archive, minimum_favorites=500))

    assert [candidate.subject_id for candidate in candidates] == [1]
    assert candidates[0].tags == ("校园",)
