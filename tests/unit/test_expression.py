"""Unit tests for the AI game expression layer."""

import json
from random import Random

from anime_party import (
    AiGamePresenter,
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)
from anime_party.engine import ReplyKind
from anime_party.presentation import WRONG_ANSWER_LINES
from apeiria_core import IncomingMessage, LlmTransportError


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []
        self.answer = '{"text": "唔，不是这个哦～"}'
        self.error: Exception | None = None

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        self.calls.append([dict(m) for m in messages])
        if self.error is not None:
            raise self.error
        return self.answer


def make_presenter(transport: FakeTransport) -> AiGamePresenter:
    catalog = load_questions(default_questions_path())
    engine = AnimePartyEngine(catalog, random=Random(1))
    engine.handle(IncomingMessage("1", "s", "10001", "来一个"))
    wrong = engine.handle(IncomingMessage("2", "s", "10001", "命运之夜"))
    assert wrong.kind is ReplyKind.WRONG_ANSWER
    return AiGamePresenter(
        transport,
        ChineseGamePresenter(random=Random(3)),
        model="deepseek-v4-flash",
    ), wrong


def test_full_rewording_replaces_template() -> None:
    transport = FakeTransport()
    presenter, wrong = make_presenter(transport)

    lines = presenter.render(wrong, sender_name="aryuu")

    assert lines == ("唔，不是这个哦～",)
    assert transport.calls[0][0]["role"] == "system"
    context = json.loads(transport.calls[0][1]["content"])
    assert context["mode"] == "full"
    assert "aryuu" in context["event"]


def test_information_boundary_hides_answer_title() -> None:
    transport = FakeTransport()
    presenter, wrong = make_presenter(transport)

    presenter.render(wrong, sender_name="aryuu")

    user_content = transport.calls[0][1]["content"]
    assert "命运石之门" not in user_content  # the answer never reaches the model


def test_lead_mode_keeps_fixed_data_line() -> None:
    transport = FakeTransport()
    catalog = load_questions(default_questions_path())
    engine = AnimePartyEngine(catalog, random=Random(1))
    engine.handle(IncomingMessage("1", "s", "10001", "来一个"))
    question = engine.handle(IncomingMessage("2", "s", "10001", "zzz-not-a-title"))
    assert question.kind is ReplyKind.WRONG_ANSWER
    engine.handle(IncomingMessage("3", "s", "10001", "提示"))
    hint = engine.handle(IncomingMessage("4", "s", "10001", "提示"))
    assert hint.kind is ReplyKind.HINT
    transport.answer = '{"lead": "线索来咯～"}'
    presenter = AiGamePresenter(
        transport, ChineseGamePresenter(random=Random(3)), model="deepseek-v4-flash"
    )

    lines = presenter.render(hint, sender_name="aryuu")

    assert len(lines) == 1
    assert lines[0].startswith("线索来咯～")
    assert "提示 2/3：" in lines[0]  # the fixed hint text survives untouched
    assert "命运石之门" not in json.dumps(transport.calls[0][1]["content"])


def test_transport_failure_falls_back_to_templates() -> None:
    transport = FakeTransport()
    presenter, wrong = make_presenter(transport)
    transport.error = LlmTransportError("down")

    lines = presenter.render(wrong, sender_name="aryuu")

    assert lines[0] in WRONG_ANSWER_LINES


def test_unparsable_output_falls_back_to_templates() -> None:
    transport = FakeTransport()
    presenter, wrong = make_presenter(transport)
    transport.answer = "完全不是 JSON"

    lines = presenter.render(wrong, sender_name="aryuu")

    assert lines[0] in WRONG_ANSWER_LINES


def test_ignored_replies_skip_the_model() -> None:
    transport = FakeTransport()
    catalog = load_questions(default_questions_path())
    engine = AnimePartyEngine(catalog, random=Random(1))
    ignored = engine.handle(IncomingMessage("1", "s", "10001", "早"))
    assert ignored.kind is ReplyKind.IGNORED
    presenter = AiGamePresenter(
        transport, ChineseGamePresenter(random=Random(3)), model="deepseek-v4-flash"
    )

    assert presenter.render(ignored, sender_name="aryuu") == ()
    assert transport.calls == []
