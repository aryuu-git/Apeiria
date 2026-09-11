"""AstrBot entry point for the Apeiria thin adapter."""

import asyncio
import json
import logging
import time
from pathlib import Path
from random import Random
from typing import Any

from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from anime_party import (
    EXPRESSION_CONTRACT,
    AiGamePresenter,
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)
from apeiria_core import (
    COMPANION_CONTRACT,
    DEFAULT_PERSONA_PROMPT,
    CompanionService,
    EventSink,
    GroupControlPolicy,
    LlmTransport,
    OpenAICompatibleTransport,
    SQLiteStateStore,
    build_persona_prompt,
)

from .adapter import GAME_ACTION_EXPRESSIONS, ApeiriaEventAdapter

logger = logging.getLogger("apeiria")


@star.register(
    "astrbot_plugin_apeiria",
    "aryuu-git",
    "Apeiria companion and anime party adapter",
    "0.1.0",
)
class ApeiriaPlugin(star.Star):
    """Connect AstrBot message events to the Apeiria domain core."""

    def __init__(self, context: star.Context, config: dict | None = None) -> None:
        super().__init__(context, config)
        settings = config or {}
        self._enabled = bool(settings.get("enabled", True))
        state_store = SQLiteStateStore(
            Path(get_astrbot_data_path()) / "plugin_data" / self.name / "state.db",
            event_retention_seconds=float(settings.get("event_retention_days", 7))
            * 86400.0,
        )
        self._event_sink: EventSink = state_store
        transport = self._build_transport(settings)
        fallback_presenter = ChineseGamePresenter(random=Random())
        persona_prompt = build_persona_prompt(
            Path(str(settings.get("persona_dir", "")).strip())
            if str(settings.get("persona_dir", "")).strip()
            else None
        ) or DEFAULT_PERSONA_PROMPT
        engine = AnimePartyEngine(
            load_questions(default_questions_path()),
            recent_limit=int(settings.get("recent_question_limit", 8)),
            handled_message_limit=int(settings.get("handled_message_limit", 4096)),
            state_store=state_store,
            round_timeout_seconds=float(settings.get("round_timeout_minutes", 15))
            * 60.0,
        )
        allowed_group_ids = {
            str(group_id).strip()
            for group_id in settings.get("allowed_group_ids", [])
            if str(group_id).strip()
        }
        admin_ids = {
            str(admin_id).strip()
            for admin_id in settings.get("admin_ids", [])
            if str(admin_id).strip()
        }
        owner_ids = {
            str(owner_id).strip()
            for owner_id in settings.get("owner_ids", [])
            if str(owner_id).strip()
        }
        self._companion = self._build_companion(
            settings, state_store, owner_ids, transport, persona_prompt
        )
        self._expression = self._build_expression(
            settings, fallback_presenter, transport, persona_prompt
        )
        self._adapter = ApeiriaEventAdapter(
            engine,
            fallback_presenter,
            allowed_group_ids=allowed_group_ids,
            group_control=GroupControlPolicy(
                admin_ids,
                handled_message_limit=int(settings.get("handled_message_limit", 4096)),
                state_store=state_store,
            ),
            companion=self._companion,
            event_sink=self._event_sink,
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def on_message(self, event: AstrMessageEvent):
        """Handle deterministic game messages, then optional presence replies.

        Args:
            event: AstrBot message event.

        Yields:
            AstrBot text results for each rendered domain message.
        """

        if not self._enabled:
            return
        result = self._adapter.handle(event)
        messages = result.messages
        if result.consumed and result.reply is not None and self._expression is not None:
            started = time.perf_counter()
            expressed = await asyncio.to_thread(
                self._expression.render,
                result.reply,
                sender_name=result.sender_name,
            )
            self._emit(
                "game.expression",
                event.unified_msg_origin,
                {
                    "kind": result.reply.kind.value,
                    "fallback": expressed == messages,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            messages = expressed
        for message in messages:
            yield event.plain_result(message)
        if result.companion_eligible and self._companion is not None:
            started = time.perf_counter()
            decision = await asyncio.to_thread(
                self._companion.decide,
                event.unified_msg_origin,
                event.get_sender_id(),
                result.sender_name,
                event.message_str,
                mentioned=result.mentioned,
                called=result.called,
                game_context=result.state,
            )
            self._emit(
                "companion.decision",
                event.unified_msg_origin,
                {
                    "speak": decision.speak,
                    "text": decision.text,
                    "action": decision.action,
                    "error": decision.error,
                    "mentioned": result.mentioned,
                    "sender_name": result.sender_name,
                    "game": result.state,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            if decision.speak and decision.text:
                yield event.plain_result(decision.text)
            if decision.action is not None:
                expression = GAME_ACTION_EXPRESSIONS[decision.action]
                for message in self._adapter.run_game_expression(event, expression):
                    yield event.plain_result(message)

    def _emit(self, kind: str, session_id: str, payload: dict[str, Any]) -> None:
        """Fan one lifecycle event out to the sink and the runtime log."""
        line = json.dumps(payload, ensure_ascii=False)
        try:
            self._event_sink.append_event(kind, session_id, payload)
        except Exception:  # observability must never break the product
            logger.exception("event sink failed for %s", kind)
        logger.info("[%s] %s", kind, line)

    def _build_transport(self, settings: dict) -> LlmTransport | None:
        """Build the shared LLM transport, or ``None`` unless configured."""
        base_url = str(settings.get("ai_base_url", "")).strip()
        api_key = str(settings.get("ai_api_key", "")).strip()
        if not (base_url and api_key):
            return None
        return OpenAICompatibleTransport(base_url=base_url, api_key=api_key)

    def _build_companion(
        self,
        settings: dict,
        state_store: SQLiteStateStore,
        owner_ids: set[str],
        transport: LlmTransport | None,
        persona_prompt: str,
    ) -> CompanionService | None:
        """Build the presence service, or ``None`` unless fully configured."""
        if transport is None or not bool(settings.get("ai_enabled", False)):
            return None
        model = str(settings.get("ai_model", "")).strip()
        if not model:
            return None
        return CompanionService(
            transport,
            state_store,
            model=model,
            owner_ids=owner_ids,
            system_prompt=persona_prompt + "\n\n" + COMPANION_CONTRACT,
            autonomous_rate_limit=int(settings.get("ai_autonomous_rate_limit", 5)),
            rate_window_seconds=float(settings.get("ai_rate_window_minutes", 10))
            * 60.0,
            retention_seconds=float(settings.get("ai_history_retention_days", 30))
            * 86400.0,
            prompt_limit=int(settings.get("ai_prompt_context_limit", 20)),
        )

    def _build_expression(
        self,
        settings: dict,
        fallback: ChineseGamePresenter,
        transport: LlmTransport | None,
        persona_prompt: str,
    ) -> AiGamePresenter | None:
        """Build the AI expression layer, or ``None`` unless fully configured."""
        if transport is None or not bool(settings.get("ai_enabled", False)):
            return None
        if not bool(settings.get("ai_expressions_enabled", True)):
            return None
        model = str(settings.get("ai_model", "")).strip()
        if not model:
            return None
        return AiGamePresenter(
            transport,
            fallback,
            model=model,
            system_prompt=persona_prompt + "\n\n" + EXPRESSION_CONTRACT,
        )
