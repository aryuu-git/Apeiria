from pathlib import Path
from random import Random

from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    Difficulty,
    Question,
    QuestionCatalog,
    ReplyKind,
    default_questions_path,
    load_questions,
)
from apeiria_core import IncomingMessage, SQLiteStateStore

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
    catalog = load_questions(default_questions_path())

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


def test_active_game_survives_engine_restart(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    first = AnimePartyEngine(make_catalog(), random=Random(1), state_store=store)
    started = first.handle(make_message("1", "来一个"))
    first_hint = first.handle(make_message("2", "提示"))

    restarted = AnimePartyEngine(
        make_catalog(),
        random=Random(2),
        state_store=SQLiteStateStore(store.path),
    )
    second_hint = restarted.handle(make_message("3", "提示"))

    assert started.question is not None
    assert first_hint.hint_level == 1
    assert second_hint.question == started.question
    assert second_hint.hint_level == 2


def test_social_talk_during_active_round_is_not_an_answer() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))
    engine.handle(make_message("1", "来一个"))

    for message_id, text in [("2", "早"), ("3", "你好"), ("4", "哈哈，这题有点难"), ("5", "在吗")]:
        reply = engine.handle(make_message(message_id, text))
        assert reply.kind is ReplyKind.IGNORED, text

    still_guessing = engine.handle(make_message("6", "命运之夜"))
    assert still_guessing.kind is ReplyKind.WRONG_ANSWER


def test_wrong_answer_lines_rotate_with_randomness() -> None:
    from anime_party.presentation import WRONG_ANSWER_LINES

    engine = AnimePartyEngine(make_catalog(), random=Random(1))
    engine.handle(make_message("1", "来一个"))
    presenter = ChineseGamePresenter(random=Random(7))

    seen = {
        presenter.render(engine.handle(make_message(str(index), "命运之夜")))[0]
        for index in range(2, 7)
    }

    assert seen.issubset(set(WRONG_ANSWER_LINES))
    assert len(seen) > 1
    assert presenter.render(engine.handle(make_message("100", "命运之夜")))[0] in WRONG_ANSWER_LINES
