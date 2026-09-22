"""Unit tests for the parts of the runner that need neither a browser nor an API key.

    .venv/bin/python scripts/unit_tests.py

Standard-library unittest. Python puts this script's directory on sys.path, so the modules under
scripts/ import directly (`from jev_client import JevClient`). Exits non-zero on any failure.
The Jev client is exercised against a local HTTP/1.1 server that counts connections and requests,
so the keep-alive, reconnect, backoff and proxy behaviour is observed, not assumed. The policy
tests feed hand-built answers to the validation and target resolution, including the malformed
shapes the runner must refuse to act on.
"""
from __future__ import annotations

import http.client
import http.server
import json
import math
import os
import threading
import unittest
from unittest import mock

from jev_client import DEFAULT_BASE_URL, JevClient, JevError
from policy import (
    HISTORY_WINDOW, build_questions, build_state, element_operations, read_checks, read_choice, resolve_target,
    validate_choice,
)
from spec import DEFAULTS, _merge

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


OFFERED = ["CLICK", "WAIT", "DONE"]


def answer(choice="CLICK", probabilities=None, confidence=0.8, **extra) -> dict:
    """A valid Choice answer over OFFERED unless a field is overridden."""
    a = {"type": "choice", "choice": choice, "confidence": confidence,
         "probabilities": {"CLICK": 0.8, "WAIT": 0.15, "DONE": 0.05} if probabilities is None else probabilities}
    a.update(extra)
    return a


def observation(elements: list[dict]) -> dict:
    """The fields of observe() that build_questions and resolve_target read."""
    return {"url": "http://x/", "title": "t", "elements": elements, "truncated": 0, "visible_text": "",
            "can_scroll_down": False, "can_scroll_up": False}


ELEMENTS = [
    {"idx": 0, "role": "textbox", "name": "Username"},
    {"idx": 1, "role": "button", "name": "Login"},
    {"idx": 2, "role": "select", "name": "Size", "options": [{"i": 0, "text": "S"}, {"i": 1, "text": "M", "disabled": True}]},
]
SPEC = _merge(DEFAULTS, {"id": "u", "start_url": "http://x/", "goal": "g", "data": {"username": "tom", "password": "pw"},
                         "secrets": ["password"], "checks": {"ok": "The page says welcome"}, "done_when": ["ok"]})


class ValidateChoiceTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertIsNone(validate_choice(answer(), OFFERED))
        self.assertIsNone(validate_choice(answer(probabilities={"CLICK": 1}, confidence=1), OFFERED))  # ints are numbers
        self.assertIsNone(validate_choice(answer(probabilities={"CLICK": 0.5, "WAIT": 0.5}), OFFERED))  # a tie is on top
        self.assertIsNone(validate_choice(answer(probabilities={"CLICK": 0.81, "WAIT": 0.2}), OFFERED))  # 1.01 is within 0.02

    def test_choice_not_offered(self) -> None:
        self.assertIn("not offered", validate_choice(answer(choice="FLY", probabilities={"FLY": 1.0}), OFFERED))
        self.assertIn("not offered", validate_choice(answer(choice="FLY"), OFFERED))

    def test_probability_key_not_offered(self) -> None:
        self.assertIn("probability key 'FLY'", validate_choice(answer(probabilities={"CLICK": 0.7, "FLY": 0.3}), OFFERED))

    def test_value_above_one(self) -> None:
        self.assertIn("probability of 'CLICK'", validate_choice(answer(probabilities={"CLICK": 1.2, "WAIT": -0.2}), OFFERED))

    def test_nan_value(self) -> None:
        self.assertIn("not a finite number", validate_choice(answer(probabilities={"CLICK": math.nan, "WAIT": 0.1}), OFFERED))
        self.assertIn("not a finite number", validate_choice(answer(probabilities={"CLICK": math.inf}), OFFERED))

    def test_sum_not_one(self) -> None:
        self.assertIn("sum to 0.900", validate_choice(answer(probabilities={"CLICK": 0.8, "WAIT": 0.1}), OFFERED))
        self.assertIn("sum to 1.500", validate_choice(answer(probabilities={"CLICK": 0.9, "WAIT": 0.6}), OFFERED))

    def test_confidence_out_of_range(self) -> None:
        self.assertIn("confidence", validate_choice(answer(confidence=1.2), OFFERED))
        self.assertIn("confidence", validate_choice(answer(confidence=math.nan), OFFERED))
        self.assertIn("confidence", validate_choice(answer(confidence="0.9"), OFFERED))

    def test_choice_not_top(self) -> None:
        self.assertIn("not the top option", validate_choice(answer(choice="WAIT"), OFFERED))
        self.assertIn("has no probability", validate_choice(answer(choice="DONE", probabilities={"CLICK": 0.5, "WAIT": 0.5}), OFFERED))

    def test_huge_integer_is_rejected_not_raised(self) -> None:
        # json.loads turns a 400-digit literal into an int; float(int) would raise OverflowError.
        self.assertIn("not a finite number", validate_choice(answer(probabilities={"CLICK": 10**400}), OFFERED))
        self.assertIn("not a finite number", validate_choice(answer(probabilities={"CLICK": 1.0, "WAIT": -(10**400)}), OFFERED))
        self.assertIn("confidence", validate_choice(answer(confidence=10**400), OFFERED))

    def test_bool_is_not_a_number(self) -> None:
        self.assertIn("not a finite number", validate_choice(answer(probabilities={"CLICK": True}), OFFERED))
        self.assertIn("confidence", validate_choice(answer(confidence=True), OFFERED))

    def test_missing_fields(self) -> None:
        a = answer()
        del a["probabilities"]
        self.assertIn("probabilities missing", validate_choice(a, OFFERED))
        self.assertIn("probabilities missing", validate_choice(answer(probabilities={}), OFFERED))
        a = answer()
        del a["confidence"]
        self.assertIn("confidence is missing", validate_choice(a, OFFERED))
        a = answer()
        del a["choice"]
        self.assertIn("choice is missing", validate_choice(a, OFFERED))
        self.assertIn("choice is missing", validate_choice(answer(choice=1), OFFERED))

    def test_wrong_shape(self) -> None:
        self.assertEqual(validate_choice(None, OFFERED), "no answer")
        self.assertIn("not an object", validate_choice("CLICK", OFFERED))
        self.assertIn("not 'choice'", validate_choice({"type": "noul", "noul": 0.5}, OFFERED))
        self.assertIn("not offered", validate_choice(answer(), []))


