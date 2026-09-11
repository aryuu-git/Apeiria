from dataclasses import dataclass
from random import Random

from adapter import ApeiriaEventAdapter
from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)


@dataclass
class FakeMessageObject:
    message_id: str


class FakeAstrEvent:
    def __init__(self, message_id: str, text: str, group_id: str = "123456") -> None:
        self.message_str = text
        self.group_id = group_id
        self.unified_msg_origin = f"aiocqhttp:GroupMessage:{group_id}"
        self.message_obj = FakeMessageObject(message_id)
        self.stopped = False

    def get_sender_id(self) -> str:
        return "10001"

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
