from pathlib import Path
from random import Random

from anime_party import AnimePartyEngine, Difficulty, Question, QuestionCatalog, load_questions
from apeiria_core import IncomingMessage


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
    assert started.messages == ("猜猜这部动画：⌚🍌📱",)

    duplicate = engine.handle(make_message("1", "来一个"))
    assert duplicate.duplicate is True
    assert duplicate.messages == ()

    hint = engine.handle(make_message("2", "提示"))
    assert hint.messages == ("提示 1/3：涉及时间",)

    wrong = engine.handle(make_message("3", "命运之夜"))
    assert wrong.messages == ("还不对。可以继续猜，或者说“提示”。",)

    correct = engine.handle(make_message("4", "steins gate"))
    assert correct.messages[0].startswith("答对了，是《命运石之门》")


def test_difficulty_change_starts_matching_question() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))

    reply = engine.handle(make_message("1", "简单点"))

    assert reply.messages == ("已切换为简单难度。", "猜猜这部动画：🎸🍰☕")


def test_pause_clears_current_question() -> None:
    engine = AnimePartyEngine(make_catalog(), random=Random(1))
    engine.handle(make_message("1", "来一个"))

    paused = engine.handle(make_message("2", "暂停"))
    ignored_answer = engine.handle(make_message("3", "命运石之门"))

    assert paused.messages == ("游戏已暂停。想继续时，对我说“来一个”。",)
    assert ignored_answer.messages == ()


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
