"""Deterministic state machine for Emoji anime guessing."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from random import Random
from typing import Any

from apeiria_core import IncomingMessage, StateStore

from .catalog import QuestionCatalog
from .models import Difficulty, Question


class GameStatus(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"


class ReplyKind(StrEnum):
    IGNORED = "ignored"
    QUESTION = "question"
    DIFFICULTY_CHANGED = "difficulty_changed"
    PAUSED = "paused"
    NO_ACTIVE_QUESTION = "no_active_question"
    HINT = "hint"
    HINTS_EXHAUSTED = "hints_exhausted"
    REVEALED = "revealed"
    WRONG_ANSWER = "wrong_answer"
    CORRECT_ANSWER = "correct_answer"


@dataclass(slots=True)
class GameSession:
    status: GameStatus = GameStatus.IDLE
    difficulty: Difficulty = Difficulty.NORMAL
    current: Question | None = None
    hint_level: int = 0
    recent_subject_ids: list[int] = field(default_factory=list)
    started_at: float | None = None
    wrong_attempts: int = 0


@dataclass(frozen=True, slots=True)
class GameReply:
    kind: ReplyKind
    duplicate: bool = False
    question: Question | None = None
    difficulty: Difficulty | None = None
    hint_level: int | None = None
    hint: str | None = None
    timed_out: bool = False
    state: dict[str, Any] | None = None



class AnimePartyEngine:
    START_COMMANDS = frozenset({"来一个", "猜动画", "开始", "开始游戏"})
    NEXT_COMMANDS = frozenset({"再来", "再来一个", "下一题"})
    HINT_COMMANDS = frozenset({"提示", "给个提示"})
    REVEAL_COMMANDS = frozenset({"公布", "公布答案", "答案"})
    PAUSE_COMMANDS = frozenset({"暂停", "暂停游戏", "不玩了"})
    EASY_COMMANDS = frozenset({"简单点", "简单"})
    HARD_COMMANDS = frozenset({"难一点", "困难", "难点"})
    # Messages that are clearly social, never answer attempts. Kept narrow
    # on purpose: anything not listed still goes through answer checking,
    # so real titles are never swallowed by the triage.
    CHITCHAT_EXACT = frozenset({
        "早", "早安", "早上好", "午安", "晚安", "你好", "您好", "你们好",
        "哈喽", "哈罗", "嗨", "hi", "hello", "在吗", "在嘛", "来了",
        "打卡", "签到", "辛苦了", "冲", "冲了", "睡了", "困",
    })
    CHITCHAT_CONTAINS = ("哈哈", "嘿嘿", "233", "hhh", "笑死", "哈哈哈哈")

    def __init__(
        self,
        catalog: QuestionCatalog,
        *,
        random: Random | None = None,
        recent_limit: int = 8,
        handled_message_limit: int = 4096,
        state_store: StateStore | None = None,
        round_timeout_seconds: float = 0.0,
        name_triggers: tuple[str, ...] = ("艾佩理雅", "艾佩莉亚", "apeiria"),
        clock: Callable[[], float] | None = None,
    ) -> None:
        if recent_limit < 0:
            raise ValueError("recent_limit must be non-negative")
        if handled_message_limit < 1:
            raise ValueError("handled_message_limit must be positive")
        if round_timeout_seconds < 0:
            raise ValueError("round_timeout_seconds must be non-negative")
        self._catalog = catalog
        self._random = random or Random()
        self._recent_limit = recent_limit
        self._handled_message_limit = handled_message_limit
        self._state_store = state_store
        self._round_timeout_seconds = round_timeout_seconds
        self._name_triggers = tuple(trigger.lower() for trigger in name_triggers)
        self._clock = clock or time.time
        self._sessions: dict[str, GameSession] = {}
        self._handled_messages: dict[tuple[str, str], None] = {}

    def _is_name_call(self, text: str) -> bool:
        """Return whether the message addresses the companion by name."""
        lowered = text.lower()
        return any(trigger in lowered for trigger in self._name_triggers)

    def handle(self, message: IncomingMessage) -> GameReply:
        identity = (message.session_id, message.message_id)
        if identity in self._handled_messages:
            return GameReply(kind=ReplyKind.IGNORED, duplicate=True)
        self._handled_messages[identity] = None
        if len(self._handled_messages) > self._handled_message_limit:
            oldest = next(iter(self._handled_messages))
            del self._handled_messages[oldest]

        session = self._get_session(message.session_id)
        text = message.text.strip()

        if (
            session.status is GameStatus.ACTIVE
            and self._round_timeout_seconds > 0
            and session.started_at is not None
            and self._clock() - session.started_at > self._round_timeout_seconds
        ):
            reply = replace(self._reveal(session), timed_out=True)
            return self._persist(message.session_id, session, reply)

        if text in self.PAUSE_COMMANDS:
            session.status = GameStatus.PAUSED
            session.current = None
            session.hint_level = 0
            return self._persist(message.session_id, session, GameReply(kind=ReplyKind.PAUSED))
        if text in self.EASY_COMMANDS:
            session.difficulty = Difficulty.EASY
            return self._persist(
                message.session_id,
                session,
                self._start_question(session, changed_difficulty=Difficulty.EASY),
            )
        if text in self.HARD_COMMANDS:
            session.difficulty = Difficulty.HARD
            return self._persist(
                message.session_id,
                session,
                self._start_question(session, changed_difficulty=Difficulty.HARD),
            )
        if text in self.START_COMMANDS or text in self.NEXT_COMMANDS:
            return self._persist(message.session_id, session, self._start_question(session))
        if text in self.HINT_COMMANDS:
            return self._persist(message.session_id, session, self._hint(session))
        if text in self.REVEAL_COMMANDS:
            return self._persist(message.session_id, session, self._reveal(session))
        if session.status is GameStatus.ACTIVE and (
            self._looks_like_chitchat(text) or self._is_name_call(text)
        ):
            # Social talk and direct name calls during an active round are
            # never answer attempts: leave them unconsumed so the presence
            # layer can respond.
            return replace(
                GameReply(kind=ReplyKind.IGNORED), state=self._snapshot(session)
            )
        reply = self._answer(session, text)
        if reply.kind is ReplyKind.CORRECT_ANSWER:
            return self._persist(message.session_id, session, reply)
        if reply.kind is ReplyKind.WRONG_ANSWER:
            return self._persist(message.session_id, session, reply)
        return replace(reply, state=self._snapshot(session))

    def _get_session(self, session_id: str) -> GameSession:
        if session_id in self._sessions:
            return self._sessions[session_id]
        session = GameSession()
        if self._state_store is not None:
            raw = self._state_store.get("anime-party", session_id)
            if raw is not None:
                try:
                    payload = json.loads(raw)
                    current_id = payload.get("current_subject_id")
                    current = self._catalog.get(int(current_id)) if current_id is not None else None
                    status = GameStatus(payload["status"])
                    if status is GameStatus.ACTIVE and current is None:
                        status = GameStatus.IDLE
                    session = GameSession(
                        status=status,
                        difficulty=Difficulty(payload["difficulty"]),
                        current=current,
                        hint_level=int(payload["hint_level"]),
                        recent_subject_ids=[int(item) for item in payload["recent_subject_ids"]],
                        started_at=(
                            float(payload["started_at"])
                            if payload.get("started_at") is not None
                            else None
                        ),
                        wrong_attempts=int(payload.get("wrong_attempts", 0)),
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    session = GameSession()
        self._sessions[session_id] = session
        return session

    def _persist(
        self,
        session_id: str,
        session: GameSession,
        reply: GameReply,
    ) -> GameReply:
        if self._state_store is not None:
            self._state_store.set(
                "anime-party",
                session_id,
                json.dumps(self._snapshot(session), ensure_ascii=False, separators=(",", ":")),
            )
        return replace(reply, state=self._snapshot(session))

    def _snapshot(self, session: GameSession) -> dict[str, Any]:
        """Serializable round state shared with persistence and the presence layer."""
        return {
            "status": session.status.value,
            "difficulty": session.difficulty.value,
            "current_subject_id": (
                None if session.current is None else session.current.subject_id
            ),
            "hint_level": session.hint_level,
            "recent_subject_ids": session.recent_subject_ids,
            "started_at": session.started_at,
            "wrong_attempts": session.wrong_attempts,
        }

    def _start_question(
        self,
        session: GameSession,
        *,
        changed_difficulty: Difficulty | None = None,
    ) -> GameReply:
        question = self._catalog.choose(
            difficulty=session.difficulty,
            excluded_subject_ids=set(session.recent_subject_ids),
            random=self._random,
        )
        session.status = GameStatus.ACTIVE
        session.current = question
        session.hint_level = 0
        session.wrong_attempts = 0
        session.started_at = self._clock()
        session.recent_subject_ids.append(question.subject_id)
        if self._recent_limit == 0:
            session.recent_subject_ids.clear()
        else:
            del session.recent_subject_ids[: -self._recent_limit]
        return GameReply(
            kind=(
                ReplyKind.DIFFICULTY_CHANGED
                if changed_difficulty is not None
                else ReplyKind.QUESTION
            ),
            question=question,
            difficulty=changed_difficulty,
        )

    def _hint(self, session: GameSession) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(kind=ReplyKind.NO_ACTIVE_QUESTION)
        if session.hint_level >= 3:
            return GameReply(kind=ReplyKind.HINTS_EXHAUSTED, question=session.current)
        session.hint_level += 1
        hint = session.current.hints[session.hint_level - 1]
        return GameReply(
            kind=ReplyKind.HINT,
            question=session.current,
            hint_level=session.hint_level,
            hint=hint,
        )

    def _reveal(self, session: GameSession) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(kind=ReplyKind.NO_ACTIVE_QUESTION)
        question = session.current
        session.status = GameStatus.IDLE
        session.current = None
        session.hint_level = 0
        session.wrong_attempts = 0
        session.started_at = None
        return GameReply(kind=ReplyKind.REVEALED, question=question)

    def _looks_like_chitchat(self, text: str) -> bool:
        """Return whether an active-round message is social, not a guess."""
        if not text:
            return True
        if text in self.CHITCHAT_EXACT:
            return True
        if any(marker in text for marker in self.CHITCHAT_CONTAINS):
            return True
        return all(char in "。，！？!?~～… .,、 " for char in text)

    def _answer(self, session: GameSession, text: str) -> GameReply:
        if session.status is not GameStatus.ACTIVE or session.current is None:
            return GameReply(kind=ReplyKind.IGNORED)
        if not session.current.accepts(text):
            session.wrong_attempts += 1
            return GameReply(kind=ReplyKind.WRONG_ANSWER, question=session.current)
        question = session.current
        session.status = GameStatus.IDLE
        session.current = None
        session.hint_level = 0
        session.wrong_attempts = 0
        session.started_at = None
        return GameReply(kind=ReplyKind.CORRECT_ANSWER, question=question)
