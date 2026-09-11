"""Unit tests for the AI companion presence service and its transport."""

import json
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from apeiria_core import (
    CompanionDecision,
    CompanionService,
    LlmTransportError,
    SQLiteStateStore,
)
from apeiria_core.companion import parse_decision

SYSTEM_PROMPT = "你是艾佩理雅。"


def verdict(speak: bool = True, text: str = "好的呀。", action: str | None = None) -> str:
    return json.dumps({"speak": speak, "text": text, "action": action}, ensure_ascii=False)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, str]]]] = []
        self.answer = verdict()
        self.error: Exception | None = None

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        self.calls.append((model, [dict(message) for message in messages]))
        if self.error is not None:
            raise self.error
        return self.answer


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_service(
    transport: FakeTransport,
    store: SQLiteStateStore,
    clock: FakeClock,
    **options: Any,
) -> CompanionService:
    return CompanionService(
        transport,
        store,
        system_prompt=SYSTEM_PROMPT,
        model="deepseek-v4-flash",
        clock=clock,
        **options,
    )


def test_parse_decision_verdicts() -> None:
    assert parse_decision(verdict()) == CompanionDecision(True, "好的呀。", None)
    assert parse_decision(verdict(speak=False)) == CompanionDecision(False)
    assert parse_decision(verdict(text="")) == CompanionDecision(False)
    assert parse_decision(verdict(action="start_game", text="")) == CompanionDecision(
        True, None, "start_game"
    )
    assert parse_decision(verdict(action="hack", text="随口说说")) == CompanionDecision(
        True, "随口说说", None
    )
    assert parse_decision("```json\n" + verdict() + "\n```") == CompanionDecision(
        True, "好的呀。", None
    )
    assert parse_decision("前置废话 " + verdict() + " 后置废话") == CompanionDecision(
        True, "好的呀。", None
    )
    assert parse_decision("完全不是 JSON") == CompanionDecision(False)
    assert parse_decision("{broken json") == CompanionDecision(False)
    assert parse_decision('{"speak": true, "text": 42, "action": null}') == (
        CompanionDecision(False)
    )


def test_wants_reply_gating(tmp_path) -> None:
    transport = FakeTransport()
    service = make_service(
        transport,
        SQLiteStateStore(tmp_path / "state.db"),
        FakeClock(),
        owner_ids={"951505136"},
    )

    assert service.wants_reply("你好", mentioned=True, sender_id="10001")
    assert service.wants_reply("艾佩理雅你好", mentioned=False, sender_id="10001")
    assert service.wants_reply("今晚看什么番好", mentioned=False, sender_id="10001")
    assert service.wants_reply("今天天气不错", mentioned=False, sender_id="951505136")
    assert not service.wants_reply("今天天气不错", mentioned=False, sender_id="10001")
    assert not service.wants_reply("", mentioned=False, sender_id="10001")


