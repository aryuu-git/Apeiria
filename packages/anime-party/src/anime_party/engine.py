"""Deterministic state machine for Emoji anime guessing."""

from dataclasses import dataclass, field
from enum import StrEnum
from random import Random

from apeiria_core import IncomingMessage

from .catalog import QuestionCatalog
from .models import Difficulty, Question


class GameStatus(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"


@dataclass(slots=True)
class GameSession:
    status: GameStatus = GameStatus.IDLE
    difficulty: Difficulty = Difficulty.NORMAL
    current: Question | None = None
    hint_level: int = 0
    recent_subject_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GameReply:
    messages: tuple[str, ...]
    duplicate: bool = False


class AnimePartyEngine:
    START_COMMANDS = frozenset({"来一个", "猜动画", "开始", "开始游戏"})
    NEXT_COMMANDS = frozenset({"再来", "再来一个", "下一题"})
    HINT_COMMANDS = frozenset({"提示", "给个提示"})
    REVEAL_COMMANDS = frozenset({"公布", "公布答案", "答案"})
    PAUSE_COMMANDS = frozenset({"暂停", "暂停游戏", "不玩了"})
    EASY_COMMANDS = frozenset({"简单点", "简单"})
    HARD_COMMANDS = frozenset({"难一点", "困难", "难点"})

    def __init__(
        self,
        catalog: QuestionCatalog,
        *,
        random: Random | None = None,
        recent_limit: int = 8,
        handled_message_limit: int = 4096,
    ) -> None:
        if recent_limit < 0:
            raise ValueError("recent_limit must be non-negative")
        if handled_message_limit < 1:
            raise ValueError("handled_message_limit must be positive")
        self._catalog = catalog
        self._random = random or Random()
        self._recent_limit = recent_limit
        self._handled_message_limit = handled_message_limit
        self._sessions: dict[str, GameSession] = {}
        self._handled_messages: dict[tuple[str, str], None] = {}

    def handle(self, message: IncomingMessage) -> GameReply:
        identity = (message.session_id, message.message_id)
        if identity in self._handled_messages:
            return GameReply(messages=(), duplicate=True)
        self._handled_messages[identity] = None
        if len(self._handled_messages) > self._handled_message_limit:
            oldest = next(iter(self._handled_messages))
            del self._handled_messages[oldest]

        session = self._sessions.setdefault(message.session_id, GameSession())
        text = message.text.strip()

        if text in self.PAUSE_COMMANDS:
            session.status = GameStatus.PAUSED
            session.current = None
            session.hint_level = 0
            return GameReply(("游戏已暂停。想继续时，对我说“来一个”。",))
        if text in self.EASY_COMMANDS:
            session.difficulty = Difficulty.EASY
            return self._start_question(session, prefix="已切换为简单难度。")
        if text in self.HARD_COMMANDS:
            session.difficulty = Difficulty.HARD
            return self._start_question(session, prefix="已切换为困难难度。")
        if text in self.START_COMMANDS or text in self.NEXT_COMMANDS:
            return self._start_question(session)
        if text in self.HINT_COMMANDS:
            return self._hint(session)
        if text in self.REVEAL_COMMANDS:
            return self._reveal(session)
        return self._answer(session, text)

    def _start_question(self, session: GameSession, *, prefix: str | None = None) -> GameReply:
        question = self._catalog.choose(
            difficulty=session.difficulty,
            excluded_subject_ids=set(session.recent_subject_ids),
            random=self._random,
        )
        session.status = GameStatus.ACTIVE
        session.current = question
        session.hint_level = 0
        session.recent_subject_ids.append(question.subject_id)
        if self._recent_limit == 0:
            session.recent_subject_ids.clear()
        else:
            del session.recent_subject_ids[: -self._recent_limit]
        messages = [f"猜猜这部动画：{question.emoji}"]
        if prefix:
            messages.insert(0, prefix)
        return GameReply(tuple(messages))

    def _hint(self, session: GameSession) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(("现在没有进行中的题目。对我说“来一个”吧。",))
        if session.hint_level >= 3:
            return GameReply(("三层提示已经全部给出。可以继续猜，或说“公布答案”。",))
        session.hint_level += 1
        hint = session.current.hints[session.hint_level - 1]
        return GameReply((f"提示 {session.hint_level}/3：{hint}",))

    def _reveal(self, session: GameSession) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(("现在没有可以公布的题目。",))
        question = session.current
        session.status = GameStatus.IDLE
        session.current = None
        session.hint_level = 0
        return GameReply((f"答案是《{question.title}》。{question.explanation}",))

    def _answer(self, session: GameSession, text: str) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(())
        if not session.current.accepts(text):
            return GameReply(("还不对。可以继续猜，或者说“提示”。",))
        question = session.current
        session.status = GameStatus.IDLE
        session.current = None
        session.hint_level = 0
        return GameReply((f"答对了，是《{question.title}》！{question.explanation}",))
