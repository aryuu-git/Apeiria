from pathlib import Path

from apeiria_core import GroupControlPolicy, IncomingMessage, SQLiteStateStore


def message(
    message_id: str,
    sender_id: str,
    text: str,
    session_id: str = "group:1",
) -> IncomingMessage:
    return IncomingMessage(message_id, session_id, sender_id, text)


def test_admin_can_silence_and_resume_one_group() -> None:
    policy = GroupControlPolicy({"admin"})

    silenced = policy.evaluate(message("1", "admin", "艾佩理雅静默"))
    hidden = policy.evaluate(message("2", "member", "来一个"))
    other_group = policy.evaluate(message("3", "member", "来一个", "group:2"))
    resumed = policy.evaluate(message("4", "admin", "艾佩理雅恢复"))
    visible = policy.evaluate(message("5", "member", "来一个"))

    assert silenced.allow is False and silenced.response is not None
    assert hidden.allow is False and hidden.response is None
    assert other_group.allow is True
    assert resumed.allow is False and resumed.response == "我回来了。"
    assert visible.allow is True


def test_non_admin_cannot_change_silence_state() -> None:
    policy = GroupControlPolicy({"admin"})

    denied = policy.evaluate(message("1", "member", "艾佩理雅静默"))
    ordinary = policy.evaluate(message("2", "member", "来一个"))

    assert denied.allow is False
    assert denied.response == "只有管理员可以让我进入静默。"
    assert ordinary.allow is True


def test_control_messages_are_deduplicated_with_bounded_memory() -> None:
    policy = GroupControlPolicy({"admin"}, handled_message_limit=2)

    first = policy.evaluate(message("1", "admin", "艾佩理雅静默"))
    duplicate = policy.evaluate(message("1", "admin", "艾佩理雅静默"))
    policy.evaluate(message("2", "admin", "艾佩理雅恢复"))
    policy.evaluate(message("3", "member", "普通聊天"))
    replay_after_eviction = policy.evaluate(message("1", "admin", "艾佩理雅静默"))

    assert first.response is not None
    assert duplicate.allow is False and duplicate.response is None
    assert replay_after_eviction.response is not None


def test_silence_survives_policy_restart(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    first = GroupControlPolicy({"admin"}, state_store=store)
    first.evaluate(message("1", "admin", "艾佩理雅静默"))

    restarted = GroupControlPolicy({"admin"}, state_store=SQLiteStateStore(store.path))
    hidden = restarted.evaluate(message("2", "member", "来一个"))
    resumed = restarted.evaluate(message("3", "admin", "艾佩理雅恢复"))

    assert hidden.allow is False and hidden.response is None
    assert resumed.response == "我回来了。"
