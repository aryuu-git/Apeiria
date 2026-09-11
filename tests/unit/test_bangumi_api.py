"""Unit tests for the Bangumi API client, cache, and quiet degradation."""

import json
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from anime_party.bangumi_api import (
    BangumiClient,
    BangumiHTTPError,
    BangumiTransportError,
    BangumiUnavailableError,
    UrllibBangumiTransport,
)
from apeiria_core import SQLiteStateStore

SUBJECT_8 = {
    "id": 8,
    "name": "Code Geass: Lelouch of the Rebellion R2",
    "name_cn": "Code Geass 反叛的鲁路修R2",
    "date": "2008-04-06",
    "nsfw": False,
}

SUBJECT_9 = {
    "id": 9,
    "name": "Another Subject",
    "name_cn": "另一个条目",
    "date": "2009-04-06",
    "nsfw": False,
}


class FakeTransport:
    """Scriptable transport: missing URLs answer 404, exceptions raise."""

    def __init__(self, responses: dict[str, dict[str, Any] | Exception]) -> None:
        self._responses = responses
        self.requested: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        self.requested.append(url)
        response = self._responses.get(url)
        if response is None:
            raise BangumiHTTPError(404, url)
        if isinstance(response, Exception):
            raise response
        return response

    def set_response(self, url: str, response: dict[str, Any] | Exception) -> None:
        self._responses[url] = response


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds


def make_client(
    transport: FakeTransport,
    store: SQLiteStateStore,
    clock: FakeClock,
    **options: Any,
) -> BangumiClient:
    return BangumiClient(
        transport,
        store,
        clock=clock,
        sleeper=clock.sleep,
        **options,
    )


