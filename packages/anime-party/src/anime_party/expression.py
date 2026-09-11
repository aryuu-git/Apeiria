"""LLM-powered game expression with deterministic template fallbacks.

Architecture: the state machine stays the sole authority over game
decisions (correctness, hint levels, progress); this layer only rewords
the *expression* of an already-decided reply. Two safeguards:

- Information boundary: the LLM context per reply kind never includes the
  answer title unless the reply itself is a reveal, so the model cannot
  leak the answer while rewording hints or wrong-answer nudges.
- Quiet fallback: transport failure, unparsable output, or an empty
  phrase falls back to the deterministic template rendering.

Phrase modes: "full" kinds are entirely reworded; "lead" kinds keep the
fixed data line (emoji question, hint text, answer reveal) untouched and
only prepend a short LLM-generated lead-in.
"""

import json
from typing import Any

from apeiria_core import LlmTransport, LlmTransportError

from .engine import GameReply, ReplyKind
from .models import Difficulty
from .presentation import ChineseGamePresenter

EXPRESSION_CONTRACT = """现在要把一条游戏系统的回复说得像你本人在群里说话。

规则：
- 自然简洁，一到两句，可以带一点情绪或小吐槽。
- 绝不新增任何题目线索或剧透；绝不改变、省略 data 中给出的固定信息。
- data 里没有的信息就是不能提的。

只输出一个 JSON 对象，不要输出任何多余文字：
- full 模式：{"text": "整句回复"}
- lead 模式：{"lead": "不超过 15 字的引子短语，以逗号或波浪号结尾",
  "注释": "引子后面会直接接上固定信息"}
"""

EXPRESSION_SYSTEM_PROMPT = (
    "你是艾佩理雅，QQ 群里温柔、纯真、认真而好奇的陪伴者。\n\n"
    + EXPRESSION_CONTRACT
)

FULL_KINDS = frozenset({
    ReplyKind.WRONG_ANSWER,
    ReplyKind.HINTS_EXHAUSTED,
    ReplyKind.NO_ACTIVE_QUESTION,
    ReplyKind.PAUSED,
})
LEAD_KINDS = frozenset({
    ReplyKind.QUESTION,
    ReplyKind.HINT,
    ReplyKind.DIFFICULTY_CHANGED,
    ReplyKind.CORRECT_ANSWER,
    ReplyKind.REVEALED,
})

_DIFFICULTY_LABELS = {
    Difficulty.EASY: "简单",
    Difficulty.NORMAL: "普通",
    Difficulty.HARD: "困难",
}


def _extract_phrase(raw: str) -> str | None:
    """Pull the text/lead phrase out of the model verdict; ambiguity → None."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("text") if isinstance(data.get("text"), str) else data.get("lead")
    if not isinstance(value, str):
        return None
    clean = value.strip()
    return clean or None


class AiGamePresenter:
    """Decorator over the template presenter that rewords replies via LLM."""

    def __init__(
        self,
        transport: LlmTransport,
        fallback: ChineseGamePresenter,
        *,
        model: str,
        system_prompt: str = EXPRESSION_SYSTEM_PROMPT,
    ) -> None:
        self._transport = transport
        self._fallback = fallback
        self._model = model
        self._system_prompt = system_prompt

    def render(self, reply: GameReply, *, sender_name: str = "") -> tuple[str, ...]:
        """Render one reply; the LLM rewords it or the templates answer."""
        fallback = self._fallback.render(reply)
        if reply.kind is ReplyKind.IGNORED:
            return fallback
        payload = self._context_for(reply, sender_name)
        if payload is None:
            return fallback
        mode = "full" if reply.kind in FULL_KINDS else "lead"
        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": json.dumps({"mode": mode, **payload}, ensure_ascii=False),
            },
        ]
        try:
            raw = self._transport.chat(self._model, messages)
        except LlmTransportError:
            return fallback
        phrase = _extract_phrase(raw)
        if phrase is None:
            return fallback
        if mode == "full":
            return (phrase,)
        return (f"{phrase}{fallback[0]}", *fallback[1:])

    def _context_for(self, reply: GameReply, sender_name: str) -> dict[str, Any] | None:
        """Build the visible context; fields omitted here are unmentionable."""
        question = reply.question
        kind = reply.kind
        event = f"刚刚 {sender_name}：" if sender_name else "刚刚："
        if kind is ReplyKind.WRONG_ANSWER:
            return {
                "mode": "full",
                "event": f"{event}猜错了一次，游戏继续",
                "emoji": question.emoji if question else "",
            }
        if kind is ReplyKind.HINTS_EXHAUSTED:
            return {"mode": "full", "event": f"{event}要提示，但三层提示已经给完"}
        if kind is ReplyKind.NO_ACTIVE_QUESTION:
            return {"mode": "full", "event": f"{event}要提示，但现在没有进行中的题目"}
        if kind is ReplyKind.PAUSED:
            return {"mode": "full", "event": "游戏被暂停了"}
        if kind is ReplyKind.QUESTION:
            return {
                "mode": "lead",
                "event": f"{event}要了一个新题，emoji 猜动画题已出",
                "emoji": question.emoji if question else "",
            }
        if kind is ReplyKind.HINT:
            return {
                "mode": "lead",
                "event": f"{event}要了第 {reply.hint_level} 层提示",
                "hint": reply.hint or "",
            }
        if kind is ReplyKind.DIFFICULTY_CHANGED:
            label = (
                _DIFFICULTY_LABELS[reply.difficulty]
                if reply.difficulty is not None
                else ""
            )
            return {
                "mode": "lead",
                "event": f"{event}把难度切到了{label}，新题已出",
                "emoji": question.emoji if question else "",
            }
        if kind is ReplyKind.CORRECT_ANSWER:
            return {
                "mode": "lead",
                "event": f"{event}答对了！",
                "title": question.title if question else "",
                "explanation": question.explanation if question else "",
            }
        if kind is ReplyKind.REVEALED:
            return {
                "mode": "lead",
                "event": f"{event}要求公布答案",
                "title": question.title if question else "",
                "explanation": question.explanation if question else "",
            }
        return None
