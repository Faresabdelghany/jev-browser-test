"""Minimal client for TypeSafe's System One API (the Jev model).

Standard library only (`http.client`), so the runner has no dependency beyond Playwright.

    POST https://api.typesafe.ai/v1/systemone
    Authorization: Bearer $TYPESAFE_API_KEY
    {"state": ..., "model": "jev-latest", "questions": {...}}

One connection is opened lazily on the first call and kept alive for the rest of the run, so only
the first step pays for the TCP + TLS handshake. Every response body is read to the end so the
socket can carry the next request. If the kept-alive socket has died under us (server idle
timeout, load-balancer reset) the request is retried once, immediately, on a fresh connection:
Jev calls are read-only, so a retry cannot double-act. The number of such reconnects is reported
in `usage_summary()` as evidence that the guard fired.

Proxies are honoured the way `urllib.request` honours them: `https_proxy` / `http_proxy` /
`no_proxy` from the environment, else the macOS system proxy. An https API is reached through a
CONNECT tunnel on the proxy, an http API by sending it the absolute URL; credentials in the proxy
URL become Proxy-Authorization. The hop to the proxy itself is plain TCP.

Environment variables:
    TYPESAFE_API_KEY   required
    TYPESAFE_MODEL     optional, default "jev-latest"
    TYPESAFE_BASE_URL  optional, default https://api.typesafe.ai/v1/systemone
    https_proxy / http_proxy / no_proxy   optional, the same spellings curl and urllib accept
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import time
import urllib.request
from urllib.parse import SplitResult, unquote, urlsplit

DEFAULT_BASE_URL = "https://api.typesafe.ai/v1/systemone"

# The kept-alive socket died under us. `http.client.RemoteDisconnected` is both a ConnectionResetError
# and an HTTPException; BrokenPipeError / ConnectionResetError / ConnectionAbortedError are all
# ConnectionError. Timeouts are deliberately NOT here: they are an OSError but not a ConnectionError.
CONNECTION_LOST = (ConnectionError, http.client.HTTPException)


class JevError(RuntimeError):
    """Raised when the API cannot be reached or returns an error."""


def choice(instructions: str | dict | list, criteria: dict) -> dict:
    """Build a Choice question: pick one label from `criteria` (label -> description, a string or an object).

    `instructions` may be structured, e.g. {"goal": ..., "rules": ...}: TypeSafe reads objects and arrays
    as well as strings, and an object keeps the question and the guidance it refers to apart.
    """
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str | dict | list, criteria: list) -> dict:
    """Build a Score question: position on an ordered rubric (index 0..n-1). Structured `instructions` allowed."""
    return {"type": "score", "instructions": instructions, "criteria": criteria}


def noul(instructions: str | dict | list) -> dict:
    """Build a Noul question: probability (0-1) that the statement is true of the state.

    `instructions` may be an object such as {"statement": ..., "rules": ...}.
    """
    return {"type": "noul", "instructions": instructions}


def proxy_for(scheme: str, hostport: str) -> SplitResult | None:
    """The proxy `urllib.request` would use for `scheme://hostport`, or None to connect directly.

    `<scheme>_proxy` and `no_proxy` come from the environment (the macOS system proxy when none is
    set), exactly as urllib reads them. A bare "host:port" is accepted as well as a full URL.
    """
    proxies = urllib.request.getproxies()
    if scheme not in proxies or urllib.request.proxy_bypass(hostport):
        return None
    raw = proxies[scheme]
    return urlsplit(raw if "://" in raw else "http://" + raw)


def proxy_auth_headers(proxy: SplitResult) -> dict[str, str]:
    """Proxy-Authorization for credentials embedded in the proxy URL (http://user:pass@host:port)."""
    if not proxy.username:
        return {}
    creds = f"{unquote(proxy.username)}:{unquote(proxy.password or '')}".encode()
    return {"Proxy-Authorization": "Basic " + base64.b64encode(creds).decode()}


class JevClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 20.0,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY", "")
        if not self.api_key:
            raise JevError(
                "TYPESAFE_API_KEY is not set. Create a key at https://console.typesafe.ai/keys "
                "and export it (or put it in a .env file in the directory the runner is started from)."
            )
        self.model = model or os.environ.get("TYPESAFE_MODEL", "jev-latest")
        self.base_url = base_url or os.environ.get("TYPESAFE_BASE_URL", DEFAULT_BASE_URL)
        url = urlsplit(self.base_url)
        if url.scheme not in ("https", "http") or not url.hostname:
            raise JevError(f"TYPESAFE_BASE_URL must be an http(s) URL, got {self.base_url!r}")
        self._conn_class = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        self._host, self._port = url.hostname, url.port
        self._path = (url.path or "/") + (f"?{url.query}" if url.query else "")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "jev-browser-test/0.1",
        }
        # Through a proxy, an https API is tunnelled (CONNECT, proxy credentials on the tunnel request);
        # an http API is requested by absolute URL, with the proxy credentials on every request.
        hostport = self._host + (f":{self._port}" if self._port else "")
        self._proxy = proxy_for(url.scheme, hostport)
        self._target = self._path  # the request target; the absolute URL when an http proxy relays it
        self._tunnel_headers: dict[str, str] = {}
        if self._proxy is not None:
            if url.scheme == "https":
                self._tunnel_headers = proxy_auth_headers(self._proxy)
            else:
                self._target = f"http://{hostport}{self._path}"
                self._headers.update(proxy_auth_headers(self._proxy))
        self._conn: http.client.HTTPConnection | None = None
        self._sleep = time.sleep  # injectable so tests do not wait out the backoff
        self.timeout = timeout
        self.retries = retries
        self.requests = 0
        self.reconnects = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.last_model: str | None = None

    def _open(self) -> http.client.HTTPConnection:
        """A fresh connection to the API, or to the proxy that relays to it."""
        if self._proxy is None:
            return self._conn_class(self._host, self._port, timeout=self.timeout)
        conn = self._conn_class(self._proxy.hostname, self._proxy.port or 80, timeout=self.timeout)
        if self._conn_class is http.client.HTTPSConnection:
            conn.set_tunnel(self._host, self._port, headers=self._tunnel_headers)  # TLS runs inside the tunnel
        return conn

    def _post(self, body: bytes) -> tuple[int, bytes]:
        """One request on the kept-alive connection (opened on first use). Returns (status, body)."""
        if self._conn is None:
            self._conn = self._open()
        self._conn.request("POST", self._target, body=body, headers=self._headers)
        resp = self._conn.getresponse()
        return resp.status, resp.read()  # read to the end so the connection is ready for the next call

    def close(self) -> None:
        """Drop the kept-alive connection, if any. The next call opens a fresh one."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def system_one(self, state, questions: dict[str, dict]) -> dict:
        """Evaluate all `questions` against `state` in one call.

        Returns {"answers": {...}, "usage": {...}, "model": str, "latency_ms": int}.
        Answer shapes (per TypeSafe docs):
          choice -> {"type": "choice", "choice": label, "confidence": 0-1, "probabilities": {label: p}}
          score  -> {"type": "score", "score": float, "confidence": 0-1, "probabilities": {...}}
          noul   -> {"type": "noul", "noul": 0-1}
        """
        body = json.dumps({"state": state, "model": self.model, "questions": questions}).encode()
        attempt = 0          # backoff retries: 429 / 5xx / timeouts / unreachable
        reconnected = False  # the one immediate retry a dropped keep-alive socket gets
        while True:
            t0 = time.perf_counter()
            try:
                status, raw = self._post(body)
            except (http.client.HTTPException, OSError) as e:
                self.close()
                if isinstance(e, CONNECTION_LOST) and not reconnected:
                    reconnected = True
                    self.reconnects += 1
                    continue
                if attempt < self.retries:
                    attempt += 1
                    self._sleep(0.5 * 2**attempt)
                    continue
                raise JevError(f"TypeSafe API unreachable: {e}") from None
            if 200 <= status < 300:
                break
            detail = raw.decode(errors="replace")[:500]
            if (status == 429 or status >= 500) and attempt < self.retries:
                attempt += 1
                self._sleep(0.5 * 2**attempt)
                continue
            raise JevError(f"TypeSafe API HTTP {status}: {detail}")
        latency_ms = int((time.perf_counter() - t0) * 1000)
        data = json.loads(raw.decode())

        usage = data.get("usage") or {}
        self.requests += 1
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.last_model = data.get("model")
        return {
            "answers": data.get("answers") or {},
            "usage": usage,
            "model": data.get("model"),
            "latency_ms": latency_ms,
        }

    def usage_summary(self) -> dict:
        return {
            "jev_requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.last_model or self.model,
            "reconnects": self.reconnects,
        }