class ReadAnswersTests(unittest.TestCase):
    def test_read_choice_strict_and_lenient(self) -> None:
        answers = {"operation": answer(choice="FLY")}
        self.assertIsNone(read_choice(answers, "operation", OFFERED))
        self.assertEqual(read_choice(answers, "operation")["choice"], "FLY")  # lenient: shape only
        self.assertIsNone(read_choice({}, "operation", OFFERED))
        self.assertIsNone(read_choice({}, "operation"))
        got = read_choice({"operation": answer()}, "operation", OFFERED)
        self.assertEqual(got, {"choice": "CLICK", "confidence": 0.8, "top_probabilities": {"CLICK": 0.8, "WAIT": 0.15, "DONE": 0.05}})

    def test_read_checks_skips_malformed_values(self) -> None:
        spec = {"checks": {"a": "", "b": "", "c": "", "d": "", "e": "", "f": "", "g": "", "h": ""}}
        answers = {
            "a": {"type": "noul", "noul": 0.42},
            "b": {"type": "noul", "noul": 1.5},
            "c": {"type": "noul", "noul": math.nan},
            "d": {"type": "noul", "noul": True},
            "e": {"type": "noul"},
            "f": {"type": "choice", "choice": "x"},
            "g": {"type": "noul", "noul": 1},
            "h": {"type": "noul", "noul": 10**400},  # must be skipped, not raise OverflowError
        }
        self.assertEqual(read_checks(answers, spec), {"a": 0.42, "g": 1.0})

    def test_build_questions_reports_offered_keys(self) -> None:
        questions, meta = build_questions(SPEC, observation(ELEMENTS), last_operation="TYPE_TEXT")
        self.assertEqual(meta["operations"], ["CLICK", "TYPE_TEXT", "PRESS_ENTER", "SELECT", "WAIT", "DONE", "BLOCKED"])
        self.assertEqual(meta["offered"], {
            "operation": meta["operations"],
            "click_target": ["1"],
            "type_target": ["0"],
            "type_value": ["username", "password"],
            "select_target": ["2:0"],  # the disabled option is not offered
        })
        for key, offered in meta["offered"].items():
            self.assertEqual(list(questions[key]["criteria"]), offered)
        self.assertNotIn("ok", meta["offered"])  # nouls have no option set
        _, meta = build_questions(SPEC, observation(ELEMENTS[:1]), last_operation=None)
        self.assertEqual(set(meta["offered"]), {"operation", "type_target", "type_value"})
        self.assertNotIn("CLICK", meta["offered"]["operation"])

    def test_select_with_only_disabled_options_is_withdrawn(self) -> None:
        el = {"idx": 2, "role": "select", "name": "Size", "options": [{"i": 0, "text": "S", "disabled": True}]}
        questions, meta = build_questions(SPEC, observation([el]), last_operation=None)
        self.assertNotIn("SELECT", meta["operations"])
        self.assertNotIn("SELECT", meta["offered"]["operation"])
        self.assertNotIn("select_target", questions)


