"""Limited-context AI companion replies with quiet degradation.

Owner decisions recorded 2026-09-12 (docs/05-DECISIONS.md):

- Provider: Volcano Engine Ark, OpenAI-compatible chat completions.
- Model: ``deepseek-v4-flash``; budget uncapped while usage is observed.
- Group short-term context may be sent to the cloud AI, bounded in count.
- Context history persists locally in SQLite for 30 days, cleanable.

Quiet degradation contract: :meth:`CompanionService.reply` never raises.
Transport failures, empty answers, and non-triggering messages all yield
``None``; the caller stays silent, matching the product rule of never
spamming errors into the group.
"""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from apeiria_core.state_store import StateStore

DEFAULT_RETENTION_SECONDS = 30 * 24 * 3600.0
DEFAULT_ARCHIVE_LIMIT = 50
DEFAULT_PROMPT_LIMIT = 20
DEFAULT_MAX_MESSAGE_CHARS = 500
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_TRIGGERS = ("艾佩理雅", "艾佩莉亚", "apeiria")
HISTORY_NAMESPACE = "companion"


class LlmTransportError(RuntimeError):
    """Raised by transports on any failure; never escapes the service."""


class LlmTransport(Protocol):
    """Minimal chat transport required by :class:`CompanionService`."""

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        """Return the assistant text or raise :class:`LlmTransportError`."""


def _build_opener(proxy: str | None) -> urllib.request.OpenerDirector:
    if proxy is None:
        return urllib.request.build_opener()
    if proxy == "":
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    )


class OpenAICompatibleTransport:
    """Stdlib transport for OpenAI-compatible chat completions endpoints.

    ``proxy=None`` keeps urllib's default behavior (Windows system proxy and
    proxy environment variables). Pass ``proxy=""`` to force direct
    connections, or an explicit URL such as ``http://127.0.0.1:7890``.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        proxy: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._opener = _build_opener(proxy)

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"model": model, "messages": messages}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "aryuu-git/Apeiria/0.1 (https://github.com/aryuu-git/Apeiria)",
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise LlmTransportError(f"HTTP {error.code} from chat completions") from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise LlmTransportError(f"chat completions unreachable: {error}") from error
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmTransportError("unexpected chat completions response") from error
        if not isinstance(content, str):
            raise LlmTransportError("chat completions content is not text")
        return content


@dataclass(frozen=True, slots=True)
class ContextEntry:
    """One archived group message used to build limited context."""

    timestamp: float
    role: str
    sender_name: str
    text: str


class CompanionService:
    """Trigger-gated AI replies over a bounded, TTL-pruned group history.

    Contract: call :meth:`observe` for every eligible group message first
    (the plugin adapter guarantees this), then :meth:`reply` only for
    candidate replies; :meth:`reply` appends the assistant answer itself.
    """

    def __init__(
        self,
        transport: LlmTransport,
        store: StateStore,
        *,
        system_prompt: str,
        model: str,
        triggers: tuple[str, ...] = DEFAULT_TRIGGERS,
        retention_seconds: float = DEFAULT_RETENTION_SECONDS,
        archive_limit: int = DEFAULT_ARCHIVE_LIMIT,
        prompt_limit: int = DEFAULT_PROMPT_LIMIT,
        max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._transport = transport
        self._store = store
        self._system_prompt = system_prompt
        self._model = model
        self._triggers = tuple(trigger.lower() for trigger in triggers)
        self._retention_seconds = retention_seconds
        self._archive_limit = archive_limit
        self._prompt_limit = prompt_limit
        self._max_message_chars = max_message_chars
        self._clock = clock

    def observe(self, session_id: str, sender_name: str, text: str) -> None:
        """Archive one group message into the session history."""
        self._append(session_id, ContextEntry(
            timestamp=self._clock(),
            role="user",
            sender_name=sender_name,
            text=self._clip(text),
        ))

    def wants_reply(self, text: str, *, mentioned: bool) -> bool:
        """Return whether this message explicitly invites a reply."""
        if mentioned:
            return True
        normalized = text.strip().lower()
        return bool(normalized) and any(trigger in normalized for trigger in self._triggers)

    def reply(
        self,
        session_id: str,
        sender_name: str,
        text: str,
        *,
        mentioned: bool,
    ) -> str | None:
        """Return one companion reply, or ``None`` to stay silent."""
        clean = text.strip()
        if not self.wants_reply(clean, mentioned=mentioned):
            return None
        prompt = [
            {"role": "system", "content": self._system_prompt},
            *(
                {
                    "role": entry.role,
                    "content": (
                        entry.text
                        if entry.role == "assistant"
                        else f"{entry.sender_name} 说：{entry.text}"
                    ),
                }
                for entry in self._load(session_id)[-self._prompt_limit :]
            ),
            {"role": "user", "content": f"{sender_name} 说：{self._clip(clean)}"},
        ]
        try:
            answer = self._transport.chat(self._model, prompt).strip()
        except LlmTransportError:
            return None
        if not answer:
            return None
        self._append(session_id, ContextEntry(
            timestamp=self._clock(),
            role="assistant",
            sender_name="",
            text=self._clip(answer),
        ))
        return answer

    def _append(self, session_id: str, entry: ContextEntry) -> None:
        entries = [item for item in self._load(session_id) if item is not None]
        entries.append(entry)
        floor = self._clock() - self._retention_seconds
        entries = [item for item in entries if item.timestamp >= floor]
        entries = entries[-self._archive_limit :]
        payload = json.dumps(
            {
                "entries": [
                    {
                        "t": item.timestamp,
                        "role": item.role,
                        "name": item.sender_name,
                        "text": item.text,
                    }
                    for item in entries
                ]
            }
        )
        self._store.set(HISTORY_NAMESPACE, f"context-{session_id}", payload)

    def _load(self, session_id: str) -> list[ContextEntry]:
        raw = self._store.get(HISTORY_NAMESPACE, f"context-{session_id}")
        if raw is None:
            return []
        try:
            rows = json.loads(raw)["entries"]
            return [
                ContextEntry(
                    timestamp=float(row["t"]),
                    role=str(row["role"]),
                    sender_name=str(row["name"]),
                    text=str(row["text"]),
                )
                for row in rows
            ]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    def _clip(self, text: str) -> str:
        return text.strip()[: self._max_message_chars]


def companion_settings_from(config: dict[str, Any]) -> dict[str, Any]:
    """Extract the ``ai_*`` plugin settings shared by adapter and entry point."""
    return {
        "enabled": bool(config.get("ai_enabled", False)),
        "base_url": str(config.get("ai_base_url", "")).strip(),
        "api_key": str(config.get("ai_api_key", "")).strip(),
        "model": str(config.get("ai_model", "")).strip(),
        "system_prompt": str(config.get("ai_system_prompt", "")).strip(),
        "retention_days": int(config.get("ai_history_retention_days", 30)),
        "prompt_limit": int(config.get("ai_prompt_context_limit", 20)),
    }
