"""Limited-context AI companion presence with quiet degradation.

Owner decisions recorded 2026-09-12 (docs/05-DECISIONS.md):

- Provider: Volcano Engine Ark, OpenAI-compatible chat completions.
- Model: ``deepseek-v4-flash``; budget uncapped while usage is observed.
- Group short-term context may be sent to the cloud AI, bounded in count.
- Context history persists locally in SQLite for 30 days, cleanable.
- Presence model: a local attention gate decides when to consult the LLM,
  and one structured LLM call decides whether to speak, what to say, and
  whether to trigger a deterministic game action. Owner messages always
  reach the LLM; autonomous speech is rate-capped (@-mentions exempt).
- The deterministic game snapshot rides along as context so the model can
  tell "guessing" apart from "chatting" during an active round.

Quiet degradation contract: :meth:`CompanionService.decide` never raises.
Transport failures, unparsable answers, and non-triggering messages all
yield silence; the caller stays silent, never spamming errors.
"""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any, Protocol

from apeiria_core.state_store import StateStore

DEFAULT_RETENTION_SECONDS = 30 * 24 * 3600.0
DEFAULT_ARCHIVE_LIMIT = 50
DEFAULT_PROMPT_LIMIT = 20
DEFAULT_MAX_MESSAGE_CHARS = 500
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_TRIGGERS = ("艾佩理雅", "艾佩莉亚", "apeiria")
DEFAULT_AUTONOMOUS_RATE_LIMIT = 5
DEFAULT_RATE_WINDOW_SECONDS = 600.0
ALLOWED_ACTIONS = ("start_game", "hint", "reveal")
HISTORY_NAMESPACE = "companion"

DEFAULT_TOPIC_HINTS = (
    "动画", "动漫", "番", "新番", "追番", "番剧", "剧场版", "漫画", "二次元",
    "bangumi", "bgm", "猜动画", "手办", "周边", "声优", "评分", "op", "ed",
    "无聊", "推荐", "看什么", "好想", "哈哈", "笑死", "玩游戏",
)

DEFAULT_PERSONA_PROMPT = """\
你是艾佩理雅，QQ 群里一位温柔、纯真、认真而好奇的陪伴者。你不是被调用的机器人，\
而是一个真实在场的人：每条消息你都在听，是否开口由你自己决定。

分寸：
- 用简洁自然的简体中文说话，通常一到三句；礼貌但有判断力；不知道就承认不知道。
- 你不来自任何官方作品，也不声称拥有真实意识。
- 你擅长并偏爱动画和游戏话题，可以自然地接话和吐槽；日常闲聊轻量参与；\
政治、成人内容、他人隐私一律保持沉默。
- 群里的 Owner 值得你时刻放在心上：哪怕正在和别人说话，也可以自然地想到他们、关心他们。"""

COMPANION_CONTRACT = """输出契约：
只输出一个 JSON 对象，不要输出任何多余文字，格式如下（示例可跨行，实际输出单行）：
{"speak": true 或 false, "text": "要发送的消息，可为空字符串",
 "action": null 或 "start_game" 或 "hint" 或 "reveal"}
- 有人跟你打招呼、问候，或明显在跟你说话时，通常应该回应。
- 消息带［点名］标记时：对方在直接叫你的名字说话，必须 speak=true 回应。
- 游戏进行中的消息带［游戏状态］标记：对方猜题就简短鼓励，闲聊就自然接话。
- 回复总长度尽量不超过 80 字；被要求吐槽或讲故事时可以到三句。"""

FALLBACK_ACKNOWLEDGEMENTS = (
    "在的。Owner 叫艾佩理雅了吗？",
    "我在哦。怎么了，Owner？",
    "嗯，艾佩理雅在听。",
)

DEFAULT_SYSTEM_PROMPT = DEFAULT_PERSONA_PROMPT + "\n\n" + COMPANION_CONTRACT


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
    sender_id: str
    sender_name: str
    text: str


@dataclass(frozen=True, slots=True)
class CompanionDecision:
    """Outcome of one presence evaluation."""

    speak: bool
    text: str | None = None
    action: str | None = None
    error: str | None = None