class BuildStateTests(unittest.TestCase):
    ELEMENTS = [
        {"idx": 0, "role": "textbox", "name": "Username", "value": "tom"},
        {"idx": 1, "role": "button", "name": "Login", "text": "Log in now"},
        {"idx": 2, "role": "checkbox", "name": "", "checked": True, "context": "Remember me"},
        {"idx": 3, "role": "select", "name": "Size", "options": [{"i": 0, "text": "S"}, {"i": 1, "text": "M", "disabled": True}]},
        {"idx": 4, "role": "button", "name": "Disabled", "disabled": True},
        {"idx": 5, "role": "link", "name": "Help"},
    ]

    def test_shape_and_order(self) -> None:
        spec = _merge(SPEC, {"notes": "dismiss the banner"})
        history = [{"step": i, "operation": "CLICK", "target": f"[{i}]", "value_key": None, "ok": True, "page_changed": True}
                   for i in range(1, 13)]
        state = build_state(spec, observation(self.ELEMENTS), 13, history)
        self.assertEqual(list(state), ["goal", "hints", "step", "page", "elements", "truncated_elements",
                                       "visible_text", "available_data_values", "recent_actions"])
        self.assertEqual(state["hints"], "dismiss the banner")
        self.assertEqual(state["step"], {"n": 13, "max": 25})
        self.assertEqual(state["page"], {"url": "http://x/", "title": "t"})
        self.assertEqual(state["truncated_elements"], 0)
        self.assertEqual(len(state["recent_actions"]), HISTORY_WINDOW)
        self.assertEqual(state["recent_actions"][0]["step"], 3)  # the oldest two of 12 fell out of the window
        self.assertNotIn("hints", build_state(SPEC, observation([]), 1, []))
        self.assertEqual(build_state(SPEC, observation([]), 1, [])["recent_actions"], [])

    def test_elements_are_records_with_operations(self) -> None:
        state = build_state(SPEC, observation(self.ELEMENTS), 1, [])
        by_index = {e["index"]: e for e in state["elements"]}
        self.assertEqual(by_index[0], {"index": 0, "role": "textbox", "label": "Username", "value": "tom",
                                       "checked": None, "context": None, "operations": ["TYPE_TEXT"]})
        self.assertEqual(by_index[1]["text"], "Log in now")
        self.assertEqual(by_index[1]["operations"], ["CLICK"])
        self.assertEqual((by_index[2]["checked"], by_index[2]["context"], by_index[2]["label"]), (True, "Remember me", ""))
        self.assertEqual(by_index[3]["options"], ["S"])  # the disabled option is not listed
        self.assertEqual(by_index[3]["operations"], ["SELECT"])
        self.assertEqual((by_index[4]["disabled"], by_index[4]["operations"]), (True, []))
        self.assertNotIn("disabled", by_index[5])
        self.assertNotIn("text", by_index[5])

    def test_operations_follow_the_data(self) -> None:
        textbox = self.ELEMENTS[0]
        self.assertEqual(element_operations(SPEC, textbox), ["TYPE_TEXT"])
        no_data = dict(SPEC, data={}, secrets=[])  # _merge would keep SPEC's keys inside an empty dict
        self.assertEqual(element_operations(no_data, textbox), [])  # nothing to type -> not a TYPE_TEXT target
        only_disabled = {"idx": 9, "role": "select", "name": "S", "options": [{"i": 0, "text": "x", "disabled": True}]}
        self.assertEqual(element_operations(SPEC, only_disabled), [])
        # build_questions offers exactly the elements the state marks as targets
        _, meta = build_questions(SPEC, observation(self.ELEMENTS), None)
        self.assertEqual(meta["offered"]["click_target"], ["1", "2", "5"])
        self.assertEqual(meta["offered"]["type_target"], ["0"])
        self.assertEqual(meta["offered"]["select_target"], ["3:0"])

    def test_secrets_are_masked_in_values(self) -> None:
        spec = _merge(SPEC, {"data": {"username": "tom", "password": "pw", "long": "x" * 50}})
        state = build_state(spec, observation([]), 1, [])
        self.assertEqual(state["available_data_values"], [
            {"key": "username", "value": "tom"},
            {"key": "password", "value": "<secret>"},
            {"key": "long", "value": "x" * 37 + "..."},
        ])
        self.assertNotIn("pw", json.dumps(state))


