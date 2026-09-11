"""Framework-facing mapping kept separate from the AstrBot plugin entry point."""

import json
import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any, Protocol

from anime_party import AnimePartyEngine, ChineseGamePresenter, GameReply, ReplyKind
from apeiria_core import CompanionService, EventSink, GroupControlPolicy, IncomingMessage

GAME_ACTION_EXPRESSIONS = {
    "start_game": "来一个",
    "hint": "提示",
    "reveal": "公布",
}

logger = logging.getLogger("apeiria")


class AstrEventLike(Protocol):
    """Small subset of AstrBot events required by Apeiria."""

    message_str: str
    unified_msg_origin: str
    message_obj: object

    def get_sender_id(self) -> str:
        """Return the platform sender identifier."""

    def get_group_id(self) -> str:
        """Return the group identifier, or an empty string outside groups."""

    def get_self_id(self) -> str:
        """Return the bot account identifier on this platform."""

    def stop_event(self) -> None:
        """Stop later handlers for a consumed game event."""


@dataclass(frozen=True, slots=True)
class HandlingResult:
    """Outcome of routing one event through the domain layer."""

    messages: tuple[str, ...]
    consumed: bool
    companion_eligible: bool
    mentioned: bool
    sender_name: str
    called: bool = False
    reply: GameReply | None = None
    state: dict[str, Any] | None = None


def _mentioned_by_self(event: AstrEventLike) -> bool:
    segments = getattr(event.message_obj, "message", None)
    if not isinstance(segments, list):
        return False
    self_id = event.get_self_id()
    return any(
        isinstance(segment, dict)
        and segment.get("type") == "at"
        and str((segment.get("data") or {}).get("qq", "")) == self_id
        for segment in segments
    )


def _sender_name(event: AstrEventLike) -> str:
    sender = getattr(event.message_obj, "sender", None)
    nickname = getattr(sender, "nickname", None)
    return str(nickname).strip() or event.get_sender_id()


