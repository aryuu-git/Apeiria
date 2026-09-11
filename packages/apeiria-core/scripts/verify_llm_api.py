"""Verify the AI companion endpoint with the real transport.

Reads the ``ai`` section of a local, git-ignored config file, sends one
small chat completion, and reports the answer. Exit code 0 means the
endpoint, key, and model all work.

Usage::

    uv run python packages/apeiria-core/scripts/verify_llm_api.py
    uv run python packages/apeiria-core/scripts/verify_llm_api.py --prompt "你好"
"""

import argparse
import json
import sys
from pathlib import Path

from apeiria_core import LlmTransportError, OpenAICompatibleTransport


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("deploy/napcat/apeiria.local.json"),
        help="local git-ignored config with an 'ai' section",
    )
    parser.add_argument("--prompt", default="用一句话介绍你自己")
    args = parser.parse_args()

    ai = json.loads(args.config.read_text(encoding="utf-8"))["ai"]
    transport = OpenAICompatibleTransport(
        base_url=str(ai["base_url"]),
        api_key=str(ai["api_key"]),
    )
    try:
        answer = transport.chat(
            str(ai["model"]),
            [{"role": "user", "content": args.prompt}],
        )
    except LlmTransportError as error:
        print(f"UNAVAILABLE: {error}")
        sys.exit(1)
    print(f"OK: {answer}")


if __name__ == "__main__":
    main()
