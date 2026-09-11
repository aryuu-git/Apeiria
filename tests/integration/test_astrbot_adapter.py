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


@dataclass
class FakeMessageObject:
    message_id: str


class FakeAstrEvent:
    def __init__(
        self,
        message_id: str,
        text: str,
        group_id: str = "123456",
        sender_id: str = "10001",
    ) -> None:
        self.message_str = text
        self.group_id = group_id
        self.sender_id = sender_id
        self.unified_msg_origin = f"aiocqhttp:GroupMessage:{group_id}"
        self.message_obj = FakeMessageObject(message_id)
        self.stopped = False

    def get_sender_id(self) -> str:
        return self.sender_id

    def get_group_id(self) -> str:
        return self.group_id

    def stop_event(self) -> None:
        self.stopped = True


def test_adapter_maps_event_and_stops_consumed_pipeline() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
    )
    event = FakeAstrEvent("message-1", "来一个")

    messages = adapter.handle(event)

    assert messages[0].startswith("猜猜这部动画：")
    assert event.stopped is True


def test_adapter_leaves_unrelated_group_chat_unconsumed() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
    )
    event = FakeAstrEvent("message-1", "大家晚上好")

    messages = adapter.handle(event)

    assert messages == ()
    assert event.stopped is False


def test_adapter_denies_group_outside_allowlist() -> None:
    catalog = load_questions(default_questions_path())
    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(catalog, random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"654321"},
    )
    event = FakeAstrEvent("message-1", "来一个")

    messages = adapter.handle(event)

    assert messages == ()
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

    assert adapter.handle(silence)[0].startswith("好的")
    assert adapter.handle(game) == ()
    assert adapter.handle(resume) == ("我回来了。",)
    assert adapter.handle(game_after_resume)[0].startswith("猜猜这部动画：")
    assert silence.stopped is True
    assert game.stopped is False
