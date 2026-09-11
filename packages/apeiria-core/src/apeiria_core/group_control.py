"""Deterministic group-level access and silence controls."""

from collections.abc import Collection
from dataclasses import dataclass

from .messages import IncomingMessage


@dataclass(frozen=True, slots=True)
class ControlDecision:
    """Describe whether a message may continue to product handlers."""

    allow: bool
    response: str | None = None


class GroupControlPolicy:
    """Apply administrator-only, in-memory group silence controls."""

    SILENCE_COMMANDS = frozenset({"艾佩理雅静默", "机器人静默"})
    RESUME_COMMANDS = frozenset({"艾佩理雅恢复", "机器人恢复"})

    def __init__(self, admin_ids: Collection[str], *, handled_message_limit: int = 4096) -> None:
        if handled_message_limit < 1:
            raise ValueError("handled_message_limit must be positive")
        self._admin_ids = frozenset(admin_ids)
        self._silent_sessions: set[str] = set()
        self._handled_message_limit = handled_message_limit
        self._handled_messages: dict[tuple[str, str], None] = {}

    def evaluate(self, message: IncomingMessage) -> ControlDecision:
        """Evaluate one normalized message before other domain handlers."""

        identity = (message.session_id, message.message_id)
        if identity in self._handled_messages:
            return ControlDecision(False)
        self._handled_messages[identity] = None
        if len(self._handled_messages) > self._handled_message_limit:
            oldest = next(iter(self._handled_messages))
            del self._handled_messages[oldest]

        text = message.text.strip()
        is_admin = message.sender_id in self._admin_ids

        if text in self.SILENCE_COMMANDS:
            if not is_admin:
                return ControlDecision(False, "只有管理员可以让我进入静默。")
            self._silent_sessions.add(message.session_id)
            return ControlDecision(False, "好的，我会保持安静。管理员说“艾佩理雅恢复”时我再回来。")

        if text in self.RESUME_COMMANDS:
            if not is_admin:
                return ControlDecision(False, "只有管理员可以解除静默。")
            self._silent_sessions.discard(message.session_id)
            return ControlDecision(False, "我回来了。")

        return ControlDecision(message.session_id not in self._silent_sessions)