class CriteriaTests(unittest.TestCase):
    ELEMENTS = [
        {"idx": 0, "role": "textbox", "name": "Username", "value": "tom"},
        {"idx": 1, "role": "textbox", "name": "Password"},
        {"idx": 2, "role": "checkbox", "name": "", "checked": True, "context": "Remember me"},
        {"idx": 3, "role": "link", "name": "Help", "value": None},
        {"idx": 4, "role": "clickable", "name": "", "text": "Acme row", "context": "SKU-1005 Gadget Acme Ltd"},
        {"idx": 5, "role": "select", "name": "Size", "value": "S", "options": [{"i": 0, "text": "S"}, {"i": 1, "text": "M"}, {"i": 2, "text": "L", "disabled": True}]},
    ]

    def setUp(self) -> None:
        self.questions, self.meta = build_questions(SPEC, observation(self.ELEMENTS), None)

    def test_target_criteria_are_objects(self) -> None:
        click = self.questions["click_target"]["criteria"]
        typ = self.questions["type_target"]["criteria"]
        self.assertEqual(typ["0"], {"element": '[0] textbox "Username"', "role": "textbox", "current_value": "tom"})
        self.assertEqual(typ["1"], {"element": '[1] textbox "Password"', "role": "textbox", "current_value": ""})
        self.assertEqual(click["2"], {"element": '[2] checkbox ""', "role": "checkbox", "checked": "true", "context": "Remember me"})
        self.assertEqual(click["3"], {"element": '[3] link "Help"', "role": "link"})  # no empty fields
        self.assertEqual(click["4"], {"element": '[4] clickable ""', "role": "clickable", "text": "Acme row",
                                      "context": "SKU-1005 Gadget Acme Ltd"})
        self.assertNotIn("5", click)  # a select is a SELECT target, not a click target

    def test_fields_carry_current_value_only_and_buttons_no_value(self) -> None:
        # A textarea's observed `text` is its initial markup, a contenteditable's is its content: for fields
        # only `current_value` is offered. A submit input's `value` is its caption, never a current_value.
        elements = [
            {"idx": 0, "role": "textbox", "name": "Notes", "text": "hello there", "value": "completely new"},
            {"idx": 1, "role": "submit", "name": "Sign in", "value": "Sign in"},
            {"idx": 2, "role": "select", "name": "Size", "text": "S M", "value": "S", "options": [{"i": 0, "text": "S"}]},
            {"idx": 3, "role": "searchbox", "name": "Find"},
        ]
        questions, _ = build_questions(SPEC, observation(elements), None)
        self.assertEqual(questions["type_target"]["criteria"]["0"], {"element": '[0] textbox "Notes"', "role": "textbox", "current_value": "completely new"})
        self.assertEqual(questions["type_target"]["criteria"]["3"], {"element": '[3] searchbox "Find"', "role": "searchbox", "current_value": ""})
        self.assertEqual(questions["click_target"]["criteria"]["1"], {"element": '[1] submit "Sign in"', "role": "submit"})
        self.assertEqual(questions["select_target"]["criteria"]["2:0"], {"element": '[2] select "Size"', "option": "S", "current_value": "S"})
        state = build_state(SPEC, observation(elements), 1, [])
        self.assertNotIn("text", state["elements"][0])
        self.assertNotIn("text", state["elements"][2])
        self.assertEqual(state["elements"][1]["value"], "Sign in")  # the record keeps what was observed

    def test_select_and_value_criteria(self) -> None:
        sel = self.questions["select_target"]["criteria"]
        self.assertEqual(list(sel), ["5:0", "5:1"])  # the disabled option is not offered
        self.assertEqual(sel["5:1"], {"element": '[5] select "Size"', "option": "M", "current_value": "S"})
        self.assertEqual(self.questions["type_value"]["criteria"], {
            "username": {"key": "username", "value": "tom"},
            "password": {"key": "password", "value": "<secret>"},
        })
        self.assertNotIn("pw", json.dumps(self.questions))


