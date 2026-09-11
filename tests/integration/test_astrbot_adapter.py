from dataclasses import dataclass
from random import Random

from adapter import ApeiriaEventAdapter
from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)
from apeiria_core import GroupControlPolicy

BOT_SELF_ID = "690947000"


@dataclass
class FakeMessageObject:
    message_id: str
    message: list | None = None
    sender: object = None


@dataclass
class FakeSender:
    nickname: str = ""


class FakeAstrEvent:
    def __init__(
        self,
        message_id: str,
        text: str,
        group_id: str = "123456",
        sender_id: str = "10001",
        *,
        segments: list | None = None,
        nickname: str = "",
    ) -> None:
        self.message_str = text
        self.group_id = group_id
        self.sender_id = sender_id
        self.unified_msg_origin = f"aiocqhttp:GroupMessage:{group_id}"
        self.message_obj = FakeMessageObject(
            message_id,
            segments,
            FakeSender(nickname),
        )
        self.stopped = False

    def get_sender_id(self) -> str:
        return self.sender_id

    def get_group_id(self) -> str:
        return self.group_id

    def get_self_id(self) -> str:
        return BOT_SELF_ID
    def stop_event(self) -> None:
        self.stopped = True


class FakeCompanion:
    def __init__(self) -> None:
        self.observed: list[tuple[str, str, str, str]] = []
        self.replies: list[tuple[str, str, str, str, bool]] = []
        self.answer = "嗯，我在。"

    def observe(
        self,
        session_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
    ) -> None:
        self.observed.append((session_id, sender_id, sender_name, text))

    def matches_name(self, text: str) -> bool:
        return "艾佩理雅" in text

    def wants_reply(self, text: str, *, mentioned: bool, sender_id: str) -> bool:
        return (
            mentioned
            or "艾佩理雅" in text
            or any(hint in text for hint in ("番", "动画", "游戏", "无聊"))
        )

    def decide(
        self,
        session_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
        *,
        mentioned: bool,
    ) -> str:
        self.replies.append((session_id, sender_id, sender_name, text, mentioned))
        return self.answer


def test_adapter_maps_event_and_stops_consumed_pipeline() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
    )
    event = FakeAstrEvent("message-1", "来一个")

    result = adapter.handle(event)

    assert result.messages[0].startswith("猜猜这部动画：")
    assert result.consumed is True
    assert result.companion_eligible is False
    assert event.stopped is True


def test_adapter_leaves_unrelated_group_chat_unconsumed() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
    )
    event = FakeAstrEvent("message-1", "大家晚上好")

    result = adapter.handle(event)

    assert result.messages == ()
    assert result.consumed is False
    assert event.stopped is False


def test_adapter_denies_group_outside_allowlist() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"654321"},
    )
    event = FakeAstrEvent("message-1", "来一个")

    result = adapter.handle(event)

    assert result.messages == ()
    assert event.stopped is False


def test_adapter_applies_admin_silence_before_game() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"123456"},
        group_control=GroupControlPolicy({"admin"}),
    )
    silence = FakeAstrEvent("1", "艾佩理雅静默", sender_id="admin")
    game = FakeAstrEvent("2", "来一个")
    resume = FakeAstrEvent("3", "艾佩理雅恢复", sender_id="admin")
    game_after_resume = FakeAstrEvent("4", "来一个")

    assert adapter.handle(silence).messages[0].startswith("好的")
    assert adapter.handle(silence).messages == ()
    assert adapter.handle(game).messages == ()
    assert adapter.handle(resume).messages == ("我回来了。",)
    assert adapter.handle(game_after_resume).messages[0].startswith("猜猜这部动画：")
    assert silence.stopped is True
    assert game.stopped is False


