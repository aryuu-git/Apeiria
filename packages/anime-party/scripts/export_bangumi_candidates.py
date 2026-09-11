"""Export a compact, reviewable candidate list from a Bangumi Archive dump."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from anime_party.bangumi import iter_anime_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--minimum-favorites", type=int, default=500)
    args = parser.parse_args()

    candidates = sorted(
        iter_anime_candidates(
            args.archive,
            minimum_favorites=args.minimum_favorites,
        ),
        key=lambda item: (-item.favorites, item.subject_id),
    )[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([asdict(item) for item in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