def test_ungated_message_never_calls_transport(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(transport, store, FakeClock())

    decision = service.decide("s", "10001", "阿明", "随便聊聊", mentioned=False)

    assert decision.speak is False
    assert transport.calls == []


def test_decide_builds_prompt_and_archives_answer(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport()
    service = make_service(transport, store, clock)
    service.observe("s", "10001", "阿明", "早上好")

    decision = service.decide("s", "10001", "阿明", "艾佩理雅，晚上吃什么", mentioned=False)

    assert decision == CompanionDecision(True, "好的呀。", None)
    model, messages = transport.calls[0]
    assert model == "deepseek-v4-flash"
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[-1] == {"role": "user", "content": "阿明 说：艾佩理雅，晚上吃什么"}
    assert {"role": "user", "content": "阿明 说：早上好"} in messages[1:-1]

    service.decide("s", "10001", "阿明", "艾佩理雅，还有呢", mentioned=False)
    _, second = transport.calls[1]
    assert {"role": "assistant", "content": "好的呀。"} in second[1:-1]


def test_owner_message_marked_in_prompt(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(
        transport,
        store,
        FakeClock(),
        owner_ids={"951505136"},
    )
    service.observe("s", "951505136", "Owner", "在忙什么")

    service.decide("s", "10001", "阿明", "艾佩理雅，聊聊", mentioned=False)

    _, messages = transport.calls[0]
    assert {"role": "user", "content": "Owner（Owner） 说：在忙什么"} in messages[1:-1]


def test_model_silence_keeps_history_clean(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport()
    transport.answer = verdict(speak=False)
    service = make_service(transport, store, clock)

    decision = service.decide("s", "10001", "阿明", "艾佩理雅？", mentioned=False)

    assert decision.speak is False
    transport.answer = verdict()
    assert service.decide("s", "10001", "阿明", "艾佩理雅，还在吗", mentioned=False).speak
    _, messages = transport.calls[1]
    assert not any(message["role"] == "assistant" for message in messages[1:-1])


def test_transport_failure_returns_silence(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport()
    transport.error = LlmTransportError("boom")
    service = make_service(transport, store, clock)

    decision = service.decide("s", "10001", "阿明", "艾佩理雅？", mentioned=False)

    assert decision.speak is False
    transport.error = None
    assert service.decide("s", "10001", "阿明", "艾佩理雅，还在吗", mentioned=False).speak
    _, messages = transport.calls[1]
    assert not any(message["role"] == "assistant" for message in messages[1:-1])


def test_rate_limit_blocks_autonomous_spree(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport()
    service = make_service(
        transport,
        store,
        clock,
        autonomous_rate_limit=2,
        rate_window_seconds=600.0,
    )

    assert service.decide("s", "10001", "阿明", "好无聊啊", mentioned=False).speak
    assert service.decide("s", "10001", "阿明", "看什么番好", mentioned=False).speak

    transport.calls.clear()
    decision = service.decide("s", "10001", "阿明", "来点新番推荐", mentioned=False)
    assert decision.speak is False
    assert transport.calls == []

    clock.advance(601.0)
    assert service.decide("s", "10001", "阿明", "来点新番推荐", mentioned=False).speak


def test_mentions_bypass_rate_limit(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(
        transport,
        store,
        FakeClock(),
        autonomous_rate_limit=1,
        rate_window_seconds=600.0,
    )

    assert service.decide("s", "10001", "阿明", "好无聊啊", mentioned=False).speak

    for index in range(3):
        assert service.decide(
            "s", "10001", "阿明", f"艾佩理雅，第{index}次", mentioned=True
        ).speak

    assert len(transport.calls) == 4


def test_owner_messages_bypass_rate_limit(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(
        transport,
        store,
        FakeClock(),
        owner_ids={"951505136"},
        autonomous_rate_limit=1,
        rate_window_seconds=600.0,
    )

    assert service.decide("s", "10001", "阿明", "好无聊啊", mentioned=False).speak

    transport.calls.clear()
    assert service.decide("s", "951505136", "Owner", "在忙什么", mentioned=False).speak
    assert len(transport.calls) == 1


def test_prunes_expired_history_from_prompt(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport()
    service = make_service(transport, store, clock)
    service.observe("s", "10001", "阿明", "一月的话题")

    clock.advance(31 * 24 * 3600.0)
    service.observe("s", "10001", "阿明", "今天的话题")
    service.decide("s", "10001", "阿明", "艾佩理雅，聊什么", mentioned=False)

    _, messages = transport.calls[0]
    user_contents = [m["content"] for m in messages if m["role"] == "user"]
    assert "阿明 说：今天的话题" in user_contents
    assert "阿明 说：一月的话题" not in user_contents


def test_archive_limit_trims_history(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(transport, store, FakeClock(), archive_limit=2)
    for index in range(4):
        service.observe("s", "10001", "阿明", f"消息{index}")

    service.decide("s", "10001", "阿明", "艾佩理雅？", mentioned=False)

    _, messages = transport.calls[0]
    user_contents = [m["content"] for m in messages[1:-1] if m["role"] == "user"]
    assert user_contents == ["阿明 说：消息2", "阿明 说：消息3"]


def test_clips_long_messages(tmp_path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    transport = FakeTransport()
    service = make_service(transport, store, FakeClock(), max_message_chars=10)
    service.observe("s", "10001", "阿明", "x" * 200)

    service.decide("s", "10001", "阿明", "艾佩理雅，复述一下", mentioned=False)

    _, messages = transport.calls[0]
    assert messages[1] == {"role": "user", "content": "阿明 说：" + "x" * 10}


class StubHandler(BaseHTTPRequestHandler):
    last_authorization: str | None = None

    def do_POST(self) -> None:
        StubHandler.last_authorization = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path != "/chat/completions":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer test-key":
            self.send_error(401)
            return
        if payload.get("model") != "deepseek-v4-flash":
            self.send_error(400)
            return
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": "桩回复"}}]}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture()
def stub_api_port() -> Iterator[int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_openai_transport_round_trip(stub_api_port: int) -> None:
    from apeiria_core import OpenAICompatibleTransport

    transport = OpenAICompatibleTransport(
        base_url=f"http://127.0.0.1:{stub_api_port}",
        api_key="test-key",
        proxy="",
    )

    answer = transport.chat(
        "deepseek-v4-flash",
        [{"role": "user", "content": "你好"}],
    )

    assert answer == "桩回复"
    assert StubHandler.last_authorization == "Bearer test-key"


def test_openai_transport_maps_errors(stub_api_port: int) -> None:
    from apeiria_core import OpenAICompatibleTransport

    transport = OpenAICompatibleTransport(
        base_url=f"http://127.0.0.1:{stub_api_port}",
        api_key="wrong-key",
        proxy="",
    )

    with pytest.raises(LlmTransportError, match="401"):
        transport.chat("deepseek-v4-flash", [{"role": "user", "content": "你好"}])

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    dead = OpenAICompatibleTransport(
        base_url=f"http://127.0.0.1:{port}",
        api_key="test-key",
        proxy="",
        timeout=2.0,
    )

    with pytest.raises(LlmTransportError):
        dead.chat("deepseek-v4-flash", [{"role": "user", "content": "你好"}])
