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
    def __init__(self, message_id: str, text: str) -> None:
        self.message_str = text
        self.unified_msg_origin = "aiocqhttp:GroupMessage:123456"
        self.message_obj = FakeMessageObject(message_id)
        self.stopped = False

    def get_sender_id(self) -> str:
        return "10001"

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
