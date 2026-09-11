"""Verify Apeiria against the real AstrBot event contract."""

from random import Random

from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage, Group, MessageMember
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata

from adapter import ApeiriaEventAdapter
from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)
from apeiria_core import GroupControlPolicy


def make_real_event(text: str) -> AstrMessageEvent:
    """Construct the real AstrBot v4.28 event shape used by OneBot groups."""

    message = AstrBotMessage()
    message.type = MessageType.GROUP_MESSAGE
    message.self_id = "900001"
    message.session_id = "200001"
    message.message_id = "event-1"
    message.group = Group("200001", "Apeiria test group")
    message.sender = MessageMember("300001", "Owner")
    message.message = []
    message.message_str = text
    message.raw_message = {}
    message.timestamp = 0
    return AstrMessageEvent(
        text,
        message,
        PlatformMetadata("aiocqhttp", "OneBot V11", "apeiria-test"),
        "200001",
    )


def main() -> None:
    """Assert identifiers, pipeline control, and domain mapping."""

    event = make_real_event("来一个")
    assert event.message_obj.message_id == "event-1"
    assert event.get_sender_id() == "300001"
    assert event.get_group_id() == "200001"
    assert event.unified_msg_origin == "apeiria-test:GroupMessage:200001"

    adapter = ApeiriaEventAdapter(
        AnimePartyEngine(load_questions(default_questions_path()), random=Random(1)),
        ChineseGamePresenter(),
        allowed_group_ids={"200001"},
        group_control=GroupControlPolicy({"300001"}),
    )
    rendered = adapter.handle(event)
    assert rendered[0].startswith("猜猜这部动画：")
    assert event.is_stopped()
    print("AstrBot event contract verified.")


if __name__ == "__main__":
    main()
