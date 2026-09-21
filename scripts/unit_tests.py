"""Unit tests for the parts of the runner that need neither a browser nor an API key.

    .venv/bin/python scripts/unit_tests.py

Standard-library unittest. Python puts this script's directory on sys.path, so the modules under
scripts/ import directly (`from jev_client import JevClient`). Exits non-zero on any failure.
The Jev client is exercised against a local HTTP/1.1 server that counts connections and requests,
so the keep-alive, reconnect, backoff and proxy behaviour is observed, not assumed.
"""
from __future__ import annotations

import http.client
import http.server
import json
import os
import threading
import unittest
from unittest import mock

from jev_client import DEFAULT_BASE_URL, JevClient, JevError

ANSWER = {
    "model": "fake",
    "answers": {"operation": {"type": "choice", "choice": "DONE", "confidence": 0.9,
                              "probabilities": {"DONE": 0.9, "WAIT": 0.1}}},
    "usage": {"input_tokens": 1, "output_tokens": 1},
}


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive, like the real API
    timeout = 2                    # an abandoned keep-alive socket frees its thread by itself

    def log_message(self, *args) -> None:  # keep the test output clean
        pass

    def do_POST(self) -> None:
        srv: FakeSystemOne = self.server  # type: ignore[assignment]
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        with srv.lock:
            srv.requests += 1
            srv.seen.append({"method": "POST", "path": self.path, "headers": dict(self.headers),
                             "body": json.loads(body)})
            action = srv.script.pop(0) if srv.script else 200
        if action == "hang":
            srv.release.wait(5)
            action = "drop"
        if action == "drop":
            # Close the socket without answering: the client must see RemoteDisconnected and retry.
            self.close_connection = True
            return
        payload = json.dumps(ANSWER if action == 200 else {"error": f"scripted {action}"}).encode()
        self.send_response(action)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_CONNECT(self) -> None:
        # The client thinks we are its https proxy. Record the tunnel request and refuse it: a fake
        # server could not complete the TLS handshake that would follow a 200 anyway.
        srv: FakeSystemOne = self.server  # type: ignore[assignment]
        with srv.lock:
            srv.requests += 1
            srv.seen.append({"method": "CONNECT", "path": self.path, "headers": dict(self.headers)})
        self.send_response(502)
        self.send_header("Content-Length", "0")
        self.end_headers()
        self.close_connection = True


class FakeSystemOne(http.server.ThreadingHTTPServer):
    """Local stand-in for POST /v1/systemone.

    `script` lists what to do with the next requests, in order: an int is the HTTP status to answer
    with, "drop" closes the socket without a response, "hang" blocks until `release` is set (then
    drops). Once the script is exhausted every request gets a 200 with a valid System One body.
    """

    daemon_threads = True
    block_on_close = False  # never wait for a handler parked on a keep-alive socket

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.connections = 0
        self.requests = 0
        self.seen: list[dict] = []
        self.script: list = []
        self.lock = threading.Lock()
        self.release = threading.Event()

    def process_request(self, request, client_address) -> None:
        with self.lock:
            self.connections += 1
        super().process_request(request, client_address)

    @property
    def hostport(self) -> str:
        return f"127.0.0.1:{self.server_address[1]}"

    @property
    def url(self) -> str:
        return f"http://{self.hostport}/v1/systemone"


def proxy_env(**settings: str):
    """Pin the proxy-related environment for one test: drop every *_proxy variable, then set `settings`.

    `urllib.request.getproxies()` reads these at call time (and falls back to the macOS system proxy
    when none is set), so the tests fix them instead of inheriting whatever the shell has.
    """
    env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
    env.update(settings)
    return mock.patch.dict(os.environ, env, clear=True)


