"""Bangumi HTTP API client with persistent cache and quiet degradation.

Facts verified against the official spec (bangumi/api, synced from
bangumi/server `openapi/v0.yaml`) and a live probe on 2026-09-11:

- ``GET /v0/subjects/{subject_id}`` works unauthenticated and returns the
  ``Subject`` JSON object; missing entries answer HTTP 404.
- Non-browser clients MUST send a User-Agent containing the developer ID and
  application name; open-source projects add the project homepage.
- From networks where ``api.bangumi.tv`` is unreachable, the alternative
  domain ``api.bgm.tv`` serves the same API and is therefore the default here.

Quiet degradation contract: this client NEVER raises to callers of
:meth:`BangumiClient.get_subject`. Unreachable API, unexpected payloads, and
expired entries degrade to the freshest cached copy (any age) or ``None``.
"""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from apeiria_core import StateStore

DEFAULT_BASE_URL = "https://api.bgm.tv"
DEFAULT_USER_AGENT = "aryuu-git/Apeiria/0.1 (https://github.com/aryuu-git/Apeiria)"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_TTL_SECONDS = 7 * 24 * 3600.0
DEFAULT_MIN_INTERVAL_SECONDS = 1.0


class BangumiTransportError(RuntimeError):
    """Base error raised by transports; never escapes :class:`BangumiClient`."""


class BangumiHTTPError(BangumiTransportError):
    """The API answered with an HTTP error status."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url


class BangumiUnavailableError(BangumiTransportError):
    """The API could not be reached at all (network, TLS, timeout, proxy)."""


class BangumiTransport(Protocol):
    """Minimal synchronous transport required by :class:`BangumiClient`."""

    def get_json(self, url: str) -> dict[str, Any]:
        """Return the parsed JSON object or raise :class:`BangumiTransportError`."""


class UrllibBangumiTransport:
    """Stdlib transport that reuses Windows/env proxy configuration by default.

    ``proxy=None`` keeps urllib's default behavior (system proxy registry and
    proxy environment variables). Pass ``proxy=""`` to force direct
    connections, or an explicit URL such as ``http://127.0.0.1:7890``.
    """

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        proxy: str | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._opener = (
            urllib.request.build_opener()
            if proxy is None
            else urllib.request.build_opener(urllib.request.ProxyHandler({}))
            if proxy == ""
            else urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            )
        )

    def get_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent, "Accept": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise BangumiHTTPError(error.code, url) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise BangumiUnavailableError(f"{url}: {error}") from error
        if not isinstance(payload, dict):
            raise BangumiTransportError(f"{url}: expected a JSON object")
        return payload


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    """Typed cache payload; guards strict typing at cache boundaries."""

    fetched_at: float
    subject: dict[str, Any]


class BangumiClient:
    """Cached Bangumi subject reader that never fails its caller.

    Cache entries live in the shared :class:`StateStore` under the
    ``anime-party`` namespace with keys ``bangumi-subject-{id}``. Requests are
    throttled to one per ``min_interval_seconds``; cache hits never touch the
    network and never sleep.
    """

    CACHE_NAMESPACE = "anime-party"

    def __init__(
        self,
        transport: BangumiTransport,
        store: StateStore,
        *,
        base_url: str = DEFAULT_BASE_URL,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._store = store
        self._base_url = base_url.rstrip("/")
        self._ttl_seconds = ttl_seconds
        self._min_interval_seconds = min_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    def get_subject(self, subject_id: int) -> dict[str, Any] | None:
        """Return the subject JSON, its stale cached copy, or ``None``.

        ``None`` means the subject is definitively absent (HTTP 404) or
        unreachable with no cached copy; callers treat it as "no data" and
        stay silent.
        """
        if subject_id <= 0:
            return None
        key = f"bangumi-subject-{subject_id}"
        cached = self._load_cache(key)
        now = self._clock()
        if cached is not None and now - cached.fetched_at < self._ttl_seconds:
            return cached.subject
        try:
            subject = self._fetch(subject_id)
        except BangumiTransportError:
            if cached is None:
                return None
            return cached.subject
        if subject is None:
            return None
        self._store.set(
            self.CACHE_NAMESPACE,
            key,
            json.dumps({"fetched_at": self._clock(), "subject": subject}),
        )
        return subject

    def _fetch(self, subject_id: int) -> dict[str, Any] | None:
        """Fetch over the network; ``None`` means HTTP 404."""
        self._throttle()
        url = f"{self._base_url}/v0/subjects/{subject_id}"
        try:
            return self._transport.get_json(url)
        except BangumiHTTPError as error:
            if error.status == 404:
                return None
            raise

    def _throttle(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self._min_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
        self._last_request_at = self._clock()


    def _load_cache(self, key: str) -> _CacheEntry | None:
        raw = self._store.get(self.CACHE_NAMESPACE, key)
        if raw is None:
            return None
        try:
            entry = json.loads(raw)
            fetched_at = float(entry["fetched_at"])
            subject = entry["subject"]
            if not isinstance(subject, dict):
                raise TypeError("subject must be an object")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
        return _CacheEntry(fetched_at=fetched_at, subject=subject)