class SpecValidationTests(unittest.TestCase):
    def problems(self, **overrides) -> list[str]:
        from spec import validate
        return validate(_merge(SPEC, overrides))

    def test_observation_defaults_and_bounds(self) -> None:
        self.assertEqual((DEFAULTS["observation"]["max_elements"], DEFAULTS["observation"]["max_text_chars"]), (200, 4000))
        self.assertEqual(self.problems(observation={"max_elements": 250}), [])
        self.assertEqual(self.problems(observation={"max_elements": 1, "max_text_chars": 100}), [])
        self.assertTrue(any("max_elements" in p for p in self.problems(observation={"max_elements": 0})))
        self.assertTrue(any("max_elements" in p for p in self.problems(observation={"max_elements": 251})))
        self.assertTrue(any("max_text_chars" in p for p in self.problems(observation={"max_text_chars": 50})))

    def test_screenshots_modes(self) -> None:
        self.assertEqual(DEFAULTS["observation"]["screenshots"], "key")
        for ok in (True, False, "key"):
            self.assertEqual(self.problems(observation={"screenshots": ok}), [])
        for bad in ("all", "none", 1, 0, None):
            self.assertTrue(any("screenshots" in p for p in self.problems(observation={"screenshots": bad})), bad)

    def test_cdp_url(self) -> None:
        self.assertIsNone(DEFAULTS["browser"]["cdp_url"])
        self.assertEqual(self.problems(browser={"cdp_url": "http://127.0.0.1:9222"}), [])
        self.assertEqual(self.problems(browser={"cdp_url": "ws://127.0.0.1:9222/devtools/browser/abc"}), [])
        self.assertTrue(any("cdp_url" in p for p in self.problems(browser={"cdp_url": "127.0.0.1:9222"})))
        self.assertTrue(any("cdp_url" in p for p in self.problems(browser={"cdp_url": 9222})))

    def test_settle_defaults_and_bounds(self) -> None:
        self.assertEqual((DEFAULTS["browser"]["settle_ms"], DEFAULTS["browser"]["quiet_ms"]), (400, 100))
        self.assertEqual(self.problems(), [])
        self.assertEqual(self.problems(browser={"settle_ms": 0, "quiet_ms": 0}), [])
        self.assertTrue(any("quiet_ms" in p for p in self.problems(browser={"settle_ms": 50})))  # default quiet 100 > cap
        self.assertTrue(any("settle_ms" in p for p in self.problems(browser={"settle_ms": 20000})))
        self.assertTrue(any("settle_ms" in p for p in self.problems(browser={"settle_ms": "400"})))
        self.assertTrue(any("quiet_ms" in p for p in self.problems(browser={"quiet_ms": -1})))