def test_adapter_offers_companion_for_mention() -> None:
    catalog = load_questions(default_questions_path())
    companion = FakeCompanion()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        companion=companion,
    )
    event = FakeAstrEvent(
        "message-2",
        "晚上好",
        segments=[{"type": "at", "data": {"qq": BOT_SELF_ID}}],
        nickname="阿明",
    )

    result = adapter.handle(event)

    assert result.companion_eligible is True
    assert result.mentioned is True
    assert result.sender_name == "阿明"
    assert result.consumed is False
    assert event.stopped is False
    assert companion.observed == [
        ("aiocqhttp:GroupMessage:123456", "10001", "阿明", "晚上好")
    ]
    assert adapter.handle(event).messages == ()  # duplicate delivery stays silent
    assert len(companion.observed) == 1


def test_adapter_declines_companion_for_plain_chat() -> None:
    catalog = load_questions(default_questions_path())
    companion = FakeCompanion()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        companion=companion,
    )
    event = FakeAstrEvent("message-3", "大家晚上好", nickname="阿明")

    result = adapter.handle(event)

    assert result.companion_eligible is False
    assert result.mentioned is False
    assert len(companion.observed) == 1  # history still recorded


def test_adapter_declines_companion_during_game() -> None:
    catalog = load_questions(default_questions_path())
    companion = FakeCompanion()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        companion=companion,
    )
    event = FakeAstrEvent("message-4", "来一个", nickname="阿明")

    result = adapter.handle(event)

    assert result.companion_eligible is False
    assert result.consumed is True


def test_adapter_declines_companion_during_silence() -> None:
    catalog = load_questions(default_questions_path())
    companion = FakeCompanion()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"123456"},
        group_control=GroupControlPolicy({"admin"}),
        companion=companion,
    )
    silence = FakeAstrEvent("1", "艾佩理雅静默", sender_id="admin")
    chat = FakeAstrEvent("2", "艾佩理雅在吗")

    assert adapter.handle(silence).consumed is True

    result = adapter.handle(chat)

    assert result.companion_eligible is False
    assert companion.observed == []


def test_adapter_runs_game_expression_for_companion_action() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
    )
    event = FakeAstrEvent("message-5", "随便什么", nickname="阿明")

    messages = adapter.run_game_expression(event, "来一个")

    assert len(messages) == 1
    assert messages[0].startswith("猜猜这部动画：")
    assert event.stopped is False  # synthetic expression must not stop the real event


class FakeSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def append_event(self, kind: str, session_id: str, payload: dict) -> int:
        self.events.append((kind, session_id, dict(payload)))
        return len(self.events)


def test_adapter_emits_lifecycle_events() -> None:
    catalog = load_questions(default_questions_path())
    sink = FakeSink()
    companion = FakeCompanion()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"123456"},
        companion=companion,
        event_sink=sink,
    )
    chat = FakeAstrEvent("2", "今晚看什么番", nickname="阿明")
    game = FakeAstrEvent("3", "来一个")
    duplicate = FakeAstrEvent("3", "来一个")

    adapter.handle(chat)
    adapter.handle(game)
    adapter.handle(duplicate)

    kinds = [kind for kind, _, _ in sink.events]
    assert kinds == ["companion.gate", "game.reply", "message.skip"]
    assert sink.events[0][2]["eligible"] is True
    assert sink.events[1][2]["kind"] == "question"
    assert sink.events[2][2]["reason"] == "duplicate"


def test_adapter_hands_misses_to_presence() -> None:
    catalog = load_questions(default_questions_path())
    companion = FakeCompanion()
    sink = FakeSink()
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        companion=companion,
        event_sink=sink,
    )
    adapter.handle(FakeAstrEvent("1", "来一个"))
    miss = FakeAstrEvent("2", "这是我的猜测吗", nickname="阿明")

    result = adapter.handle(miss)

    assert result.messages == ()  # no robo reply for a miss
    assert result.consumed is False
    assert result.companion_eligible is True
    assert result.state is not None
    assert result.state["wrong_attempts"] == 1
    assert [kind for kind, _, _ in sink.events][-1] == "game.miss"
