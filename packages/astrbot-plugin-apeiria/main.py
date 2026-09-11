"""AstrBot entry point for the Apeiria thin adapter."""

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
from apeiria_core import GroupControlPolicy, SQLiteStateStore

from .adapter import ApeiriaEventAdapter


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
        self._adapter = ApeiriaEventAdapter(
            engine,
            ChineseGamePresenter(),
            allowed_group_ids=allowed_group_ids,
            group_control=GroupControlPolicy(
                admin_ids,
                handled_message_limit=int(settings.get("handled_message_limit", 4096)),
                state_store=state_store,
            ),
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def on_message(self, event: AstrMessageEvent):
        """Handle messages that belong to the deterministic game.

        Args:
            event: AstrBot message event.

        Yields:
            AstrBot text results for each rendered domain message.
        """

        if not self._enabled:
            return
        for message in self._adapter.handle(event):
            yield event.plain_result(message)
