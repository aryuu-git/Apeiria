"""Platform-independent Apeiria domain primitives."""

from .companion import (
    DEFAULT_TRIGGERS,
    CompanionService,
    ContextEntry,
    LlmTransport,
    LlmTransportError,
    OpenAICompatibleTransport,
)
from .group_control import ControlDecision, GroupControlPolicy
from .messages import IncomingMessage
from .state_store import SQLiteStateStore, StateStore

__all__ = [
    "CompanionService",
    "ContextEntry",
    "ControlDecision",
    "DEFAULT_TRIGGERS",
    "GroupControlPolicy",
    "IncomingMessage",
    "LlmTransport",
    "LlmTransportError",
    "OpenAICompatibleTransport",
    "SQLiteStateStore",
    "StateStore",
]
