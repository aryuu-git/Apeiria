from pathlib import Path
from random import Random

from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    Difficulty,
    Question,
    QuestionCatalog,
    ReplyKind,
    load_questions,
)
from apeiria_core import IncomingMessage

PRESENTER = ChineseGamePresenter()


def make_message(message_id: str, text: str, *, session_id: str = "group:1") -> IncomingMessage:
    return IncomingMessage(
        message_id=message_id,
        session_id=session_id,
        sender_id="user:1",
        text=text,
    )


def make_catalog() -> QuestionCatalog:
    return QuestionCatalog(
        [
            Question(
                subject_id=1,
                title="命运石之门",
                aliases=("Steins;Gate", "石头门"),
                emoji="⌚🍌📱",
                difficulty=Difficulty.NORMAL,
                hints=("涉及时间", "故事发生在秋叶原", "电话微波炉"),
                explanation="一切都是命运石之门的选择。",
            ),
            Question(
                subject_id=2,
                title="轻音少女",
                aliases=("K-ON!", "轻音"),
                emoji="🎸🍰☕",
                difficulty=Difficulty.EASY,
                hints=("校园", "下午茶", "轻音乐部"),
                explanation="音乐与放学后的下午茶。",
            ),
            Question(
                subject_id=3,
                title="奇诺之旅",
                aliases=("Kino no Tabi",),
                emoji="🏍️🗺️3️⃣",
                difficulty=Difficulty.HARD,
                hints=("旅行", "会说话的摩托车", "每个国家停留三天"),
                explanation="旅行者奇诺与汉密斯的见闻。",
            ),
        ]
    )


def test_complete_game_flow_and_duplicate_delivery() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))

    started = engine.handle(make_message("1", "来一个"))
    assert PRESENTER.render(started) == ("猜猜这部动画：⌚🍌📱",)

    duplicate = engine.handle(make_message("1", "来一个"))
    assert duplicate.duplicate is True
    assert PRESENTER.render(duplicate) == ()

    hint = engine.handle(make_message("2", "提示"))
    assert PRESENTER.render(hint) == ("提示 1/3：涉及时间",)

    wrong = engine.handle(make_message("3", "命运之夜"))
    assert PRESENTER.render(wrong) == ("还不对。可以继续猜，或者说“提示”。",)

    correct = engine.handle(make_message("4", "steins gate"))
    assert PRESENTER.render(correct)[0].startswith("答对了，是《命运石之门》")


def test_difficulty_change_starts_matching_question() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))

    reply = engine.handle(make_message("1", "简单点"))

    assert PRESENTER.render(reply) == ("已切换为简单难度。", "猜猜这部动画：🎸🍰☕")


def test_pause_clears_current_question() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))
    engine.handle(make_message("1", "来一个"))

    paused = engine.handle(make_message("2", "暂停"))
    ignored_answer = engine.handle(make_message("3", "命运石之门"))

    assert PRESENTER.render(paused) == ("游戏已暂停。想继续时，对我说“来一个”。",)
    assert ignored_answer.kind is ReplyKind.IGNORED


def test_shipped_catalog_contains_30_distinct_questions() -> None:
    path = Path("packages/anime-party/data/questions.zh-CN.json")
    catalog = load_questions(path)

    assert catalog.size == 30
    assert len({question.subject_id for question in catalog.questions}) == 30


def test_message_deduplication_has_a_capacity_bound() -> None:
    engine = AnimePartyEngine(
        make_catalog(),
        random=Random(1),
        handled_message_limit=2,
    )
    engine.handle(make_message("1", "普通聊天"))
    engine.handle(make_message("2", "普通聊天"))
    engine.handle(make_message("3", "普通聊天"))

    replay_after_eviction = engine.handle(make_message("1", "普通聊天"))

    assert replay_after_eviction.duplicate is False


def test_all_hints_are_bounded_and_reveal_finishes_question() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))
    engine.handle(make_message("1", "来一个"))

    hint_kinds = [engine.handle(make_message(str(index), "提示")).kind for index in range(2, 6)]
    revealed = engine.handle(make_message("6", "公布"))
    second_reveal = engine.handle(make_message("7", "公布"))

    assert hint_kinds == [
        ReplyKind.HINT,
        ReplyKind.HINT,
        ReplyKind.HINT,
        ReplyKind.HINTS_EXHAUSTED,
    ]
    assert revealed.kind is ReplyKind.REVEALED
    assert second_reveal.kind is ReplyKind.NO_ACTIVE_QUESTION


def test_sessions_are_isolated() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))

    group_one = engine.handle(make_message("1", "来一个", session_id="group:1"))
    group_two_answer = engine.handle(make_message("1", "命运石之门", session_id="group:2"))

    assert group_one.kind is ReplyKind.QUESTION
    assert group_two_answer.kind is ReplyKind.IGNORED