class FingerprintCompareTests(unittest.TestCase):
    def fp(self, **changes) -> dict:
        base = {"url": "http://x/a", "title": "A", "text_head": "hello",
                "nodes": {"0": [True, True, "", None, False, "aaaa"], "1": [True, True, "tom", None, False, "bbbb"]}}
        nodes = dict(base["nodes"])
        for k, v in changes.pop("nodes", {}).items():
            if v is None:
                nodes.pop(k, None)
            else:
                nodes[k] = v
        base["nodes"] = nodes
        base.update(changes)
        return base

    def test_scroll_and_wait_never_stale(self) -> None:
        from observe import compare_fingerprint
        for op in ("SCROLL_DOWN", "SCROLL_UP", "WAIT"):
            self.assertIsNone(compare_fingerprint(self.fp(), self.fp(url="http://y/", title="B", nodes={"0": None}), op))

    def test_target_operations_compare_only_the_target(self) -> None:
        from observe import compare_fingerprint
        before = self.fp()
        other_changed = self.fp(title="B", text_head="bye", nodes={"1": [True, True, "tom!", None, False, "cccc"]})
        self.assertIsNone(compare_fingerprint(before, other_changed, "CLICK", 0))
        self.assertEqual(compare_fingerprint(before, other_changed, "TYPE_TEXT", 1), "target [1] changed: value")
        self.assertEqual(compare_fingerprint(before, self.fp(nodes={"0": [True, True, "", None, True, "aaaa"]}), "CLICK", 0),
                         "target [0] changed: disabled")
        self.assertEqual(compare_fingerprint(before, self.fp(nodes={"0": [True, True, "", None, False, "zzzz"]}), "SELECT", 0),
                         "target [0] changed: context")
        self.assertEqual(compare_fingerprint(before, self.fp(nodes={"0": None}), "CLICK", 0), "target [0] is no longer on the page")
        self.assertEqual(compare_fingerprint(before, self.fp(url="http://x/b"), "CLICK", 0), "url changed")
        self.assertEqual(compare_fingerprint(before, self.fp(), "CLICK", 7), "target [7] was not in the observation")

    def test_whole_page_operations_compare_everything(self) -> None:
        from observe import compare_fingerprint
        before = self.fp()
        for op in ("DONE", "BLOCKED", "PRESS_ENTER"):
            self.assertIsNone(compare_fingerprint(before, self.fp(), op))
            self.assertEqual(compare_fingerprint(before, self.fp(title="B"), op), "title changed")
            self.assertEqual(compare_fingerprint(before, self.fp(text_head="bye"), op), "visible text changed")
            self.assertEqual(compare_fingerprint(before, self.fp(nodes={"1": [True, False, "tom", None, False, "bbbb"]}), op),
                             "element [1] changed: visible")
            self.assertEqual(compare_fingerprint(before, self.fp(nodes={"1": None}), op), "element [1] is no longer on the page")
            self.assertEqual(compare_fingerprint(before, self.fp(nodes={"2": [True, True, "", None, False, "dddd"]}), op),
                             "element [2] appeared")

    def test_max_stale_is_validated(self) -> None:
        from spec import validate
        self.assertEqual(DEFAULTS["thresholds"]["max_stale"], 3)
        self.assertTrue(any("max_stale" in p for p in validate(_merge(SPEC, {"thresholds": {"max_stale": 0}}))))
        self.assertTrue(any("max_repeat" in p for p in validate(_merge(SPEC, {"thresholds": {"max_repeat": "3"}}))))


class MaskSecretsTests(unittest.TestCase):
    def test_masks_every_observed_channel_and_truncated_prefixes(self) -> None:
        from observe import MASK, mask_secrets
        long_secret = "L" * 45 + "tail"  # longer than the observer's 40-char value cut
        obs = {
            "url": "http://x/", "title": "Hello hunter2-not-real",
            "elements": [
                {"idx": 0, "role": "textbox", "name": "API token", "value": "hunter2-not-real"},
                {"idx": 1, "role": "textbox", "name": "hunter2-not-real", "text": "prefix hunter2-not-real suffix"},
                {"idx": 2, "role": "checkbox", "name": "", "context": "row with hunter2-not-real inside"},
                {"idx": 3, "role": "textbox", "name": "Long", "value": long_secret[:40]},
                {"idx": 4, "role": "select", "name": "S", "options": [{"i": 0, "text": long_secret[:50]}]},
                {"idx": 5, "role": "button", "name": "Save", "value": None},
            ],
            "visible_text": "Token: hunter2-not-real and " + long_secret,
            "fingerprint": {"nodes": {"0": [True, True, "hunter2-not-real", None, False, "abcd"]}},
        }
        out = mask_secrets(obs, ["hunter2-not-real", long_secret, ""])
        self.assertIs(out, obs)
        dumped = json.dumps({k: v for k, v in out.items() if k != "fingerprint"})
        self.assertNotIn("hunter2", dumped)
        self.assertNotIn("LLLLLLLLLL", dumped)
        self.assertEqual(out["elements"][0]["value"], MASK)
        self.assertEqual(out["elements"][1]["text"], f"prefix {MASK} suffix")
        self.assertEqual(out["elements"][2]["context"], f"row with {MASK} inside")
        self.assertEqual(out["elements"][3]["value"], MASK)
        self.assertEqual(out["elements"][4]["options"][0]["text"], MASK)
        self.assertEqual(out["visible_text"], f"Token: {MASK} and {MASK}")
        self.assertEqual(out["elements"][5]["value"], None)
        self.assertEqual(out["fingerprint"]["nodes"]["0"][2], "hunter2-not-real")  # compared in Python only

    def test_no_secrets_is_a_no_op(self) -> None:
        from observe import mask_secrets
        obs = {"elements": [{"idx": 0, "role": "textbox", "name": "n", "value": "v"}], "visible_text": "t", "title": "T"}
        self.assertEqual(mask_secrets(dict(obs), []), obs)
        self.assertEqual(mask_secrets(dict(obs), [""]), obs)