class JevClientTests(unittest.TestCase):
    def setUp(self) -> None:
        # Nothing may sit between the tests and the fake server. start()/addCleanup rather than
        # enterContext(): that is 3.11+, and the repo runs on the stock macOS 3.9 too.
        patcher = proxy_env(no_proxy="*")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.server = FakeSystemOne()
        # A short poll interval keeps shutdown() in tearDown from costing up to 0.5 s per test.
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.client = JevClient(api_key="x", base_url=self.server.url, timeout=5.0, retries=2)
        self.delays: list[float] = []
        self.client._sleep = self.delays.append

    def tearDown(self) -> None:
        self.client.close()
        self.server.release.set()
        self.server.shutdown()
        self.server.server_close()

    def call(self) -> dict:
        return self.client.system_one({"goal": "g"}, {"operation": {"type": "choice", "criteria": {"DONE": "d"}}})

    def test_consecutive_calls_share_one_connection(self) -> None:
        self.call()
        resp = self.call()
        self.assertEqual(self.server.connections, 1)
        self.assertEqual(self.server.requests, 2)
        self.assertEqual(resp["answers"]["operation"]["choice"], "DONE")
        self.assertIsInstance(resp["latency_ms"], int)
        self.client.close()
        self.call()  # after close() the next call opens a fresh connection
        self.assertEqual(self.server.connections, 2)
        self.assertEqual(self.server.requests, 3)

    def test_request_shape(self) -> None:
        self.call()
        seen = self.server.seen[0]
        self.assertEqual(seen["path"], "/v1/systemone")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer x")
        self.assertEqual(seen["headers"]["Content-Type"], "application/json")
        self.assertEqual(seen["headers"]["User-Agent"], "jev-browser-test/0.1")
        self.assertEqual(seen["body"]["state"], {"goal": "g"})
        self.assertEqual(seen["body"]["model"], self.client.model)
        self.assertIn("operation", seen["body"]["questions"])

    def test_path_keeps_query(self) -> None:
        client = JevClient(api_key="x", base_url=self.server.url + "?trace=1")
        try:
            client.system_one({}, {})
        finally:
            client.close()
        self.assertEqual(self.server.seen[0]["path"], "/v1/systemone?trace=1")

    def test_dropped_socket_reconnects_once_and_succeeds(self) -> None:
        self.call()
        self.server.script = ["drop"]
        resp = self.call()
        self.assertEqual(resp["answers"]["operation"]["choice"], "DONE")
        self.assertEqual(self.client.reconnects, 1)
        self.assertEqual(self.server.connections, 2)
        self.assertEqual(self.server.requests, 3)  # the dropped request plus its retry
        self.assertEqual(self.delays, [])          # the reconnect is immediate, no backoff
        self.assertEqual(self.client.usage_summary()["reconnects"], 1)

    def test_repeated_drops_fall_through_to_backoff_then_raise(self) -> None:
        self.server.script = ["drop"] * 4  # 1 reconnect + retries (2) + the final failure
        with self.assertRaises(JevError) as ctx:
            self.call()
        self.assertIn("unreachable", str(ctx.exception))
        self.assertEqual(self.client.reconnects, 1)
        self.assertEqual(self.delays, [1.0, 2.0])
        self.assertEqual(self.server.requests, 4)
        self.assertEqual(self.client.requests, 0)

    def test_429_then_200_retries_without_sleeping_for_real(self) -> None:
        self.server.script = [429, 200]
        resp = self.call()
        self.assertEqual(resp["answers"]["operation"]["choice"], "DONE")
        self.assertEqual(self.delays, [1.0])
        self.assertEqual(self.server.requests, 2)
        self.assertEqual(self.server.connections, 1)  # a 429 does not cost the connection
        self.assertEqual(self.client.reconnects, 0)

    def test_5xx_exhausts_retries_then_raises(self) -> None:
        self.server.script = [503, 502, 500]
        with self.assertRaises(JevError) as ctx:
            self.call()
        self.assertIn("HTTP 500", str(ctx.exception))
        self.assertIn("scripted 500", str(ctx.exception))
        self.assertEqual(self.delays, [1.0, 2.0])

    def test_400_raises_immediately(self) -> None:
        self.server.script = [400]
        with self.assertRaises(JevError) as ctx:
            self.call()
        self.assertIn("400", str(ctx.exception))
        self.assertIn("scripted 400", str(ctx.exception))
        self.assertEqual(self.delays, [])
        self.assertEqual(self.server.requests, 1)

    def test_timeout_closes_connection_and_raises(self) -> None:
        client = JevClient(api_key="x", base_url=self.server.url, timeout=0.2, retries=0)
        client._sleep = self.delays.append
        self.server.script = ["hang"]
        try:
            with self.assertRaises(JevError) as ctx:
                client.system_one({}, {})
        finally:
            self.server.release.set()
            client.close()
        self.assertIn("unreachable", str(ctx.exception))
        self.assertEqual(client.reconnects, 0)  # a timeout is not a dropped socket

    def test_usage_counters_accumulate(self) -> None:
        for _ in range(3):
            self.call()
        self.assertEqual(self.client.requests, 3)
        self.assertEqual(self.client.input_tokens, 3)
        self.assertEqual(self.client.output_tokens, 3)
        summary = self.client.usage_summary()
        self.assertEqual(summary["jev_requests"], 3)
        self.assertEqual(summary["input_tokens"], 3)
        self.assertEqual(summary["model"], "fake")
        self.assertEqual(summary["reconnects"], 0)

    def test_default_url_is_https_with_path(self) -> None:
        client = JevClient(api_key="x", base_url=DEFAULT_BASE_URL)
        self.assertIs(client._conn_class, http.client.HTTPSConnection)
        self.assertEqual((client._host, client._port, client._path), ("api.typesafe.ai", None, "/v1/systemone"))
        self.assertIsNone(client._proxy)  # no proxy configured: connect straight to the API
        self.assertIsNone(client._conn)   # nothing is opened until the first call

    # The proxy is resolved when the client is built (like urllib does per request), so each case
    # constructs its client inside the patched environment.

    def test_http_proxy_relays_by_absolute_url_with_credentials(self) -> None:
        # The fake server plays the proxy. The API host does not resolve, so only a relayed request can succeed.
        with proxy_env(http_proxy=f"http://user:s3cret@{self.server.hostport}"):
            client = JevClient(api_key="x", base_url="http://origin.invalid:8080/v1/systemone?trace=1")
        try:
            resp = client.system_one({}, {})
        finally:
            client.close()
        self.assertEqual(resp["model"], "fake")
        seen = self.server.seen[0]
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["path"], "http://origin.invalid:8080/v1/systemone?trace=1")
        self.assertEqual(seen["headers"]["Host"], "origin.invalid:8080")
        self.assertEqual(seen["headers"]["Proxy-Authorization"], "Basic dXNlcjpzM2NyZXQ=")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer x")

    def test_https_proxy_tunnels_with_connect(self) -> None:
        # Without TLS only the tunnel request can be observed; the fake proxy refuses it and the client
        # must report that rather than going to the API host directly. Bare "host:port" spelling here.
        with proxy_env(https_proxy=f"user:s3cret@{self.server.hostport}"):
            client = JevClient(api_key="x", base_url="https://origin.invalid/v1/systemone", retries=0)
        client._sleep = self.delays.append
        try:
            with self.assertRaises(JevError) as ctx:
                client.system_one({}, {})
        finally:
            client.close()
        self.assertIn("Tunnel connection failed: 502", str(ctx.exception))
        seen = self.server.seen[0]
        self.assertEqual(seen["method"], "CONNECT")
        self.assertEqual(seen["path"], "origin.invalid:443")
        self.assertEqual(seen["headers"]["Proxy-Authorization"], "Basic dXNlcjpzM2NyZXQ=")
        self.assertEqual(client.reconnects, 0)  # a refused tunnel is not a dropped keep-alive socket

    def test_no_proxy_bypasses_the_proxy(self) -> None:
        with proxy_env(http_proxy="http://127.0.0.1:9", no_proxy="127.0.0.1"):  # port 9: nothing listens
            client = JevClient(api_key="x", base_url=self.server.url)
        try:
            client.system_one({}, {})
        finally:
            client.close()
        self.assertIsNone(client._proxy)
        self.assertEqual(self.server.seen[0]["path"], "/v1/systemone")

    def test_rejects_non_http_base_url(self) -> None:
        with self.assertRaises(JevError):
            JevClient(api_key="x", base_url="ftp://example.invalid/v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
