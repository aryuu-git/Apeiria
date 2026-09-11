"""Verify Bangumi API reachability from this machine via the real transport.

Runs the production client against the live API (default subject 8) and
reports which degradation path was taken. Useful when the network or proxy
configuration changes; exit code 0 means a fresh subject was fetched.

Usage::

    uv run python packages/anime-party/scripts/verify_bangumi_api.py
    uv run python packages/anime-party/scripts/verify_bangumi_api.py --subject-id 265
"""

import argparse
import sys
import tempfile
from pathlib import Path

from anime_party.bangumi_api import BangumiClient, UrllibBangumiTransport
from apeiria_core import SQLiteStateStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject-id", type=int, default=8)
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="optional cache database path; defaults to a throwaway temp file",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        store = SQLiteStateStore(args.db or (Path(temp_dir) / "state.db"))
        client = BangumiClient(UrllibBangumiTransport(), store)
        subject = client.get_subject(args.subject_id)

    if subject is None:
        print(f"UNAVAILABLE: subject {args.subject_id} could not be fetched (quiet degradation)")
        sys.exit(1)
    print(
        f"OK: subject {args.subject_id}: {subject.get('name')} / "
        f"{subject.get('name_cn')} ({subject.get('date')})"
    )


if __name__ == "__main__":
    main()