def test_fetches_subject_then_serves_cache_without_network(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({"https://api.bgm.tv/v0/subjects/8": SUBJECT_8})
    client = make_client(transport, store, clock)

    assert client.get_subject(8) == SUBJECT_8
    clock.advance(3600.0)
    assert client.get_subject(8) == SUBJECT_8

    assert transport.requested == ["https://api.bgm.tv/v0/subjects/8"]
    assert clock.waits == []


def test_expired_cache_refetches(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport(
        {
            "https://api.bgm.tv/v0/subjects/8": SUBJECT_8,
        }
    )
    client = make_client(transport, store, clock)

    assert client.get_subject(8) == SUBJECT_8
    clock.advance(7 * 24 * 3600.0 + 1.0)
    assert client.get_subject(8) == SUBJECT_8

    assert transport.requested == [
        "https://api.bgm.tv/v0/subjects/8",
        "https://api.bgm.tv/v0/subjects/8",
    ]


def test_unreachable_api_serves_stale_cache(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({"https://api.bgm.tv/v0/subjects/8": SUBJECT_8})
    client = make_client(transport, store, clock)
    assert client.get_subject(8) == SUBJECT_8

    transport.set_response(
        "https://api.bgm.tv/v0/subjects/8",
        BangumiUnavailableError("connection refused"),
    )
    clock.advance(30 * 24 * 3600.0)

    assert client.get_subject(8) == SUBJECT_8


def test_http_error_serves_stale_cache(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({"https://api.bgm.tv/v0/subjects/8": SUBJECT_8})
    client = make_client(transport, store, clock)
    assert client.get_subject(8) == SUBJECT_8

    transport.set_response(
        "https://api.bgm.tv/v0/subjects/8",
        BangumiHTTPError(500, "https://api.bgm.tv/v0/subjects/8"),
    )
    clock.advance(3600.0)

    assert client.get_subject(8) == SUBJECT_8


def test_unreachable_api_without_cache_returns_none(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({})
    transport.set_response(
        "https://api.bgm.tv/v0/subjects/8",
        BangumiUnavailableError("dns failure"),
    )
    client = make_client(transport, store, clock)

    assert client.get_subject(8) is None
    assert store.get(BangumiClient.CACHE_NAMESPACE, "bangumi-subject-8") is None


def test_http_404_returns_none_without_caching(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({})
    client = make_client(transport, store, clock)

    assert client.get_subject(8) is None
    assert client.get_subject(8) is None

    assert transport.requested == [
        "https://api.bgm.tv/v0/subjects/8",
        "https://api.bgm.tv/v0/subjects/8",
    ]
    assert store.get(BangumiClient.CACHE_NAMESPACE, "bangumi-subject-8") is None


def test_throttles_network_requests(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport(
        {
            "https://api.bgm.tv/v0/subjects/8": SUBJECT_8,
            "https://api.bgm.tv/v0/subjects/9": SUBJECT_9,
        }
    )
    client = make_client(transport, store, clock)

    assert client.get_subject(8) == SUBJECT_8
    assert client.get_subject(9) == SUBJECT_9

    assert transport.requested == [
        "https://api.bgm.tv/v0/subjects/8",
        "https://api.bgm.tv/v0/subjects/9",
    ]
    assert clock.waits == [1.0]


def test_corrupted_cache_entry_is_refetched(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({"https://api.bgm.tv/v0/subjects/8": SUBJECT_8})
    client = make_client(transport, store, clock)
    store.set(BangumiClient.CACHE_NAMESPACE, "bangumi-subject-8", "{not json")

    assert client.get_subject(8) == SUBJECT_8
    cached = json.loads(store.get(BangumiClient.CACHE_NAMESPACE, "bangumi-subject-8") or "")
    assert cached["subject"] == SUBJECT_8

    store.set(BangumiClient.CACHE_NAMESPACE, "bangumi-subject-8", '["a list"]')
    assert client.get_subject(8) == SUBJECT_8


def test_invalid_subject_ids_never_touch_network(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.db")
    clock = FakeClock()
    transport = FakeTransport({})
    client = make_client(transport, store, clock)

    assert client.get_subject(0) is None
    assert client.get_subject(-3) is None
    assert transport.requested == []


class StubHandler(BaseHTTPRequestHandler):
    last_user_agent: str | None = None

    def do_GET(self) -> None:
        StubHandler.last_user_agent = self.headers.get("User-Agent")
        agent = self.headers.get("User-Agent", "")
        if not agent.startswith("aryuu-git/Apeiria"):
            self.send_error(403)
            return
        if self.path == "/v0/subjects/8":
            self._send_json(200, SUBJECT_8)
        elif self.path == "/v0/subjects/list":
            self._send_json(200, [SUBJECT_8])
        elif self.path == "/v0/subjects/500":
            self.send_error(500)
        else:
            self.send_error(404)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
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


def test_urllib_transport_parses_subject_and_sends_user_agent(
    stub_api_port: int,
) -> None:
    transport = UrllibBangumiTransport(proxy="")

    assert transport.get_json(f"http://127.0.0.1:{stub_api_port}/v0/subjects/8") == SUBJECT_8
    assert StubHandler.last_user_agent == (
        "aryuu-git/Apeiria/0.1 (https://github.com/aryuu-git/Apeiria)"
    )


def test_urllib_transport_maps_404_and_500(stub_api_port: int) -> None:
    transport = UrllibBangumiTransport(proxy="")

    with pytest.raises(BangumiHTTPError, match="404") as missing:
        transport.get_json(f"http://127.0.0.1:{stub_api_port}/v0/subjects/999")
    assert missing.value.status == 404

    with pytest.raises(BangumiHTTPError, match="500") as broken:
        transport.get_json(f"http://127.0.0.1:{stub_api_port}/v0/subjects/500")
    assert broken.value.status == 500


def test_urllib_transport_rejects_non_object_json(stub_api_port: int) -> None:
    transport = UrllibBangumiTransport(proxy="")

    with pytest.raises(BangumiTransportError, match="JSON object"):
        transport.get_json(f"http://127.0.0.1:{stub_api_port}/v0/subjects/list")


def test_urllib_transport_reports_unreachable() -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    transport = UrllibBangumiTransport(proxy="")

    with pytest.raises(BangumiUnavailableError):
        transport.get_json(f"http://127.0.0.1:{port}/v0/subjects/8")


def test_client_wires_urllib_transport_end_to_end(
    stub_api_port: int,
    tmp_path: Path,
) -> None:
    client = BangumiClient(
        UrllibBangumiTransport(proxy=""),
        SQLiteStateStore(tmp_path / "state.db"),
        base_url=f"http://127.0.0.1:{stub_api_port}",
        min_interval_seconds=0.0,
    )

    assert client.get_subject(8) == SUBJECT_8
    assert client.get_subject(8) == SUBJECT_8
    assert client.get_subject(9) is None