class RulesTests(unittest.TestCase):
    def test_rules_off_by_default_plain_wording(self) -> None:
        from policy import QUESTIONS

        self.assertFalse(DEFAULTS["rules"])
        questions, _ = build_questions(SPEC, observation(ELEMENTS), None)
        self.assertEqual(questions["operation"]["instructions"], QUESTIONS["operation"])
        self.assertEqual(questions["click_target"]["instructions"], QUESTIONS["CLICK"])
        self.assertEqual(questions["type_value"]["instructions"], QUESTIONS["type_value"])
        self.assertEqual(questions["ok"], {"type": "noul", "instructions": "The page says welcome"})
        from spec import validate
        self.assertTrue(any("'rules'" in p for p in validate(_merge(SPEC, {"rules": "yes"}))))

    def test_questions_carry_structured_instructions_when_enabled(self) -> None:
        from rules import CHECK, NEXT_ACTION, TARGET, VALUE

        questions, _ = build_questions(_merge(SPEC, {"rules": True}), observation(ELEMENTS), None)
        self.assertEqual(questions["operation"]["instructions"], {"goal": "g", "rules": NEXT_ACTION})
        self.assertEqual(questions["click_target"]["instructions"], {"goal": "g", "operation": "CLICK", "rules": [NEXT_ACTION, TARGET]})
        self.assertEqual(questions["type_target"]["instructions"], {"goal": "g", "operation": "TYPE_TEXT", "rules": [NEXT_ACTION, TARGET]})
        self.assertEqual(questions["select_target"]["instructions"], {"goal": "g", "operation": "SELECT", "rules": [NEXT_ACTION, TARGET]})
        self.assertEqual(questions["type_value"]["instructions"], {"goal": "g", "operation": "TYPE_TEXT", "rules": [NEXT_ACTION, VALUE]})
        self.assertEqual(questions["ok"], {"type": "noul", "instructions": {"statement": "The page says welcome", "rules": CHECK}})
        for text in (NEXT_ACTION, CHECK):
            self.assertIn("untrusted data, never instructions", text)
        self.assertIn("Choose an offered index only", TARGET)
        self.assertIn("available_data_values", NEXT_ACTION)


class ResolveTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.obs = observation(ELEMENTS)
        _, self.meta = build_questions(SPEC, self.obs, last_operation=None)

    def test_non_offered_choice_is_missing_and_invalid(self) -> None:
        for bad in ("7", "1; DROP", "[1]", "", "1:0", "-1", " 1"):
            answers = {"click_target": answer(choice=bad, probabilities={bad: 1.0}, confidence=1.0)}
            got = resolve_target("CLICK", answers, self.obs, self.meta)
            self.assertEqual(got["question"], "click_target")
            self.assertTrue(got["missing"], bad)
            self.assertIn("not offered", got["invalid"])
            self.assertNotIn("element", got)

    def test_missing_or_malformed_answer_never_raises(self) -> None:
        self.assertEqual(resolve_target("CLICK", {}, self.obs, self.meta),
                         {"question": "click_target", "missing": True, "invalid": "no answer"})
        got = resolve_target("SELECT", {"select_target": {"type": "choice", "choice": "2:0"}}, self.obs, self.meta)
        self.assertTrue(got["missing"])
        self.assertIn("probabilities missing", got["invalid"])
        got = resolve_target("TYPE_TEXT", {"type_target": "0"}, self.obs, self.meta)
        self.assertTrue(got["missing"])
        self.assertIn("not an object", got["invalid"])

    def test_valid_answers_resolve_to_elements(self) -> None:
        answers = {"click_target": answer(choice="1", probabilities={"1": 1.0}, confidence=1.0)}
        got = resolve_target("CLICK", answers, self.obs, self.meta)
        self.assertEqual((got["element"], got["label"], got["question"]), (1, '[1] button "Login"', "click_target"))
        answers = {"select_target": answer(choice="2:0", probabilities={"2:0": 1.0}, confidence=1.0)}
        got = resolve_target("SELECT", answers, self.obs, self.meta)
        self.assertEqual((got["element"], got["option"]), (2, 0))
        self.assertEqual(got["label"], '[2] select "Size" -> "S"')
        self.assertIsNone(resolve_target("WAIT", answers, self.obs, self.meta))


