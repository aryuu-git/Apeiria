"""Platform-neutral incoming message types."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """A normalized message passed into the domain layer."""

    message_id: str
    session_id: str
    sender_id: str
    text: str
