import json
from pathlib import Path
from random import Random
from typing import Any

from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    ReplyKind,
    default_questions_path,
    load_questions,
)
from apeiria_core import IncomingMessage


def test_documented_conversation_scenarios() -> None:
    raw: Any = json.loads(Path("persona/emoji-anime-scenarios.json").read_text(encoding="utf-8"))
    catalog = load_questions(default_questions_path())
    presenter = ChineseGamePresenter()

    for scenario in raw:
        engine = AnimePartyEngine(catalog, random=Random(7))
        for step in scenario["steps"]:
            reply = engine.handle(
                IncomingMessage(
                    message_id=step["message_id"],
                    session_id=f"scenario:{scenario['name']}",
                    sender_id="owner",
                    text=step["text"],
                )
            )
            rendered = presenter.render(reply)
            assert reply.kind is ReplyKind(step["kind"]), scenario["name"]
            assert reply.duplicate is step.get("duplicate", False), scenario["name"]
            if step["contains"] is None:
                assert rendered == (), scenario["name"]
            else:
                assert any(step["contains"] in message for message in rendered), scenario["name"]