class BenchTests(unittest.TestCase):
    """bench.py's pure parts: the per-run record derived from a trace and the per-spec aggregate."""

    TRACE = {
        "status": "passed", "pass": True, "duration_ms": 5000, "actions_executed": 2,
        "usage": {"jev_requests": 3, "input_tokens": 3000, "output_tokens": 300, "model": "jev-1"},
        "timing": {"launch_ms": 150, "navigation_ms": 2000, "setup_ms": 0, "steps_ms": 2500, "final_ms": 30},
        "steps": [
            {"n": 1, "latency_ms": {"jev": 800, "browser": 600}, "decision_confidence": 0.9,
             "executed": {"action": "TYPE_TEXT", "ok": True}},
            {"n": 2, "latency_ms": {"jev": 300, "browser": 110}, "decision_confidence": 0.4, "low_confidence": True,
             "executed": {"action": "WAIT", "ok": True, "reason": "low confidence; CLICK not executed"}},
            {"n": 3, "latency_ms": {"jev": 320, "browser": 140}, "decision_confidence": 0.95, "stale": "target [1] changed: value",
             "executed": {"action": "WAIT", "ok": True, "reason": "page changed during the decision"}},
            {"n": 4, "latency_ms": {"jev": 310, "browser": 200}, "decision_confidence": 0.85,
             "executed": {"action": "CLICK", "ok": True}},
            {"n": 5, "latency_ms": {"jev": 290}, "executed": {"action": "AUTO_DONE", "ok": True}},
        ],
    }

    def test_measure_trace_per_step_fields(self) -> None:
        from bench import measure_trace
        m = measure_trace(self.TRACE)
        self.assertEqual((m["status"], m["pass"], m["duration_ms"], m["requests"], m["input_tokens"]), ("passed", True, 5000, 3, 3000))
        self.assertEqual((m["jev_ms"], m["browser_ms"], m["steps"], m["actions_executed"]), (2020, 1050, 5, 2))
        self.assertEqual((m["decision_confidence"], m["min_decision_confidence"]), (0.875, 0.4))
        self.assertEqual((m["stale_steps"], m["low_confidence_steps"]), (1, 1))
        self.assertEqual(m["jev_first_ms"], 800)                      # the request that pays for the handshake
        self.assertEqual(m["jev_warm_ms"], 305)                       # median of 300, 320, 310, 290
        self.assertEqual(m["browser_per_action_ms"], 400)             # median of 600 and 200: WAITs are not actions
        self.assertEqual(m["action_browser_ms"], [600, 200])
        self.assertEqual(m["step_jev_ms"], [800, 300, 320, 310, 290])
        self.assertEqual(m["step_browser_ms"], [600, 110, 140, 200, None])
        self.assertEqual((m["launch_ms"], m["navigation_ms"], m["setup_ms"]), (150, 2000, 0))

    def test_measure_trace_tolerates_an_empty_trace(self) -> None:
        from bench import measure_trace
        m = measure_trace({"status": "error", "error": "boom"})
        self.assertEqual((m["status"], m["pass"], m["jev_ms"], m["browser_ms"], m["steps"]), ("error", False, 0, 0, 0))
        for k in ("decision_confidence", "jev_first_ms", "jev_warm_ms", "browser_per_action_ms", "launch_ms"):
            self.assertIsNone(m[k], k)

    def test_aggregate_pools_steps_across_runs(self) -> None:
        from bench import RUN_FIELDS, aggregate, measure_trace
        r1 = dict(measure_trace(self.TRACE), wall_ms=5200, outcome="logged_in")
        other = json.loads(json.dumps(self.TRACE))
        other["status"], other["pass"] = "blocked", False
        other["steps"][3]["latency_ms"]["browser"] = 1000
        r2 = dict(measure_trace(other), wall_ms=6000, outcome="undetermined")
        agg = aggregate([r1, r2])
        self.assertEqual(set(RUN_FIELDS) | {"decision_confidence_all_steps", "jev_warm_ms_all_steps", "browser_per_action_ms_all_steps"},
                         set(agg["medians"]))
        self.assertEqual(agg["medians"]["wall_ms"], 5600)
        self.assertEqual(agg["medians"]["jev_warm_ms_all_steps"], 305)          # 8 warm requests pooled
        self.assertEqual(agg["medians"]["browser_per_action_ms_all_steps"], 600)  # 600, 200, 600, 1000 pooled
        self.assertEqual(agg["medians"]["browser_per_action_ms"], 600)           # median of per-run medians 400 and 800
        self.assertEqual(agg["status_counts"], {"passed": 1, "blocked": 1})
        self.assertEqual(agg["outcome_counts"], {"logged_in": 1, "undetermined": 1})
        self.assertEqual((agg["passes"], agg["stale_steps_total"]), (1, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