class ApeiriaEventAdapter:
    """Translate AstrBot-shaped events to and from the domain layer."""

    def __init__(
        self,
        engine: AnimePartyEngine,
        presenter: ChineseGamePresenter,
        *,
        allowed_group_ids: Collection[str] | None = None,
        group_control: GroupControlPolicy | None = None,
        companion: CompanionService | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self._engine = engine
        self._presenter = presenter
        self._allowed_group_ids = (
            None if allowed_group_ids is None else frozenset(allowed_group_ids)
        )
        self._group_control = group_control or GroupControlPolicy(())
        self._companion = companion
        self._event_sink = event_sink

    def _emit(self, kind: str, session_id: str, payload: dict[str, Any]) -> None:
        """Fan one lifecycle event out to the sink and the runtime log."""
        line = json.dumps(payload, ensure_ascii=False)
        if self._event_sink is not None:
            try:
                self._event_sink.append_event(kind, session_id, payload)
            except Exception:  # observability must never break the product
                logger.exception("event sink failed for %s", kind)
        logger.info("[%s] %s", kind, line)

    def handle(self, event: AstrEventLike) -> HandlingResult:
        """Handle one event without exposing it to the domain.

        Args:
            event: AstrBot event or compatible test double.

        Returns:
            Rendered messages plus routing facts for the presence path.
        """

        if (
            self._allowed_group_ids is not None
            and event.get_group_id() not in self._allowed_group_ids
        ):
            self._emit(
                "message.skip",
                event.unified_msg_origin,
                {
                    "reason": "group_not_allowed",
                    "group_id": event.get_group_id(),
                    "text": event.message_str,
                },
            )
            return HandlingResult((), False, False, False, "")

        mentioned = _mentioned_by_self(event)
        incoming = IncomingMessage(
            message_id=str(getattr(event.message_obj, "message_id", "")),
            session_id=event.unified_msg_origin,
            sender_id=event.get_sender_id(),
            text=event.message_str,
        )
        control = self._group_control.evaluate(incoming)
        if not control.allow:
            if control.response is not None:
                event.stop_event()
                self._emit(
                    "control.reply",
                    incoming.session_id,
                    {"reason": control.reason, "text": control.response},
                )
                return HandlingResult((control.response,), True, False, mentioned, "")
            # Duplicate delivery or admin silence: stay silent, keep history clean.
            self._emit(
                "message.skip",
                incoming.session_id,
                {
                    "reason": control.reason,
                    "message_id": incoming.message_id,
                    "sender_id": incoming.sender_id,
                    "text": incoming.text,
                },
            )
            return HandlingResult((), False, False, mentioned, "")

        sender_name = _sender_name(event)
        if self._companion is not None:
            self._companion.observe(
                incoming.session_id,
                incoming.sender_id,
                sender_name,
                incoming.text,
            )
        reply = self._engine.handle(incoming)
        rendered = self._presenter.render(reply)
        called = self._companion is not None and self._companion.matches_name(
            incoming.text
        )
        if reply.kind is ReplyKind.WRONG_ANSWER:
            # A miss is handed to the presence layer: with the game snapshot
            # in context the model can tell guessing from chatting, so a
            # greeting never gets the robo reply and a guess still gets a nudge.
            self._emit(
                "game.miss",
                incoming.session_id,
                {
                    "sender_id": incoming.sender_id,
                    "text": incoming.text,
                    "state": reply.state,
                },
            )
            return HandlingResult(
                (),
                False,
                True,
                mentioned,
                sender_name,
                called=called,
                reply=reply,
                state=reply.state,
            )
        if reply.kind is not ReplyKind.IGNORED:
            event.stop_event()
            self._emit(
                "game.reply",
                incoming.session_id,
                {
                    "kind": reply.kind.value,
                    "messages": list(rendered),
                    "sender_id": incoming.sender_id,
                    "text": incoming.text,
                },
            )
            return HandlingResult(
                rendered,
                True,
                False,
                mentioned,
                sender_name,
                reply=reply,
                state=reply.state,
            )
        eligible = self._companion is not None and self._companion.wants_reply(
            incoming.text,
            mentioned=mentioned,
            sender_id=incoming.sender_id,
        )
        self._emit(
            "companion.gate",
            incoming.session_id,
            {
                "eligible": eligible,
                "mentioned": mentioned,
                "sender_id": incoming.sender_id,
                "sender_name": sender_name,
                "text": incoming.text,
            },
        )
        return HandlingResult(
            rendered,
            False,
            eligible,
            mentioned,
            sender_name,
            called=called,
            reply=reply,
            state=reply.state,
        )
        if reply.kind is not ReplyKind.IGNORED:
            event.stop_event()
            self._emit(
                "game.reply",
                incoming.session_id,
                {
                    "kind": reply.kind.value,
                    "messages": list(rendered),
                    "sender_id": incoming.sender_id,
                    "text": incoming.text,
                },
            )
            return HandlingResult(
                rendered,
                True,
                False,
                mentioned,
                sender_name,
                reply=reply,
                state=reply.state,
            )
        eligible = self._companion is not None and self._companion.wants_reply(
            incoming.text,
            mentioned=mentioned,
            sender_id=incoming.sender_id,
        )
        self._emit(
            "companion.gate",
            incoming.session_id,
            {
                "eligible": eligible,
                "mentioned": mentioned,
                "sender_id": incoming.sender_id,
                "sender_name": sender_name,
                "text": incoming.text,
            },
        )
        return HandlingResult(
            rendered,
            False,
            eligible,
            mentioned,
            sender_name,
            called=called,
            reply=reply,
            state=reply.state,
        )

    def run_game_expression(
        self,
        event: AstrEventLike,
        expression: str,
    ) -> tuple[str, ...]:
        """Run one deterministic game expression on the companion's behalf.

        The engine stays the sole authority over game state: the presence
        layer can only propose expressions the engine already understands.
        """

        incoming = IncomingMessage(
            message_id=f"companion-{uuid.uuid4().hex}",
            session_id=event.unified_msg_origin,
            sender_id=event.get_self_id(),
            text=expression,
        )
        reply = self._engine.handle(incoming)
        rendered = self._presenter.render(reply)
        self._emit(
            "companion.action",
            incoming.session_id,
            {"expression": expression, "messages": list(rendered)},
        )
        return rendered
