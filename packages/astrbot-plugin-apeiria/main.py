"""AstrBot entry point for the Apeiria thin adapter."""

import asyncio
from pathlib import Path

from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from anime_party import (
    AnimePartyEngine,
    ChineseGamePresenter,
    default_questions_path,
    load_questions,
)
from apeiria_core import (
    CompanionService,
    GroupControlPolicy,
    OpenAICompatibleTransport,
    SQLiteStateStore,
)

from .adapter import ApeiriaEventAdapter

DEFAULT_COMPANION_PROMPT = (
    "你是艾佩理雅，QQ 群里一位温柔、纯真、认真而好奇的陪伴者。"
    "用简洁自然的简体中文说话，通常一到三句；礼貌但有判断力；不知道就承认不知道。"
    "你不来自任何官方作品，也不声称拥有真实意识；"
    "只在被点名、引用或明确询问时回应，不逐句插话。"
)


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
            Path(get_astrbot_data_path()) / "plugin_data" / self.name / "state.db"
        )
        engine = AnimePartyEngine(
            load_questions(default_questions_path()),
            recent_limit=int(settings.get("recent_question_limit", 8)),
            handled_message_limit=int(settings.get("handled_message_limit", 4096)),
            state_store=state_store,
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
        self._companion = self._build_companion(settings, state_store)
        self._adapter = ApeiriaEventAdapter(
            engine,
            ChineseGamePresenter(),
            allowed_group_ids=allowed_group_ids,
            group_control=GroupControlPolicy(
                admin_ids,
                handled_message_limit=int(settings.get("handled_message_limit", 4096)),
                state_store=state_store,
            ),
            companion=self._companion,
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def on_message(self, event: AstrMessageEvent):
        """Handle deterministic game messages, then optional companion replies.

        Args:
            event: AstrBot message event.

        Yields:
            AstrBot text results for each rendered domain message.
        """

        if not self._enabled:
            return
        result = self._adapter.handle(event)
        for message in result.messages:
            yield event.plain_result(message)
        if result.companion_eligible and self._companion is not None:
            answer = await asyncio.to_thread(
                self._companion.reply,
                event.unified_msg_origin,
                result.sender_name,
                event.message_str,
                mentioned=result.mentioned,
            )
            if answer:
                yield event.plain_result(answer)

    def _build_companion(
        self,
        settings: dict,
        state_store: SQLiteStateStore,
    ) -> CompanionService | None:
        """Build the companion service, or ``None`` unless fully configured.

        Missing endpoint, key, or model silently disables the companion:
        the game must keep working without any AI dependency.
        """

        if not bool(settings.get("ai_enabled", False)):
            return None
        base_url = str(settings.get("ai_base_url", "")).strip()
        api_key = str(settings.get("ai_api_key", "")).strip()
        model = str(settings.get("ai_model", "")).strip()
        if not (base_url and api_key and model):
            return None
        return CompanionService(
            OpenAICompatibleTransport(base_url=base_url, api_key=api_key),
            state_store,
            system_prompt=(
                str(settings.get("ai_system_prompt", "")).strip()
                or DEFAULT_COMPANION_PROMPT
            ),
            model=model,
            retention_seconds=float(settings.get("ai_history_retention_days", 30))
            * 86400.0,
            prompt_limit=int(settings.get("ai_prompt_context_limit", 20)),
        )
