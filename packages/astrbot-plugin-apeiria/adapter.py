"""Framework-facing mapping kept separate from the AstrBot plugin entry point."""

from collections.abc import Collection
from typing import Protocol

from anime_party import AnimePartyEngine, ChineseGamePresenter, ReplyKind
from apeiria_core import IncomingMessage


class AstrEventLike(Protocol):
    """Small subset of AstrBot events required by Apeiria."""

    message_str: str
    unified_msg_origin: str
    message_obj: object

    def get_sender_id(self) -> str:
        """Return the platform sender identifier."""

    def get_group_id(self) -> str:
        """Return the group identifier, or an empty string outside groups."""

    def stop_event(self) -> None:
        """Stop later handlers for a consumed game event."""


class ApeiriaEventAdapter:
    """Translate AstrBot-shaped events to and from the domain layer."""

    def __init__(
        self,
        engine: AnimePartyEngine,
        presenter: ChineseGamePresenter,
        *,
        allowed_group_ids: Collection[str] | None = None,
    ) -> None:
        self._engine = engine
        self._presenter = presenter
        self._allowed_group_ids = (
            None if allowed_group_ids is None else frozenset(allowed_group_ids)
        )

    def handle(self, event: AstrEventLike) -> tuple[str, ...]:
        """Handle one event without exposing it to the domain.

        Args:
            event: AstrBot event or compatible test double.

        Returns:
            Rendered messages to send in order.
        """

        if (
            self._allowed_group_ids is not None
            and event.get_group_id() not in self._allowed_group_ids
        ):
            return ()

        message_id = str(getattr(event.message_obj, "message_id", ""))
        reply = self._engine.handle(
            IncomingMessage(
                message_id=message_id,
                session_id=event.unified_msg_origin,
                sender_id=event.get_sender_id(),
                text=event.message_str,
            )
        )
        rendered = self._presenter.render(reply)
        if reply.kind is not ReplyKind.IGNORED:
            event.stop_event()
        return rendered
