from apeiria_core import GroupControlPolicy, IncomingMessage


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
