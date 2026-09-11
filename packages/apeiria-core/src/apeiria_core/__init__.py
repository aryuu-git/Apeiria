"""Platform-independent Apeiria domain primitives."""

from .companion import (
    COMPANION_CONTRACT,
    DEFAULT_PERSONA_PROMPT,
    DEFAULT_TRIGGERS,
    CompanionDecision,
    CompanionService,
    ContextEntry,
    LlmTransport,
    LlmTransportError,
    OpenAICompatibleTransport,
)
from .group_control import ControlDecision, GroupControlPolicy
from .messages import IncomingMessage
from .persona import build_persona_prompt
from .state_store import EventSink, SQLiteStateStore, StateStore

__all__ = [
    "COMPANION_CONTRACT",
    "CompanionDecision",
    "CompanionService",
    "ContextEntry",
    "ControlDecision",
    "DEFAULT_PERSONA_PROMPT",
    "DEFAULT_TRIGGERS",
    "EventSink",
    "GroupControlPolicy",
    "IncomingMessage",
    "LlmTransport",
    "LlmTransportError",
    "OpenAICompatibleTransport",
    "SQLiteStateStore",
    "StateStore",
    "build_persona_prompt",
]
