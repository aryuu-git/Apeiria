"""Framework-facing mapping kept separate from the AstrBot plugin entry point."""

from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from anime_party import AnimePartyEngine, ChineseGamePresenter, ReplyKind
from apeiria_core import CompanionService, GroupControlPolicy, IncomingMessage


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
    ) -> None:
        self._engine = engine
        self._presenter = presenter
        self._allowed_group_ids = (
            None if allowed_group_ids is None else frozenset(allowed_group_ids)
        )
        self._group_control = group_control or GroupControlPolicy(())
        self._companion = companion

    def handle(self, event: AstrEventLike) -> HandlingResult:
        """Handle one event without exposing it to the domain.

        Args:
            event: AstrBot event or compatible test double.

        Returns:
            Rendered messages plus routing facts for the AI companion path.
        """

        skip = HandlingResult((), False, False, False, "")
        if (
            self._allowed_group_ids is not None
            and event.get_group_id() not in self._allowed_group_ids
        ):
            return skip

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
                return HandlingResult((control.response,), True, False, mentioned, "")
            # Duplicate delivery or admin silence: stay silent, keep history clean.
            return HandlingResult((), False, False, mentioned, "")

        sender_name = _sender_name(event)
        if self._companion is not None:
            self._companion.observe(incoming.session_id, sender_name, incoming.text)
        reply = self._engine.handle(incoming)
        rendered = self._presenter.render(reply)
        if reply.kind is not ReplyKind.IGNORED:
            event.stop_event()
            return HandlingResult(rendered, True, False, mentioned, sender_name)
        eligible = self._companion is not None and self._companion.wants_reply(
            incoming.text,
            mentioned=mentioned,
        )
        return HandlingResult(rendered, False, eligible, mentioned, sender_name)