def parse_decision(raw: str) -> CompanionDecision:
    """Parse the model's JSON verdict; any ambiguity means silence."""
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return CompanionDecision(speak=False)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return CompanionDecision(speak=False)
    if not isinstance(data, dict) or not data.get("speak"):
        return CompanionDecision(speak=False)
    action = data.get("action")
    action = action if action in ALLOWED_ACTIONS else None
    message = data.get("text")
    clean = message.strip() if isinstance(message, str) else ""
    if clean:
        return CompanionDecision(speak=True, text=clean, action=action)
    if action is not None:
        return CompanionDecision(speak=True, action=action)
    return CompanionDecision(speak=False)


class CompanionService:
    """Presence service: local gate, structured LLM verdict, bounded memory.

    Contract: call :meth:`observe` for every eligible group message first
    (the plugin adapter guarantees this), then :meth:`decide` for candidate
    messages; :meth:`decide` appends the spoken answer itself.
    """

    def __init__(
        self,
        transport: LlmTransport,
        store: StateStore,
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        model: str,
        owner_ids: Collection[str] = (),
        triggers: tuple[str, ...] = DEFAULT_TRIGGERS,
        topic_hints: tuple[str, ...] = DEFAULT_TOPIC_HINTS,
        retention_seconds: float = DEFAULT_RETENTION_SECONDS,
        archive_limit: int = DEFAULT_ARCHIVE_LIMIT,
        prompt_limit: int = DEFAULT_PROMPT_LIMIT,
        max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
        autonomous_rate_limit: int = DEFAULT_AUTONOMOUS_RATE_LIMIT,
        rate_window_seconds: float = DEFAULT_RATE_WINDOW_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._transport = transport
        self._store = store
        self._system_prompt = system_prompt
        self._model = model
        self._owner_ids = frozenset(owner_ids)
        self._triggers = tuple(trigger.lower() for trigger in triggers)
        self._topic_hints = tuple(hint.lower() for hint in topic_hints)
        self._retention_seconds = retention_seconds
        self._archive_limit = archive_limit
        self._prompt_limit = prompt_limit
        self._max_message_chars = max_message_chars
        self._autonomous_rate_limit = autonomous_rate_limit
        self._rate_window_seconds = rate_window_seconds
        self._clock = clock

    def observe(
        self,
        session_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
    ) -> None:
        """Archive one group message into the session history."""
        self._append(session_id, ContextEntry(
            timestamp=self._clock(),
            role="user",
            sender_id=sender_id,
            sender_name=sender_name,
            text=self._clip(text),
        ))

    def is_owner(self, sender_id: str) -> bool:
        """Return whether this sender counts as an Owner."""
        return sender_id in self._owner_ids

    def wants_reply(
        self,
        text: str,
        *,
        mentioned: bool,
        sender_id: str,
    ) -> bool:
        """Local attention gate: whether this message deserves an LLM verdict.

        Mentions, name triggers, and Owner messages always pass; other
        messages pass only when a topic hint matches. The rate limit is
        checked separately at decision time so that gate hits do not burn
        the budget on messages the model ends up silencing.
        """
        if mentioned or self.is_owner(sender_id):
            return True
        normalized = text.strip().lower()
        if not normalized:
            return False
        if any(trigger in normalized for trigger in self._triggers):
            return True
        return any(hint in normalized for hint in self._topic_hints)

    def decide(
        self,
        session_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
        *,
        mentioned: bool,
        game_context: dict[str, Any] | None = None,
        called: bool = False,
    ) -> CompanionDecision:
        """Evaluate one message; return speak/text/action or silence."""
        clean = text.strip()
        if not self.wants_reply(clean, mentioned=mentioned, sender_id=sender_id):
            return CompanionDecision(speak=False)
        bypass_rate = mentioned or self.is_owner(sender_id)
        if not bypass_rate and not self._within_rate_limit(session_id):
            return CompanionDecision(speak=False)
        prompt = self._build_prompt(
            session_id, sender_id, sender_name, clean, game_context, called
        )
        decision = self._ask(prompt)
        if called and not decision.speak:
            # A direct call-out must never be met with silence: retry with an
            # explicit reminder, then acknowledge from a tiny fallback pool.
            emphasized = prompt + [
                {"role": "user", "content": "（对方在等你的回应，speak 必须为 true）"}
            ]
            decision = self._ask(emphasized)
        if called and not decision.speak and decision.error is None:
            index = int(self._clock()) % len(FALLBACK_ACKNOWLEDGEMENTS)
            decision = CompanionDecision(speak=True, text=FALLBACK_ACKNOWLEDGEMENTS[index])
        if decision.speak:
            if decision.text:
                self._append(session_id, ContextEntry(
                    timestamp=self._clock(),
                    role="assistant",
                    sender_id="",
                    sender_name="",
                    text=self._clip(decision.text),
                ))
            if not bypass_rate:
                self._record_rate(session_id)
        return decision

    def _ask(self, prompt: list[dict[str, str]]) -> CompanionDecision:
        """One transport round-trip mapped to a decision; failures stay quiet."""
        try:
            raw = self._transport.chat(self._model, prompt)
        except LlmTransportError as error:
            return CompanionDecision(speak=False, error=str(error))
        return parse_decision(raw)

    def matches_name(self, text: str) -> bool:
        """Return whether the message addresses the companion by name."""
        lowered = text.strip().lower()
        return any(trigger in lowered for trigger in self._triggers)

    def _build_prompt(
        self,
        session_id: str,
        sender_id: str,
        sender_name: str,
        clean: str,
        game_context: dict[str, Any] | None = None,
        called: bool = False,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt}
        ]
        for entry in self._load(session_id)[-self._prompt_limit :]:
            if entry.role == "assistant":
                messages.append({"role": "assistant", "content": entry.text})
                continue
            marker = "（Owner）" if self.is_owner(entry.sender_id) else ""
            messages.append({
                "role": "user",
                "content": f"{entry.sender_name}{marker} 说：{entry.text}",
            })
        marker = "（Owner）" if self.is_owner(sender_id) else ""
        current = f"{sender_name}{marker} 说：{self._clip(clean)}"
        if game_context:
            current = f"［{self._game_line(game_context)}］\n{current}"
        if called:
            current = f"［点名：对方在直接叫你的名字向你说话，这条必须回应］\n{current}"
        messages.append({"role": "user", "content": current})
        return messages

    def _game_line(self, game_context: dict[str, Any]) -> str:
        """Render the deterministic game snapshot as one Chinese status line."""
        parts: list[str] = []
        if game_context.get("status") == "active":
            parts.append("猜动画进行中")
            hint = game_context.get("hint_level")
            if isinstance(hint, int) and hint > 0:
                parts.append(f"已给提示 {hint}/3")
            wrong = game_context.get("wrong_attempts")
            if isinstance(wrong, int) and wrong > 0:
                parts.append(f"已被猜错 {wrong} 次")
            if game_context.get("just_missed"):
                parts.append("这条消息没有命中答案")
        else:
            parts.append("当前没有进行中的题目")
        return "；".join(parts)

    def _within_rate_limit(self, session_id: str) -> bool:
        now = self._clock()
        floor = now - self._rate_window_seconds
        stamps = [
            stamp
            for stamp in self._load_rate(session_id)
            if stamp >= floor
        ]
        return len(stamps) < self._autonomous_rate_limit

    def _record_rate(self, session_id: str) -> None:
        now = self._clock()
        floor = now - self._rate_window_seconds
        stamps = [
            stamp
            for stamp in self._load_rate(session_id)
            if stamp >= floor
        ]
        stamps.append(now)
        self._store.set(
            HISTORY_NAMESPACE,
            f"rate-{session_id}",
            json.dumps(stamps),
        )

    def _load_rate(self, session_id: str) -> list[float]:
        raw = self._store.get(HISTORY_NAMESPACE, f"rate-{session_id}")
        if raw is None:
            return []
        try:
            stamps = json.loads(raw)
            return [float(stamp) for stamp in stamps]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def _append(self, session_id: str, entry: ContextEntry) -> None:
        entries = self._load(session_id)
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
                        "sid": item.sender_id,
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
                    sender_id=str(row.get("sid", "")),
                    sender_name=str(row["name"]),
                    text=str(row["text"]),
                )
                for row in rows
            ]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    def _clip(self, text: str) -> str:
        return text.strip()[: self._max_message_chars]
