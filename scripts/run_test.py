"""Run one Jev browser test from a spec and write a trace and a result.

    python scripts/run_test.py path/to/spec.json [--out runs/<id>] [--headed | --headless] [--screenshots all|key|none] [--cdp-url URL]

Exit codes: 0 = the run ended in an outcome with verdict "pass", 1 = it did not (see result.json / trace
status), 2 = spec / environment problem.

No language model sits in this loop. Claude writes the spec beforehand and reads the result afterwards;
Jev makes one typed decision per step; Playwright executes. Everything here is deterministic given
Jev's answers, which is what makes the trace trustworthy evidence. Those answers are validated
against the options that were offered before anything is executed (policy.validate_choice): a
malformed `operation` answer is asked again once, then ends the run; a malformed target is never acted on.

The results contract (references/spec-format.md, "outcomes"): the spec declares the endings it accepts
back, each with a verdict; every step asks Jev which of them the page shows; a pass must survive a
settle-and-recheck and the spec's `assert` block; any other verdict is terminal at first sighting. The
run ends in exactly one outcome (or `undetermined`, with a typed reason) and writes result.json beside
trace.json.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import re
import sys
import time
from datetime import datetime, timezone

from jev_client import JevClient, JevError
from observe import (
    ANNOUNCE_FUNCTION, ANNOUNCE_INIT_JS, GUARD_SKIPPED, LINES_JS, TARGET_OPERATIONS, compare_fingerprint, element_label,
    fingerprint, loading_indicators, mask_secrets, mask_text, observe, signature,
)
from policy import (
    ADJUDICATION_MAX_LINES, ADJUDICATION_NONE, FILL_PREFIX, SUGGESTED_VERDICTS, announcement_lines, build_adjudication, build_questions,
    build_reason_questions, build_state, defer_action, deferred_outcomes, evidence_line_keys, is_field, plan_batch, quoted_pick, read_checks, read_choice,
    read_outcome, recent_announcements, resolve_target, seen_outcomes, suggested_verdict, validate_choice,
)
from replay import (ATTRS_JS, POLL_MS, REPLAYABLE, STABLE_ATTRS, VERIFY_MODES, Replay, Tokens, describe_target, find_target, match_final,
                    match_page, page_print)
from session import (DEFAULT_CACHE_DIR, DEFAULT_MAX_AGE_S, DEFAULT_SESSION_DIR, VALIDATE_WAIT_MS, CacheSlot, drop_session, load_session,
                     local_storage_script, page_mismatch, save_session, session_file, session_key, strip_profile)
from spec import (DIAGNOSTIC_ASSERTIONS, HEADED_ENV, UNDETERMINED, effective_outcomes, load_dotenv, load_spec, match_expect, resolve_headless,
                  spec_warnings, utf8_stdio, validate)
from summarize_trace import STALLED_STATUSES, is_action_step, summarize, unobserved_controls


class BrowserUnavailable(RuntimeError):
    """The browser could not be launched or attached to: an environment problem (exit 2), not a test result."""


SCREENSHOT_TIMEOUT_MS = 3000  # a capture is ~50-100 ms; a page whose web font never loads must not stall every capture


TERMINAL_STATUSES = {
    "passed": "an outcome with verdict pass was seen and confirmed (by every assertion holding on that page, or after a settle-and-recheck when the spec has no assertions), and every assertion held",
    "outcome": "a declared outcome with a verdict other than pass was seen (result.outcome names it)",
    "assert_failed": "a pass outcome was confirmed but an assertion did not hold on the final page (result.assertions)",
    "done_unverified": "Jev chose DONE confidently, and after a settle-and-recheck (repeated while the page kept changing) no pass outcome is visible",
    "blocked": "Jev chose BLOCKED: it saw no way to make progress",
    "never_violated": "a 'never' check became true (runs before the results contract; now status outcome)",
    "stuck": "the same action on the same page repeated max_repeat times",
    "low_confidence": "max_low_confidence_steps consecutive low-confidence decisions on an unchanged page (none of them executed): Jev could not choose between the offered options",
    "budget_exhausted": "max_steps or max_seconds reached (a pass first seen on the final look is not confirmed: result.reason.pending_outcome)",
    "unstable_page": "the page kept changing while Jev was deciding: max_stale consecutive decisions were stale and nothing was executed",
    "error": "the runner, browser or TypeSafe API failed",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redacted_spec(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    for k in s["secrets"]:
        s["data"][k] = "<secret>"
    for step in [*s.get("login", []), *s["setup"], *s.get("teardown", [])]:
        if step.get("action") == "fill":
            step["value"] = "<redacted>"
    return s


SETTLE_JS = r"""
(args) => new Promise(resolve => {
  const { quietMs, capMs, waitForOptions } = args;
  const t0 = performance.now();
  let frames = 0, lastMutation = t0, done = false, cap = null;
  const mo = new MutationObserver(() => { lastMutation = performance.now(); });
  const watch = { subtree: true, childList: true, attributes: true, characterData: true };
  try {
    mo.observe(document.documentElement || document, watch);
    if (args.deep) {
      // a MutationObserver does not see into a shadow root: with observation.shadow_dom each open root is watched too,
      // so a component still rendering keeps the page from counting as quiet
      const scan = root => { for (const el of root.querySelectorAll('*')) if (el.shadowRoot) { mo.observe(el.shadowRoot, watch); scan(el.shadowRoot); } };
      scan(document);
    }
  } catch (e) { /* no document yet: the frame/cap logic below still resolves */ }
  const finish = (ended) => {
    if (done) return;
    done = true;
    mo.disconnect();
    if (cap !== null) clearTimeout(cap);
    resolve({ ended, ms: Math.round(performance.now() - t0) });
  };
  cap = setTimeout(() => finish('cap'), capMs);
  // a row that only says the suggestions are loading ('Searching....', 'Loading...') is not the suggestions arriving
  // (observe.py's LOADING_OPTION, the same pattern)
  const LOADING_OPTION = /^(searching|loading|please wait|fetching|one moment)\b[\s.…]*$/i;
  const visibleOptions = () => {
    const out = [];
    for (const e of document.querySelectorAll('[role="option"]')) {
      const r = e.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight &&
          (!e.checkVisibility || e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }))) out.push(e);
    }
    return out;
  };
  // Only an option Jev did not see counts as "the suggestions arrived": every [role=option] in the
  // observation carries data-jev-idx, so a listbox elsewhere on the page or the previous query's suggestions
  // still on screen cannot end the wait early, while suggestions rendered synchronously by the typing
  // (already on screen when this settle starts) do count.
  const newOptionVisible = () => visibleOptions().some(e => !e.hasAttribute('data-jev-idx') && !LOADING_OPTION.test((e.innerText || e.textContent || '').trim().slice(0, 40)));
  const tick = () => {
    if (done) return;
    frames++;
    const now = performance.now();
    if (frames >= 2 && now - lastMutation >= quietMs) {
      if (!waitForOptions) return finish('quiet');
      if (newOptionVisible()) return finish('options');
      if (now - t0 >= 200) return finish('options_timeout');
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})
"""

AUTOCOMPLETE_ROLES = ("combobox", "searchbox")

BODY_TEXT_JS = "() => document.body ? document.body.innerText : ''"
# the same with the text inside open shadow roots after it (innerText stops at a shadow host): observation.shadow_dom
DEEP_BODY_TEXT_JS = r"""() => {
  if (!document.body) return '';
  const parts = [document.body.innerText];
  const scan = root => { for (const el of root.querySelectorAll('*')) if (el.shadowRoot) {
    for (const child of el.shadowRoot.children) if (!/^(STYLE|SCRIPT|TEMPLATE|LINK)$/.test(child.tagName)) parts.push(child.innerText || '');
    scan(el.shadowRoot); } };
  scan(document);
  return parts.join('\n');
}"""


# Network-aware settle (spec browser.settle "network"). The requests that count as "the action's": what an application
# fetches to render the next state (XHR, fetch) and what it loads to be able to (a route's script and stylesheet).
# Images, fonts and media arrive after the page can be read; a WebSocket and an EventSource never end; a frame's
# document is the frame's business. Analytics and monitoring calls are named by where they go.
NET_RESOURCE_TYPES = ("xhr", "fetch", "script", "stylesheet")
NET_IGNORED_RE = re.compile(
    r"google-analytics|googletagmanager|analytics\.google|doubleclick|googlesyndication|googleadservices|facebook\.(?:com|net)/tr|connect\.facebook|"
    r"hotjar|segment\.(?:io|com)|mixpanel|amplitude|sentry\.io|bugsnag|newrelic|nr-data|datadoghq|clarity\.ms|fullstory|intercom|"
    r"optimizely|matomo|piwik|plausible\.io|cloudflareinsights|/(?:collect|beacon|telemetry|analytics|rum|pixel|track(?:ing)?)(?:[/?.]|$)", re.I)
NET_POLL_MS = 15  # while the action's requests are in flight: look again this often
NET_ROUNDS = 4  # requests finished -> the DOM quiet again -> more requests? At most this many rounds inside the cap


class NetWatch:
    """The requests in flight, as the browser reports them (no script in the page): what `settle` reads with
    `browser.settle: "network"` to know that what an action started has finished. A request is watched from its
    `request` event to `requestfinished` / `requestfailed`; only those started after a given moment (the action's
    start) are waited for, so a long poll or a stream opened earlier holds nothing up, and one opened by the action is
    bounded by the settle's cap like everything else."""

    def __init__(self) -> None:
        self.pending: dict = {}  # request -> perf_counter() when its event was handled
        self.seen = 0

    def attach(self, page) -> None:
        def on_request(req) -> None:
            try:
                if req.resource_type in NET_RESOURCE_TYPES and not NET_IGNORED_RE.search(req.url):
                    self.pending[req] = time.perf_counter()
                    self.seen += 1
            except Exception:  # noqa: BLE001 - a request that cannot be read is not waited for
                pass

        def on_done(req) -> None:
            self.pending.pop(req, None)

        page.on("request", on_request)
        page.on("requestfinished", on_done)
        page.on("requestfailed", on_done)

    def started_since(self, since: float) -> int:
        return sum(1 for t in self.pending.values() if t >= since)


def settle(page, spec: dict, after: tuple[str | None, str | None] | None = None, net: NetWatch | None = None,
           since: float | None = None) -> dict:
    """Wait for the page to stop changing after an action, then return how the wait ended.

    With `browser.settle: "network"` and a watcher (`net`): the DOM-quiet window is `browser.network_quiet_ms` (short:
    the long window stood in for "the responses have arrived"), and after it the requests started since `since` (the
    action's start; default: this call) are waited for, then the DOM once more, inside the same cap. The result then
    carries "network": {"requests": how many were in flight, "ms": how long they were waited for, "left": still in
    flight at the cap}, and `ended` is "network" when they all finished.

    Event-based, not a fixed pause: `domcontentloaded` (short timeout, ignored on failure), then a page-side
    promise that resolves once two animation frames have passed AND the DOM has had no mutation for
    `browser.quiet_ms`, capped at `browser.settle_ms`. After TYPE_TEXT into a combobox/searchbox
    (`after=(operation, target_role)`) it also waits, up to 200 ms, for a visible `[role=option]` that Jev
    did not see in the observation (no data-jev-idx), so a prediction is not paid for before the autocomplete
    suggestions arrive, a listbox elsewhere on the page cannot end the wait, and suggestions rendered
    synchronously by the typing end it at once. A native <datalist> never produces such nodes: the runner
    passes role None for it. If the evaluate throws because
    the document navigated, it is retried once on the new document. Returns {"ended": "quiet" | "options" |
    "options_timeout" | "cap" | "navigated", "ms": wall-clock spent here}.
    """
    cap = spec["browser"]["settle_ms"]
    quiet = min(spec["browser"]["quiet_ms"], cap)
    network = net is not None and spec["browser"].get("settle") == "network"
    if network:
        quiet = min(quiet, spec["browser"]["network_quiet_ms"])
    operation, role = after or (None, None)
    args = {"quietMs": quiet, "capMs": cap, "waitForOptions": operation == "TYPE_TEXT" and role in AUTOCOMPLETE_ROLES,
            "deep": bool(spec.get("observation", {}).get("shadow_dom"))}
    t0 = time.perf_counter()

    def loaded() -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=max(cap, 1))
        except Exception:
            pass

    loaded()
    result = None
    for attempt in range(2):
        try:
            result = page.evaluate(SETTLE_JS, args)
            break
        except Exception:  # noqa: BLE001 - the document navigated while we waited (execution context destroyed)
            if attempt == 0:
                loaded()
    if not isinstance(result, dict):
        page.wait_for_timeout(quiet)
        result = {"ended": "navigated"}
    if network:
        since = t0 if since is None else since
        in_flight, t_net, waited_ms = net.started_since(since), time.perf_counter(), 0
        left = lambda: cap - (time.perf_counter() - t0) * 1000  # noqa: E731
        for _ in range(NET_ROUNDS):
            if not net.started_since(since) or left() <= 0:
                break
            while net.started_since(since) and left() > 0:
                page.wait_for_timeout(max(min(NET_POLL_MS, left()), 1))  # the browser's events are handled while this waits
            waited_ms = int((time.perf_counter() - t_net) * 1000)
            if left() <= 0:
                break
            try:  # what the responses rendered: the DOM quiet again, inside what is left of the cap
                again = page.evaluate(SETTLE_JS, {**args, "capMs": max(int(left()), 1), "waitForOptions": False})
                if isinstance(again, dict) and again.get("ended") == "cap":
                    result["ended"] = "cap"
            except Exception:  # noqa: BLE001 - a response navigated the page: the next observation waits for the new document
                loaded()
        if in_flight:
            still = net.started_since(since)
            result["network"] = {"requests": in_flight, "ms": waited_ms, **({"left": still} if still else {})}
            result["ended"] = "cap" if still or result.get("ended") == "cap" else "network"
    result["ms"] = int((time.perf_counter() - t0) * 1000)
    return result


def step_locator(page, step: dict, selector: str | None = None):
    """The first element a scripted step's `selector` matches, inside the <iframe> its `frame` names when it has one
    (a CSS selector, or a list of them for nested frames, outermost first). Playwright's CSS engine pierces open
    shadow roots by itself, so a control inside a web component needs nothing extra here."""
    scope = page
    frame = step.get("frame")
    for sel in ([frame] if isinstance(frame, str) else frame or []):
        scope = scope.frame_locator(sel)
    return scope.locator(selector or step["selector"]).first


def run_steps(page, spec: dict, steps: list[dict], results: list[dict], name: str = "setup", net: NetWatch | None = None,
              start: int = 0) -> list[dict]:
    """Deterministic Playwright steps, no Jev: `setup` before the flow (login, cookie banner, fixtures, and the
    interactions Jev is not offered: a file upload, a hover menu, a drag) and `teardown` after the verdict. Records
    land in `results` as they run (pass the trace's list, so a failing step is recorded even though this raises)."""
    timeout = spec["browser"]["action_timeout_ms"]
    for i, step in enumerate(steps):
        if i < start:  # already done (a reused session opened the page the first `goto` names)
            continue
        act = step["action"]
        rec = {"n": i, "action": act, "selector": step.get("selector"), "ok": True, "error": None}
        if step.get("frame"):
            rec["frame"] = step["frame"]
        before = fingerprint(page) if act in ("click", "press", "select") else None  # to tell a slow navigation from a failure
        t_step = time.perf_counter()
        try:
            if act == "goto":
                page.goto(step["url"], wait_until="domcontentloaded", timeout=spec["browser"]["navigation_timeout_ms"])
                rec["url"] = step["url"]
            elif act == "click":
                step_locator(page, step).click(timeout=timeout)
            elif act == "fill":
                step_locator(page, step).fill(step["value"], timeout=timeout)
            elif act == "press":
                step_locator(page, step).press(step["key"], timeout=timeout)
            elif act == "select":
                step_locator(page, step).select_option(step["value"], timeout=timeout)
            elif act == "hover":
                step_locator(page, step).hover(timeout=timeout)
            elif act == "check":
                step_locator(page, step).check(timeout=timeout)
            elif act == "uncheck":
                step_locator(page, step).uncheck(timeout=timeout)
            elif act == "upload":
                paths = step["path"] if isinstance(step["path"], list) else [step["path"]]
                missing = [p for p in paths if not os.path.isfile(p)]
                if missing:  # said plainly, before Playwright's own message about the same thing
                    raise FileNotFoundError(f"no such file (paths are relative to {os.getcwd()}): {', '.join(missing)}")
                step_locator(page, step).set_input_files(paths, timeout=timeout)
                rec["files"] = [os.path.basename(p) for p in paths]
            elif act == "drag":
                step_locator(page, step).drag_to(step_locator(page, step, step["to"]), timeout=timeout)
                rec["to"] = step["to"]
            elif act == "wait":
                page.wait_for_timeout(int(step["ms"]))
            elif act == "wait_for":
                t = int(step.get("timeout_ms", timeout))
                if step.get("selector"):
                    step_locator(page, step).wait_for(state=step.get("state", "visible"), timeout=t)
                if step.get("url"):
                    page.wait_for_url(step["url"], timeout=t)
            settle(page, spec, net=net, since=t_step)
        except Exception as e:  # noqa: BLE001 - we want every failure in the trace
            if navigation_pending(str(e)):
                rec["slow_navigation"] = await_navigation(page, spec, before, timeout)  # landed; the page is on its way
                settle(page, spec, net=net, since=t_step)
                results.append(rec)
                continue
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            results.append(rec)
            raise RuntimeError(f"{name}[{i}] ({act}) failed: {rec['error']}") from None
        results.append(rec)
    return results


def run_setup(page, spec: dict, results: list[dict] | None = None, net: NetWatch | None = None, start: int = 0) -> list[dict]:
    """The spec's `setup` steps (see run_steps), from step `start`."""
    return run_steps(page, spec, spec["setup"], [] if results is None else results, "setup", net, start)


def run_teardown(page, spec: dict, results: list[dict], net: NetWatch | None = None) -> dict:
    """The spec's `teardown` steps, after the verdict and whatever it was: best effort. The first failing step ends
    the teardown and is reported, never raised: cleaning up is not what the run was asked to judge. Returns
    {"ok", "steps", "ran"} and, on a failure, "failed": {"n", "action", "error"} (result.teardown)."""
    summary: dict = {"ok": True, "steps": len(spec["teardown"]), "ran": 0}
    try:
        run_steps(page, spec, spec["teardown"], results, "teardown", net)
    except Exception as e:  # noqa: BLE001 - recorded on the step; the run's result stands
        last = results[-1] if results and not results[-1]["ok"] else {"n": len(results), "action": None, "error": f"{type(e).__name__}: {str(e)[:300]}"}
        summary["ok"] = False
        summary["failed"] = {"n": last["n"], "action": last["action"], "error": last["error"]}
    summary["ran"] = sum(1 for r in results if r["ok"])
    return summary


DIAGNOSTIC_KINDS = ("page_errors", "console_errors", "failed_requests", "http_errors")
DIAGNOSTICS_KEPT = 50  # entries kept per kind in the trace; the counts are always complete
DIAGNOSTICS_IN_RESULT = 5  # entries per kind repeated in result.json


class Diagnostics:
    """What the browser itself says went wrong while the flow ran, kept beside what the page shows: uncaught
    JavaScript exceptions (`page_errors`), console.error messages (`console_errors`), requests that failed outright
    (`failed_requests`: DNS, refused, reset; a request the page or a navigation aborted is not a failure) and
    responses with a status of 400 or more (`http_errors`). Nothing here reaches Jev or changes a decision: it is
    evidence for whoever judges the run (a dead Save with a 500 behind it is a different ticket from a dead Save with
    nothing behind it), and what the `no_page_errors` / `no_failed_requests` assertions read.

    Every entry is masked like page text and stamped with the step whose observation first followed it (`take`), the
    convention the announcements use: an entry of step n was caused by what happened before step n looked."""

    def __init__(self, secrets: list[str]):
        self.secrets = secrets
        self.items: dict[str, list[dict]] = {k: [] for k in DIAGNOSTIC_KINDS}
        self.counts: dict[str, int] = {k: 0 for k in DIAGNOSTIC_KINDS}
        self.server_errors = 0  # http_errors with a status of 500 or more
        self._fresh: list[tuple[str, dict]] = []

    def _add(self, kind: str, rec: dict) -> None:
        self.counts[kind] += 1
        if kind == "http_errors" and rec.get("status", 0) >= 500:
            self.server_errors += 1
        self._fresh.append((kind, rec))
        if len(self.items[kind]) < DIAGNOSTICS_KEPT:
            self.items[kind].append(rec)

    def _text(self, s, cut: int = 300) -> str:
        return mask_text(" ".join(str(s or "").split())[:cut], self.secrets)

    def attach(self, page) -> None:
        """Listen on `page`. A handler never raises: a diagnostic that cannot be read is dropped, not a run error."""
        def guarded(fn):
            def handler(arg):
                try:
                    fn(arg)
                except Exception:  # noqa: BLE001
                    pass
            return handler

        def on_console(msg) -> None:
            if msg.type != "error":
                return
            text = msg.text or ""
            if text.startswith("Failed to load resource"):
                return  # the browser's echo of a response or a failure that is recorded as such
            rec = {"text": self._text(text)}
            where = (msg.location or {}).get("url")
            if where:
                rec["url"] = self._text(where, 200)
            self._add("console_errors", rec)

        def on_page_error(err) -> None:
            self._add("page_errors", {"text": self._text(getattr(err, "message", None) or err)})

        def on_request_failed(req) -> None:
            why = req.failure or ""
            if "ERR_ABORTED" in why:
                return  # cancelled by a navigation or by the page itself
            self._add("failed_requests", {"method": req.method, "url": self._text(req.url, 200), "resource": req.resource_type,
                                          "failure": self._text(why, 120)})

        def on_response(resp) -> None:
            if resp.status >= 400:
                if resp.status == 404 and resp.url.split("?", 1)[0].endswith("/favicon.ico"):
                    return  # the browser asks for it by itself; a site without one is not reporting an error
                req = resp.request
                self._add("http_errors", {"status": resp.status, "method": req.method, "url": self._text(resp.url, 200),
                                          "resource": req.resource_type})

        page.on("console", guarded(on_console))
        page.on("pageerror", guarded(on_page_error))
        page.on("requestfailed", guarded(on_request_failed))
        page.on("response", guarded(on_response))

    def reset(self) -> None:
        """Forget everything recorded so far: what the browser said while a saved session was being tried and found
        expired (the application's "log in first" page, its 401 or 404) is about the probe, not about the run."""
        self.items = {k: [] for k in DIAGNOSTIC_KINDS}
        self.counts = {k: 0 for k in DIAGNOSTIC_KINDS}
        self.server_errors = 0
        self._fresh = []

    def take(self, step: int) -> dict:
        """Stamp everything recorded since the last call with `step` and return its counts by kind (empty when nothing
        new): the step's `diagnostics`, flagged in the summary."""
        fresh, self._fresh = self._fresh, []
        counts: dict[str, int] = {}
        for kind, rec in fresh:
            rec["step"] = step
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "http_errors" and rec.get("status", 0) >= 500:
                counts["server_errors"] = counts.get("server_errors", 0) + 1
        return counts

    def any(self) -> bool:
        return any(self.counts.values())

    def for_trace(self) -> dict:
        return {"counts": {**self.counts, "server_errors": self.server_errors}, **{k: v for k, v in self.items.items() if v}}

    def for_result(self) -> dict:
        """The short form in result.json: the counts, and the first few of what most often is the story (exceptions,
        5xx responses, failed requests). 4xx responses and console errors stay in the trace."""
        out: dict = {"counts": {**self.counts, "server_errors": self.server_errors}}
        if self.items["page_errors"]:
            out["page_errors"] = self.items["page_errors"][:DIAGNOSTICS_IN_RESULT]
        server = [r for r in self.items["http_errors"] if r["status"] >= 500][:DIAGNOSTICS_IN_RESULT]
        if server:
            out["server_errors"] = server
        if self.items["failed_requests"]:
            out["failed_requests"] = self.items["failed_requests"][:DIAGNOSTICS_IN_RESULT]
        return out


def device_settings(playwright, name: str) -> dict:
    """Playwright's descriptor for the device `name` as context options (viewport, user agent, pixel ratio, touch),
    or BrowserUnavailable naming the closest matches: a misspelt device is an environment problem (exit 2), never a
    flow outcome."""
    devices = playwright.devices
    if name not in devices:
        import difflib
        close = difflib.get_close_matches(name, list(devices), n=4, cutoff=0.5)
        hint = f"; did you mean {', '.join(repr(c) for c in close)}?" if close else ""
        raise BrowserUnavailable(f"unknown browser.device {name!r}{hint} (Playwright's device names, e.g. 'iPhone 13', 'Pixel 7', 'iPad Mini')")
    return {k: v for k, v in devices[name].items() if k != "default_browser_type"}


WAIT_BACKOFF_MAX = 4  # lever F4: consecutive WAITs on an unchanged page pause settle_ms x 1, 2, 4, 4, ... (never more than x4)
CONFIRM_RECHECKS_MAX = 2  # a confirmation look at a page that changed during the pause and shows no pass looks again, this many times at most
BUSY_EXTRA_LOOKS = 2  # ... and this many more while the page is busy (a blank layer over controls, an empty document): a slow app renders in stages;
# the same two more for undecided decisions under a blank layer (low_confidence_limit), and the deferral bound (deferral_limit)


def recheck_limit(busy: bool) -> int:
    """How many confirmation looks may park again: CONFIRM_RECHECKS_MAX on a page with controls and nothing over them,
    BUSY_EXTRA_LOOKS more while the page is busy. Live: a slow demo's Save went covered form, empty shell, then the
    record's page under its own loading overlay with the fields not yet filled, three busy looks in a row, and the
    bound of two ended the run assert_failed one look before the fields rendered. A dialog that stays is not busy
    (its controls are the layer's own): it costs the plain looks and ends done_unverified."""
    return CONFIRM_RECHECKS_MAX + (BUSY_EXTRA_LOOKS if busy else 0)


def can_recheck(busy: bool, rechecks: int, waited_ms: int = 0, navigation_timeout_ms: int = 0) -> bool:
    """May a confirmation look park again? Within `recheck_limit` by count; and, while the page is busy, for as long as
    the looks have waited less than `navigation_timeout_ms` in all: a page on its way may take as long as a page may
    take to arrive here. Live: a slow demo's record page rendered some 30 s after Save, the four busy looks were 27.5 s
    of waits at settle_ms 2500, and the run ended done_unverified one look before the fields."""
    return rechecks < recheck_limit(busy) or (busy and waited_ms < navigation_timeout_ms)


def moved_since(page, before: dict | None) -> bool:
    """Has the page changed since the observation `before` is the fingerprint of (the whole-page comparison a WAIT uses)?
    Asked once, before an undecided streak ends the run: live, 0.5.1, dynamic-controls' loader ended in the ~0.3 s
    between the third undecided observation and the loading-indicator check, the check found nothing, the limit fell
    from five looks to three, and the run ended low_confidence on a page that had just finished."""
    if not before:
        return False
    try:
        return compare_fingerprint(before, fingerprint(page, before.get("frames"), before.get("deep")), "DONE") is not None
    except Exception:  # noqa: BLE001 - the document navigated meanwhile: that is a change
        return True


def low_confidence_limit(th: dict, blank: bool) -> int:
    """How many consecutive undecided (low-confidence) decisions on one page end the run `low_confidence`: the spec's
    max_low_confidence_steps on a settled page, BUSY_EXTRA_LOOKS more while the page says it is loading (`blank`: a
    blank layer over controls, an autocomplete's placeholder row, or a loading indicator that covers nothing; each
    undecided look already waits with backoff). Live: three undecided looks on a form under its loader, 2.5 + 5 +
    10 s, ended a run one look before the fields rendered in a slow hour."""
    return th["max_low_confidence_steps"] + (BUSY_EXTRA_LOOKS if blank else 0)


def loading_indicated(step: dict) -> bool:
    """Does something on the page say it is loading without covering anything (a spinner, an indeterminate progress
    bar, a 'Loading...' line: the step's `loading_indicators`, counted by observe.loading_indicators when the decision
    came back undecided)? Read only for the undecided-look limit: such a page gets the extra looks, but it is not
    `page_busy`, no action is deferred for it and no confirmation waits on it, because an indicator can be decoration
    that never goes away and those waits are long."""
    return step.get("loading_indicators", 0) > 0


def deferral_limit(th: dict) -> int:
    """How many times a marginal action under a blank layer is deferred on one page (each a wait with backoff, settle_ms
    x 1, 2, 4, 4, 4, ending when the page changes) before the next such decision is executed anyway: a layer that
    stays that long with Jev still picking a free control is taken at its word (deferrals_exhausted on the step). The
    same count as undecided looks under a blank layer. Live: the deferral fired once per page, and the second identical
    marginal decision typed the first name into the sidebar's filter, or left the Assign form for the Leave List tab,
    while the loader was still up."""
    return th["max_low_confidence_steps"] + BUSY_EXTRA_LOOKS
WAIT_POLL_MS = 100  # a WAIT re-reads the page's fingerprint this often and ends as soon as the page has changed
HOVER_REVEAL_MS = 800  # a hover menu may open after a delay (jQuery UI's default is 300 ms, hover-intent scripts 100-500):
# after a HOVER the runner waits up to this long for the page to change, ending the moment it does. Live, 0.5.0: the
# settle went quiet at ~110 ms, the jQuery UI submenu opened at 300, and every hover was flagged NO-EFFECT
NO_EFFECT_ACTIONS = {"CLICK", "TYPE_TEXT", "SELECT", "PRESS_ENTER", "HOVER", "UPLOAD_FILE"}  # an executed one of these that changed nothing is flagged
NAVIGATION_PENDING_MARKER = "waiting for scheduled navigations to finish"  # Playwright's call log after "click action done"


def navigation_pending(error: str | None) -> bool:
    """Did a timed-out action land, with only the navigation it started outstanding? Playwright performs the click
    ("click action done" in its call log) and then waits for the scheduled navigation to commit; on a slow server that
    wait, not the element, is what runs out `action_timeout_ms`. Live (OrangeHRM's demo answering a module page in
    9-12 s): every sidebar click of the run ended `TimeoutError: Locator.click: Timeout 8000ms exceeded`, the page
    arrived a second later anyway, the history told Jev the click had failed, and every later decision read 0.2-0.5.
    A log that stops at "waiting for element to be visible, enabled and stable" is a click that was never performed."""
    return bool(error) and NAVIGATION_PENDING_MARKER in error


def await_navigation(page, spec: dict, before: dict | None, spent_ms: int) -> dict:
    """The rest of a landed action whose navigation outlasted `action_timeout_ms`: wait for the page to change (the
    fingerprint Jev decided on, polled every WAIT_POLL_MS; a destroyed document counts) for what is left of the
    navigation budget. Returns {"ended": "changed" | "navigated" | "timeout" | "unknown", "ms": the action's total,
    "action_timeout_ms": spent_ms}; without a fingerprint to compare against nothing is waited for ("unknown")."""
    budget = max(spec["browser"]["navigation_timeout_ms"] - spent_ms, 0)
    if before is None or budget == 0:
        return {"ended": "unknown", "ms": spent_ms, "action_timeout_ms": spent_ms}
    waited = wait_for_change(page, before, budget)
    return {"ended": waited["ended"], "ms": spent_ms + waited["ms"], "action_timeout_ms": spent_ms}


def blank_layer(obs: dict) -> bool:
    """Do controls on this page sit under a layer that has no controls of its own? That is a loading or saving overlay
    (the page is on its way), as against a dialog, an open list or a banner over the page, whose own controls are
    offered (`layer_controls`, counted by the observer) and are the controls to use. An observation without the count
    (an older trace) reads as blank."""
    return obs.get("covered", 0) > 0 and not obs.get("layer_controls")


def page_loading(obs: dict) -> bool:
    """Is something on this page visibly on its way? Controls under a blank layer (a loading or saving overlay), or an
    autocomplete showing only its loading placeholder ('Searching....', `loading_options`, counted by the observer and
    not offered). Live: the employee name typed into the Leave List filter, the row 'Searching....' still up, and Jev
    clicked Search at 0.66-0.70 instead of the suggestion; the unchosen name filtered nothing."""
    return blank_layer(obs) or obs.get("loading_options", 0) > 0


def page_busy(obs: dict) -> bool:
    """Is this page still on its way? Something visibly loading (`page_loading`: a blank layer over controls, an
    autocomplete's placeholder row), or no controls at all (a single-page app's empty shell after a navigation, before
    it renders). Live: the Personal Details page of a slow demo was an empty document for two looks, same signature,
    and the assertions were run on it. A settled page has controls and nothing blank covers them; a dialog over the
    page is settled, its controls are the controls."""
    return page_loading(obs) or not obs.get("elements")


def assertions_can_wait(checked: list[dict], busy: bool, page_changed: bool, rechecks: int,
                        waited_ms: int = 0, navigation_timeout_ms: int = 0) -> bool:
    """A pass is in sight but an assertion does not hold: has this look ruled out timing? Not while the page is busy
    (`page_busy`: a blank layer over controls, an empty shell) or changed during the pause, within the recheck bound
    (`can_recheck`: CONFIRM_RECHECKS_MAX by count, and for a busy page as long as `navigation_timeout_ms`). Live: a
    Save's toast announced the pass while the overlay still covered the form and the URL was still the form's; the
    assertions were run there and the run ended `assert_failed` two seconds before the page it asserted arrived. On a
    settled page a failing assertion is the verdict at once."""
    return any(not a["ok"] for a in checked) and (busy or page_changed) and can_recheck(busy, rechecks, waited_ms, navigation_timeout_ms)


def wait_for_change(page, before: dict | None, wait_ms: int) -> dict:
    """A WAIT that ends early. Instead of sleeping the whole pause, re-read the page's fingerprint every WAIT_POLL_MS
    and return as soon as it no longer matches the one Jev decided on (the whole-page comparison: url, title, text
    head, every tagged node), else when `wait_ms` is up. Lever F4's doubling pauses overshot a 5 s loader's end by
    up to 1.6 s; polling caps the overshoot at one poll interval, and the pause is still the ceiling.
    Returns {"ended": "changed" | "timeout" | "navigated", "ms": wall-clock spent}."""
    t0 = time.perf_counter()
    while True:
        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed >= wait_ms:
            return {"ended": "timeout", "ms": int(elapsed)}
        page.wait_for_timeout(min(WAIT_POLL_MS, wait_ms - elapsed))
        if before is None:
            continue
        try:
            changed = compare_fingerprint(before, fingerprint(page, before.get("frames"), before.get("deep")), "DONE") is not None
        except Exception:  # noqa: BLE001 - the document navigated: that is a change
            return {"ended": "navigated", "ms": int((time.perf_counter() - t0) * 1000)}
        if changed:
            return {"ended": "changed", "ms": int((time.perf_counter() - t0) * 1000)}


def scroll_page(page, direction: int) -> dict:
    """SCROLL_DOWN / SCROLL_UP: window.scrollBy by 80% of the viewport; when the window did not move (an app shell whose
    content scrolls inside an overflow container), a wheel event at the viewport's centre scrolls whatever is under it.
    Returns what moved and by how much (recorded on the step as `executed.scroll`)."""
    delta = direction * int(page.evaluate("Math.round(window.innerHeight * 0.8)"))
    before = page.evaluate("window.scrollY")
    page.evaluate(f"window.scrollBy(0, {delta})")
    if page.evaluate("window.scrollY") != before:
        return {"scrolled": "window", "by": delta}
    size = page.viewport_size or {"width": 1280, "height": 800}
    page.mouse.move(size["width"] / 2, size["height"] / 2)
    page.mouse.wheel(0, delta)
    page.wait_for_timeout(100)  # the wheel does not wait for the scroll it starts
    return {"scrolled": "wheel", "by": delta}


def execute(page, spec: dict, operation: str, target: dict | None, value_key: str | None, wait_ms: int | None = None,
            before: dict | None = None, frame: str | None = None) -> dict:
    """Perform one operation. `before` is the observation's fingerprint: a WAIT ends as soon as the page differs from it.
    `frame` is the <iframe> selector of a target the observer found inside a listed frame (its element's `frame`)."""
    timeout = spec["browser"]["action_timeout_ms"]
    res: dict = {"action": operation, "ok": True, "error": None}
    try:
        if operation in ("CLICK", "TYPE_TEXT", "SELECT", "HOVER", "UPLOAD_FILE"):
            if not target or target.get("missing"):
                raise RuntimeError("no target answer for this operation")
            scope = page.frame_locator(frame) if frame else page
            loc = scope.locator(f'[data-jev-idx="{target["element"]}"]').first
            res["element"] = target["element"]
            if frame:
                res["frame"] = frame
        if operation == "CLICK":
            try:
                loc.click(timeout=timeout)
            except Exception as first:  # something sits on top of the element
                if "intercepts pointer events" not in str(first):
                    raise
                is_control = loc.evaluate("el => el.tagName === 'INPUT' || el.tagName === 'LABEL'")
                if is_control:
                    # A hidden checkbox/radio under its styled box: a forced pointer click lands on the
                    # box and is swallowed. Fire the click on the control itself instead (this is what
                    # frameworks' onChange listens to for checkboxes).
                    loc.dispatch_event("click")
                    res["dispatched"] = True
                else:
                    loc.click(timeout=timeout, force=True)
                    res["forced"] = True
        elif operation == "TYPE_TEXT":
            if not value_key or value_key not in spec["data"]:
                raise RuntimeError("no usable type_value answer")
            res["value_key"] = value_key
            value = spec["data"][value_key]
            try:
                loc.fill(value, timeout=timeout)
            except Exception:  # contenteditable / custom inputs don't support fill
                loc.click(timeout=timeout)
                loc.press_sequentially(value, timeout=timeout)
        elif operation == "HOVER":
            # the pointer stays where it is put: the menu it opens is on the next observation, and a click on one of its
            # items moves the pointer there without leaving the menu
            loc.hover(timeout=timeout)
            res["reveal"] = wait_for_change(page, before, HOVER_REVEAL_MS)  # {"ended": "changed" | "timeout" | ..., "ms"}
        elif operation == "UPLOAD_FILE":
            files = spec.get("files") or {}
            if not value_key or value_key not in files:
                raise RuntimeError("no usable upload_file answer")
            res["file_key"] = value_key
            if not os.path.isfile(files[value_key]):
                raise FileNotFoundError(f"no such file (paths are relative to {os.getcwd()}): {files[value_key]}")
            loc.set_input_files(files[value_key], timeout=timeout)  # no click, no file dialog: works on a hidden field too
            res["file"] = os.path.basename(files[value_key])
        elif operation == "PRESS_ENTER":
            page.keyboard.press("Enter")
        elif operation == "SELECT":
            res["option"] = target["option"]
            loc.select_option(index=target["option"], timeout=timeout)
        elif operation == "SCROLL_DOWN":
            res["scroll"] = scroll_page(page, 1)
        elif operation == "SCROLL_UP":
            res["scroll"] = scroll_page(page, -1)
        elif operation == "WAIT":
            res["wait_ms"] = spec["browser"]["settle_ms"] if wait_ms is None else wait_ms  # the ceiling: the loop's backoff, else settle_ms
            res["wait"] = wait_for_change(page, before, res["wait_ms"])  # ends when the page changes; then the loop's normal settle
        else:
            raise RuntimeError(f"unknown operation {operation}")
    except Exception as e:  # noqa: BLE001
        if navigation_pending(str(e)):
            # The action was performed; the page it asked for has not answered within action_timeout_ms. Wait for it
            # (what is left of the navigation budget) and report the action as landed, slow: Jev's history must not
            # say a click failed when the page then arrives.
            res["slow_navigation"] = await_navigation(page, spec, before, timeout)
        else:
            res["ok"] = False
            res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    return res


def note_invalid(step: dict, text: str) -> None:
    """Append one '<question>: <reason>' to step["invalid_answer"] (several are joined with '; ')."""
    step["invalid_answer"] = f"{step['invalid_answer']}; {text}" if step.get("invalid_answer") else text


def add_usage(a: dict | None, b: dict | None) -> dict | None:
    """The token usage of two requests made for one step (a retry, the reason follow-up), added up."""
    if not a or not b:
        return b or a
    out = dict(a)
    for k, v in b.items():
        out[k] = (a.get(k) or 0) + v if isinstance(v, (int, float)) and isinstance(a.get(k, 0), (int, float)) else v
    return out


def latency_of(resp: dict, started: float) -> int:
    """The Jev round trip in ms: the client's own measurement when it has one, else ours."""
    return resp.get("latency_ms", int((time.perf_counter() - started) * 1000))


def history_entry(n: int, operation: str, target: dict | None, value_key: str | None, executed: dict) -> dict:
    """One `recent_actions` record for Jev: what was done at step n and whether it worked.

    `page_changed` is filled in when the next observation exists (see `run`); until then it is None.
    """
    entry = {
        "step": n,
        "operation": operation,
        "target": target["label"] if target and not target.get("missing") else None,
        "value_key": value_key,
        "ok": executed["ok"],
        "page_changed": None,
    }
    if not executed["ok"]:
        entry["error"] = (executed.get("error") or "")[:80]
    return entry


NAVIGATION_RACE_MARKERS = ("Execution context was destroyed", "Cannot find context with specified id", "Frame was detached")


def observe_after_navigation(page, spec: dict, observe_fn, on_retry=None, retries: int = 2):
    """`observe_fn()` made to survive a navigation landing during the evaluate ("Execution context was destroyed":
    a saved form's redirect arriving while the page is being read). Wait for the new document, settle, look again,
    up to `retries` times, calling `on_retry()` each time; any other error, or the race persisting, propagates.
    Measured live: a slow admin app's Save navigated during the confirmation look and ended the run `error`."""
    for attempt in range(retries + 1):
        try:
            return observe_fn()
        except Exception as e:  # noqa: BLE001 - only the navigation race is retried
            if attempt == retries or not any(m in str(e) for m in NAVIGATION_RACE_MARKERS):
                raise
            if on_retry is not None:
                on_retry()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=spec["browser"]["navigation_timeout_ms"])
            except Exception:  # noqa: BLE001 - settle() waits for the new document to hold still either way
                pass
            settle(page, spec)


def wait_entry(n: int, operation: str, reason: str) -> dict:
    """A runner-inserted wait (low confidence, outcome confirmation) as Jev should see it in recent_actions."""
    return {"step": n, "operation": operation, "reason": reason, "ok": True, "page_changed": None}


def glob_to_regex(glob: str) -> str:
    """Playwright's URL glob (playwright 1.52+) as a regex, so `assert.url_matches` and `setup.wait_for.url`
    read the same way: `*` = anything but '/', `**` = anything (`/**/` also matches no segment), `{a,b}` =
    either, `\\x` = the literal x; everything else, `?` and `[` included, is literal."""
    out, i, in_group = [], 0, False
    while i < len(glob):
        c = glob[i]
        if c == "\\" and i + 1 < len(glob):
            out.append(re.escape(glob[i + 1]))
            i += 2
            continue
        if c == "*":
            j = i
            while j < len(glob) and glob[j] == "*":
                j += 1
            if j - i > 1:
                if glob[j:j + 1] == "/":
                    out.append("((.+/)|)" if glob[i - 1:i] == "/" else "(.*/)")
                    j += 1
                else:
                    out.append("(.*)")
            else:
                out.append("([^/]*)")
            i = j
            continue
        if c == "{":
            in_group = True
            out.append("(")
        elif c == "}" and in_group:
            in_group = False
            out.append(")")
        elif c == "," and in_group:
            out.append("|")
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


ASSERT_MAX_ELEMENTS = 5000  # the assertion oracle is not a Choice: no need to cut the page to 255 rows
ELEMENT_ASSERTIONS = ("field_value", "element_present", "element_absent")
ELEMENT_TEXTS_JS = "(sel) => Array.from(document.querySelectorAll(sel)).map(e => e.innerText !== undefined ? e.innerText : (e.textContent || ''))"


def check_assertions(spec: dict, page, obs: dict, secrets: list[str] | None = None, diagnostics=None) -> list[dict]:
    """Evaluate the spec's `assert` block in code on the final page (spec §5.1): free, exact, non-model.

    Each record repeats the assertion, adds `ok` and `actual` (the value found, or what was there instead).
    `url_matches` is a Playwright glob over the final URL; `text_contains` looks in the whole page text;
    `text_in` looks only inside the elements a CSS selector matches (`{selector, contains}` or `{selector, equals}`),
    which is how a notification's text is asserted on a page whose body copy also mentions it; `text_order` is a
    list of strings that must appear in the page text in that order, each found after the previous one (a sorted
    list); `field_value` matches a text field / select whose accessible name contains the given label
    (case-insensitive) and compares its value; `element_present` / `element_absent` match role and, when given,
    a name substring.
    The element assertions look at the WHOLE document (observe(..., whole_document=True)), not at the
    viewport-and-hit-tested table Jev chose from, so a Logout link below the fold is present and an alert
    below the fold is not absent. Comparisons use the real page; `actual` is masked with `secrets` before
    it is written, so a secret can be asserted on without reaching the trace.
    `text_in` takes an optional `frame` (an <iframe>'s CSS selector, or a list for nested frames): the selector is
    then looked for inside that frame. `no_page_errors` / `no_failed_requests` read `diagnostics` (the run's
    Diagnostics): no uncaught JavaScript exception so far; no request that failed outright and no 5xx response.
    """
    results = []
    secrets = secrets or []
    deep = bool((spec.get("observation") or {}).get("shadow_dom"))  # the page's shadow roots are part of what is asserted on
    body_text: str | None = None
    elements: list[dict] | None = None
    url = page.url
    for a in spec.get("assert") or []:
        (kind, arg), = a.items()
        if isinstance(arg, (str, bool)):
            shown = mask_text(arg, secrets)
        elif isinstance(arg, list):
            shown = [mask_text(v, secrets) for v in arg]
        else:
            shown = {k: mask_text(v, secrets) for k, v in arg.items()}
        rec: dict = {kind: shown, "ok": False, "actual": None}
        if kind in DIAGNOSTIC_ASSERTIONS:
            if diagnostics is None:  # a caller outside a run: nothing was recorded, nothing can be said against it
                rec["ok"], rec["actual"] = True, "not recorded"
            elif kind == "no_page_errors":
                rec["ok"] = diagnostics.counts["page_errors"] == 0
                rec["actual"] = [e["text"] for e in diagnostics.items["page_errors"][:3]] or "none"
            else:
                bad = ([f'{r["method"]} {r["url"]}: {r["failure"]}' for r in diagnostics.items["failed_requests"]]
                       + [f'{r["status"]} {r["method"]} {r["url"]}' for r in diagnostics.items["http_errors"] if r["status"] >= 500])
                rec["ok"] = diagnostics.counts["failed_requests"] == 0 and diagnostics.server_errors == 0
                rec["actual"] = bad[:3] or "none"
            results.append(rec)
            continue
        if kind in ELEMENT_ASSERTIONS and elements is None:
            try:
                elements = observe(page, ASSERT_MAX_ELEMENTS, 100, whole_document=True, shadow_dom=deep)["elements"]
            except Exception:  # noqa: BLE001 - fall back to what the observer saw
                elements = obs["elements"]
        if kind == "url_matches":
            rec["actual"] = mask_text(url, secrets)
            rec["ok"] = re.fullmatch(glob_to_regex(arg), url) is not None
        elif kind in ("text_contains", "text_order"):
            if body_text is None:
                try:
                    body_text = page.evaluate(DEEP_BODY_TEXT_JS if deep else BODY_TEXT_JS)
                except Exception:  # noqa: BLE001 - fall back to what the observer saw
                    body_text = obs["visible_text"]
            if kind == "text_contains":
                at = body_text.find(arg)
                rec["ok"] = at >= 0
                excerpt = body_text[max(0, at - 60):at + len(arg) + 60] if at >= 0 else re.sub(r"\s+", " ", body_text)[:200]
                rec["actual"] = mask_text(excerpt, secrets)
            else:
                # each string must be found after the end of the previous one: the order of a list, a table, a menu
                pos, ok, found = 0, True, []
                for needle in arg:
                    at = body_text.find(needle, pos) if ok else -1
                    found.append({"text": mask_text(needle, secrets), "at": at if at >= 0 else None})
                    if at < 0:
                        ok = False
                    else:
                        pos = at + len(needle)
                rec["ok"] = ok
                rec["actual"] = found
        elif kind == "text_in":
            try:
                if arg.get("frame"):
                    scope = page
                    for sel in ([arg["frame"]] if isinstance(arg["frame"], str) else arg["frame"]):
                        scope = scope.frame_locator(sel)
                    texts = [t for t in scope.locator(arg["selector"]).all_inner_texts() if isinstance(t, str)]
                elif deep:
                    texts = [t for t in page.locator(arg["selector"]).all_inner_texts() if isinstance(t, str)]  # a locator reaches into shadow roots
                else:
                    texts = [t for t in page.evaluate(ELEMENT_TEXTS_JS, arg["selector"]) if isinstance(t, str)]
            except Exception:  # noqa: BLE001 - a selector the page rejects, or the page is gone
                texts = []
            if "equals" in arg:
                rec["ok"] = any(t.strip() == arg["equals"] for t in texts)
            else:
                rec["ok"] = any(arg["contains"] in t for t in texts)
            rec["actual"] = [mask_text(re.sub(r"\s+", " ", t).strip()[:200], secrets) for t in texts[:5]] or "no element matches the selector"
        elif kind == "field_value":
            fields = [e for e in elements if is_field(e) and arg["label"].lower() in (e.get("name") or "").lower()]
            values = [e.get("value") or "" for e in fields]
            rec["ok"] = arg["equals"] in values
            rec["actual"] = {mask_text(f'[{e["idx"]}] {element_label(e)}', secrets): mask_text(v, secrets)
                             for e, v in zip(fields, values)} or "no field with that label"
        elif kind in ("element_present", "element_absent"):
            want = (arg.get("name") or "").lower()
            matches = [e for e in elements if e["role"] == arg["role"] and (not want or want in (e.get("name") or "").lower())]
            rec["ok"] = bool(matches) if kind == "element_present" else not matches
            rec["actual"] = [mask_text(f'[{e["idx"]}] {element_label(e)}', secrets) for e in matches[:5]] or "no such element"
        results.append(rec)
    return results


def adjudication_request(page, name: str, when: str, secrets: list[str] | None = None, extra_lines: list[str] | None = None,
                         deep: bool = False) -> dict | None:
    """The evidence questions for a seen outcome (spec §5.4) over the current page's numbered lines, ready to send
    alone (`adjudicate`) or riding in a confirmation step's request (the loop merges them: one round trip fewer
    for every pass). None when the page text cannot be read. The lines are masked like every observation.
    `extra_lines` (the messages the page announced recently, policy.announcement_lines) follow the page's lines, kept
    within the cap: a toast that has faded is then a line Jev can point at, and one still on the page is quoted from it."""
    try:
        # `deep` (observation.shadow_dom): the lines inside shadow roots are quotable too
        lines = [mask_text(ln, secrets or []) for ln in page.evaluate(LINES_JS, {"maxLines": ADJUDICATION_MAX_LINES, "deep": bool(deep)})]
    except Exception:  # noqa: BLE001 - the page is gone or navigating
        return None
    extra = list(extra_lines or [])[:ADJUDICATION_MAX_LINES // 2]
    lines = lines[:ADJUDICATION_MAX_LINES - len(extra)] + extra
    state, questions, offered = build_adjudication(name, when, lines)
    # one key for a one-sentence statement, one per sentence otherwise
    return {"name": name, "state": state, "questions": questions, "offered": offered, "keys": evidence_line_keys(questions)}


def read_adjudication(rec: dict, answers: dict, req: dict) -> None:
    """Fill `rec` (line, line_id, confidence, present, sentences, invalid_answer) from the answers to `req`."""
    state, questions, offered, keys = req["state"], req["questions"], req["offered"], req["keys"]
    picks: list[dict | None] = []
    invalid = []
    for key in keys:
        picked = read_choice(answers, key, offered)
        if picked is None:
            invalid.append(f"{key}: {validate_choice(answers.get(key), offered)}")
            picks.append(None)
            continue
        line = state["lines"][int(picked["choice"]) - 1]["text"] if picked["choice"] != ADJUDICATION_NONE else None
        picks.append({"line_id": picked["choice"], "line": line, "confidence": picked["confidence"]})
    if invalid:
        rec["invalid_answer"] = "; ".join(invalid)
    if len(keys) > 1:
        # every sentence's pick is kept; `line` below is the most confident sentence's line (`quoted_pick`)
        rec["sentences"] = [{"sentence": questions[k]["instructions"]["sentence"],
                             **(p or {"line_id": None, "line": None, "confidence": None})} for k, p in zip(keys, picks)]
    quoted = quoted_pick(picks)
    if quoted:
        rec["line_id"], rec["line"], rec["confidence"] = quoted["line_id"], quoted["line"], quoted["confidence"]
    present = answers.get("evidence_present")
    if isinstance(present, dict) and isinstance(present.get("noul"), (int, float)) and 0 <= present["noul"] <= 1:
        rec["present"] = round(float(present["noul"]), 3)


def adjudicate(page, jev, name: str, when: str, secrets: list[str] | None = None, prefetched: dict | None = None,
               extra_lines: list[str] | None = None, deep: bool = False) -> dict:
    """The evidence for a seen outcome (spec §5.4): Jev selects the line of the final page that states the outcome
    (`evidence_line`; one Choice per sentence of a compound statement, the most confident sentence's line is
    quoted) and re-judges the statement (`evidence_present`). The chosen line is copied verbatim into the result:
    selection is how a quote is produced. With `prefetched` (the request the loop merged into the confirmation
    step plus that step's `answers`) no request is made at all; otherwise it is one extra request. Never fatal:
    the run was already decided when this is asked, so any failure (transport, a non-JSON body, a malformed
    answer) is recorded on the record instead of raised."""
    rec: dict = {"outcome": name, "statement": when, "line": None, "line_id": None, "present": None, "confidence": None}
    if prefetched is not None:
        rec["merged"] = True  # rode in the confirmation step's request: its tokens are on that step, no extra latency
        try:
            read_adjudication(rec, prefetched["answers"], prefetched)
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        return rec
    req = adjudication_request(page, name, when, secrets, extra_lines, deep)
    if req is None:
        rec["error"] = "could not read the page text"
        return rec
    t0 = time.perf_counter()
    try:
        resp = jev.system_one(req["state"], req["questions"])
        rec["latency_ms"] = latency_of(resp, t0)
        rec["usage"] = resp.get("usage")
        answers = resp["answers"] if isinstance(resp.get("answers"), dict) else {}
        read_adjudication(rec, answers, req)
    except Exception as e:  # noqa: BLE001 - JevError or anything the seam returned that is not the expected shape
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    return rec


# The statuses whose terminal step's `blocked_reason` answer says something about the ending (spec §5.3). For
# done_unverified, assert_failed, unstable_page and error the answer is about progress on that page, not about
# the verdict, so the status row alone decides the suggestion.
BLOCKED_REASON_STATUSES = {"blocked", "stuck", "low_confidence", "budget_exhausted"}


def build_result(trace: dict, spec: dict, outcomes: dict, final: dict, out_dir: str) -> dict:
    """result.json (spec §5.5): the one file Claude reads first. `final` is the loop's verdict record:
    {outcome: {name, verdict, probability, confidence}, seen_at_step, first_seen_at_step, confirmed,
    assertions, adjudication}; the typed reasons come from the terminal step."""
    status = trace["status"]
    steps = trace["steps"]
    # A pass whose assertions failed is not that outcome: it is undetermined, with the failing assertions
    # (Claude decides whether the assertion or the app is wrong). The sighting is kept under reason.outcome_seen.
    seen = final.get("outcome") if status in ("passed", "outcome") else None
    seen_step = next((s for s in steps if s["n"] == final.get("seen_at_step")), None)
    terminal = steps[-1] if steps else {}
    action_steps = [s for s in steps if is_action_step(s)]
    confs = [s["decision_confidence"] for s in action_steps if isinstance(s.get("decision_confidence"), (int, float))]
    story = []
    for s in action_steps:
        line = f"{s['n']} {(s.get('executed') or {}).get('action')}"
        if (s.get("target") or {}).get("label"):
            line += f" {s['target']['label']}"
        if (s.get("type_value") or {}).get("choice"):
            line += f" <- {s['type_value']['choice']}"
        if (s.get("upload_file") or {}).get("choice"):
            line += f" <- file {s['upload_file']['choice']}"
        if not (s.get("executed") or {}).get("ok", True):
            line += "  (failed)"
        story.append(line)
    result: dict = {
        "spec_id": spec["id"],
        "outcome": seen["name"] if seen else UNDETERMINED,
        "verdict": seen["verdict"] if seen else None,
        "note": outcomes[seen["name"]].get("note") if seen else None,
        "probability": seen.get("probability") if seen else None,
        "confidence": seen.get("confidence") if seen else None,
        "seen_at_step": final.get("seen_at_step"),
        "first_seen_at_step": final.get("first_seen_at_step") if seen else None,
        "confirmed": final.get("confirmed", False) if seen else False,
        "confirmed_by": final.get("confirmed_by") if seen and final.get("confirmed") else None,  # "assertions" | "recheck"
        "path_confidence": min(confs) if confs else None,
        "reason": None,
        "evidence": {
            "line": (final.get("adjudication") or {}).get("line"),
            "present": (final.get("adjudication") or {}).get("present"),
            "screenshot": (seen_step or {}).get("screenshot") or (trace.get("final") or {}).get("screenshot"),
            "checks": (seen_step or terminal).get("checks", {}),
            # only when the line was not asked (spec evidence "failures", a pass whose assertions hold): why
            **({"skipped": final["adjudication"]["skipped"]} if (final.get("adjudication") or {}).get("skipped") else {}),
        },
        "assertions": final.get("assertions") or [],
        # every non-pass sighting that is not the result itself (the confirming step's included), and every pass
        # sighting that vanished on its recheck (a flapping success toast is worth knowing about)
        "outcomes_seen_earlier": [{"step": s["n"], "outcome": s["outcome_seen"]} for s in steps if s.get("outcome_seen")
                                  and not (seen and s["n"] == final.get("seen_at_step") and s["outcome_seen"] == seen["name"])]
                                 + [{"step": s["n"], "outcome": s["outcome_unconfirmed"], "unconfirmed": True}
                                    for s in steps if s.get("outcome_unconfirmed")],
        # every toast / live message the page announced during the run, with the step whose observation it preceded:
        # what the app said about each action, whether or not it was still on screen when the runner looked
        "announcements": [{"step": s["n"], **{k: a[k] for k in ("text", "kind", "tone") if a.get(k)}}
                          for s in steps for a in s.get("announcements") or []],
        "story": story,
        "run_stamp": spec.get("run_stamp"),  # the value ${RUN_STAMP} took in this run (None when the spec has none)
        "status": status,
        "duration_ms": trace["duration_ms"],
        "usage": trace["usage"],
        "trace": os.path.join(out_dir, "trace.json"),
    }
    if not seen:
        blocked = (terminal.get("blocked_reason") or {}).get("choice")
        stuck = (terminal.get("stuck_reason") or {}).get("choice")
        if stuck is None and status == "budget_exhausted":
            # The final look asks no stuck_reason. A budget spent on a streak of WAITs (Jev's, or the runner's
            # after refused decisions) on a page that never changed is reported with the last reason Jev gave
            # for the no-op (`still_loading`: the page was still loading when the budget ran out).
            for s in reversed(steps[:-1]):
                if (s.get("executed") or {}).get("action") != "WAIT":
                    break
                if s.get("stuck_reason"):
                    stuck = s["stuck_reason"].get("choice")
                    break
        # Which typed answers speak for the ending, in order: for `stuck` and a budget spent waiting the no-op
        # reason first; for `blocked` Jev's own blocked_reason first and then, when it has no row of its own
        # (`other`, `nothing`) and BLOCKED came right after an action that changed nothing, that step's
        # stuck_reason (measured on a dead Finish button: one click, page_changed false, then BLOCKED with
        # blocked_reason other 0.62 and stuck_reason control_had_no_effect 0.97: the second answer is the verdict).
        if status in ("stuck", "budget_exhausted"):
            typed = [stuck, blocked]
        elif status == "blocked":
            typed = [blocked, stuck]
        elif status in BLOCKED_REASON_STATUSES:
            typed = [blocked]
        else:
            typed = []
        result["reason"] = {
            "status": status,
            "blocked_reason": blocked,
            "stuck_reason": stuck,
            "suggested_verdict": suggested_verdict(status, typed),
        }
        # A stalled run on a page that keeps controls where the spec did not let the observer look (an unlisted
        # <iframe>, shadow DOM turned off, a file field without `files`): the summary's hints, in the result too. And
        # when the typed reason that decided the suggestion is `control_not_on_page`, the suggestion is test_issue,
        # not bug: "not on this page" is what a control inside an unobserved frame looks like to Jev. Live, the
        # Polymer shop with shadow DOM off: low_confidence, control_not_on_page, suggested bug, beside a hint that
        # named the option. Any other reason (a dead control, a refusal) keeps its suggestion: most pages have an
        # <iframe> somewhere.
        hints = unobserved_controls(spec, terminal) if status in STALLED_STATUSES else []
        if hints:
            result["reason"]["hints"] = hints
            if next((r for r in typed if r and SUGGESTED_VERDICTS.get(r)), None) == "control_not_on_page":
                result["reason"]["suggested_verdict"] = "test_issue"
                result["reason"]["suggestion_from"] = "hints"
        if status == "assert_failed":
            result["reason"]["outcome_seen"] = (final.get("outcome") or {}).get("name")
            result["reason"]["failed_assertions"] = [a for a in result["assertions"] if not a["ok"]]
        if status == "done_unverified":
            # The last look that evaluated the assertions while a pass was in sight: which held (the record's URL) and
            # which did not yet (the name under a loader). Live, a slow hour: the URL assertion held on the new employee's
            # page two looks before the run gave up, and only the trace said so.
            last = next((s for s in reversed(steps) if s.get("assertions_checked")), None)
            if last:
                result["reason"]["last_look_step"] = last["n"]
                result["reason"]["assertions_at_last_look"] = last["assertions_checked"]
        if status == "budget_exhausted" and terminal.get("pending_outcome"):
            # a pass first seen on the final look: the budget ran out before it could be rechecked
            result["reason"]["pending_outcome"] = terminal["pending_outcome"]
        if status == "error":
            result["reason"]["error"] = trace.get("error")
            phase = trace.get("failed_before_observation")
            if phase:
                # the start page never loaded (navigation) or a scripted setup step failed (setup): the flow was
                # not exercised, so this is the environment or the spec, never the app; exit 2, and run_suite keeps
                # it out of the outcome distribution
                result["reason"]["phase"] = phase
                result["reason"]["suggested_verdict"] = "flaky" if phase == "navigation" else "test_issue"
    return result


SCREENSHOT_MODES = (True, False, "key")


def run(spec: dict, jev, out_dir: str, screenshots: bool | str | None = None) -> dict:
    """Execute the spec. `jev` is anything with .system_one(state, questions) and .usage_summary().

    `screenshots`: True (every step), False (none, not even final.png) or "key" (terminal and flagged
    steps only); None takes the spec's `observation.screenshots`. The browser mode is `spec["browser"]["headless"]`
    as main() resolved it (CLI flag, then JEV_HEADED, then the spec: spec.resolve_headless). Writes trace.json
    and result.json into out_dir and returns the trace (the result is under trace["result"]).
    """
    from playwright.sync_api import sync_playwright

    mode = spec["observation"]["screenshots"] if screenshots is None else screenshots
    if not (mode is True or mode is False or mode == "key"):
        raise ValueError(f"screenshots must be one of {SCREENSHOT_MODES}, got {mode!r}")
    th = spec["thresholds"]
    budget = spec["budget"]
    obs_cfg = spec["observation"]
    deep = bool(obs_cfg.get("shadow_dom"))  # observe, re-read, settle, assert and quote inside open shadow roots too
    outcomes = effective_outcomes(spec)  # declared + synthesized: the runner only knows outcomes

    trace: dict = {
        "spec_id": spec["id"],
        "started_at": now_iso(),
        "status": None,
        "pass": False,
        "outcome": None,
        "verdict": None,
        "steps": [],
        "login": [],
        "setup": [],
        "teardown": [],
        "final": None,
        "spec": redacted_spec(spec),
        "outcomes": outcomes,
    }
    t_start = time.perf_counter()
    history: list[dict] = []
    last_operation: str | None = None
    last_page_changed: bool | None = None  # of the last executed action, once the next observation exists
    wait_streak, last_wait_sig = 0, None  # lever F4: consecutive Jev WAITs on the same page signature
    after_no_effect = False  # the last executed action changed nothing: the next step shows that page (a key picture)
    low_streak, last_low_sig = 0, None  # consecutive undecided (low-confidence) steps on one page signature
    defer_streak, last_defer_sig = 0, None  # consecutive deferrals of a marginal action on one page signature under a blank layer
    announced_raw: list[dict] = []  # messages the page reported through ANNOUNCE_FUNCTION since the last observation
    all_announcements: list[dict] = []  # every announcement of the run, each with the step it preceded
    stale_streak = 0
    # A pass outcome (or Jev's DONE) gets one settle-and-recheck before it counts: {name, action}
    pending: dict | None = None
    pending_change: tuple[dict, dict, str] | None = None  # (history entry, trace step, signature decided on)
    repeats: dict = {}
    status: str | None = None
    error: str | None = None
    final: dict = {"outcome": None, "seen_at_step": None, "confirmed": False, "assertions": [], "adjudication": None}
    # first_seen_at_step is added when a pass sighting starts its confirmation (the confirming step becomes seen_at_step)
    secret_values = [spec["data"][k] for k in spec["secrets"] if spec["data"].get(k)]
    diagnostics = Diagnostics(secret_values)  # what the browser says went wrong (exceptions, failed requests, 4xx/5xx)
    net = NetWatch() if spec["browser"].get("settle") == "network" else None  # the requests in flight, for the settle
    action_started = time.perf_counter()  # when the last executed action began: the settle waits for what was requested since
    teardown_summary: dict | None = None
    # Replay (replay.py): with `replay` on, a saved path's steps are executed in place of Jev's decisions for as long as
    # each applies to the page in front of it, and a passing run writes the path it took.
    rp_cfg = spec.get("replay") or {}
    rp = Replay(spec, use=rp_cfg.get("use", True)) if rp_cfg.get("enabled") else None
    last_action_end = time.perf_counter()  # when the last executed action (or the setup) had settled: a path step's wait is counted from here
    # One request per form (spec batch_fields): the fields Jev assigned values to in the request that chose a TYPE_TEXT,
    # still to be typed without asking again, and the page as it was then: {"items", "print", "text", "covered", "options"}
    batch: dict | None = None
    batch_account: dict = {"fields_typed": 0, "stopped": []}  # result.batch
    tokens = Tokens(spec)

    def record(entry: dict, step: dict, sig: str) -> None:
        """Append a history entry and remember which observation it was decided on, so the next
        observation can say whether the page changed (`page_changed` on the entry and the step)."""
        nonlocal pending_change
        history.append(entry)
        pending_change = (entry, step, sig)

    def note_page_change(sig: str) -> None:
        nonlocal pending_change, last_page_changed, after_no_effect
        after_no_effect = False
        if pending_change:
            entry, prev_step, before = pending_change
            entry["page_changed"] = prev_step["page_changed"] = sig != before
            last_page_changed = entry["page_changed"] if "reason" not in entry else None
            if last_page_changed is False and (prev_step.get("executed") or {}).get("action") in NO_EFFECT_ACTIONS:
                # the action landed and nothing Jev can see changed: the classic dead control. Flagged on the step
                # (NO-EFFECT in the summary) and the next observation, which shows that unchanged page, gets a picture.
                prev_step["no_effect"] = True
                after_no_effect = True
            pending_change = None

    def shot(page, name: str, holder: dict | None = None) -> str | None:
        """Write steps/<name>; None when screenshots are off or the capture failed (the reason lands in
        holder["screenshot_error"] so a missing picture is explained, not silent)."""
        if mode is False:
            return None
        rel = f"steps/{name}"  # the same in every trace, whatever the operating system's separator
        try:
            page.screenshot(path=os.path.join(out_dir, "steps", name), timeout=SCREENSHOT_TIMEOUT_MS)
            return rel
        except Exception as e:  # noqa: BLE001 - a picture is evidence, never a reason to stop the run
            if holder is not None:
                holder["screenshot_error"] = f"{type(e).__name__}: {str(e)[:120]}"
            return None

    def key_step(step: dict) -> bool:
        """The steps worth a picture in "key" mode: something went wrong or the runner refused to act."""
        return bool(step.get("never_violated") or step.get("low_confidence") or step.get("stale")
                    or step.get("outcome_seen") or step.get("pending_outcome") or step.get("outcome_unconfirmed")
                    or step.get("repeat_count", 0) >= 2 or step.get("after_no_effect") or step.get("outcome_deferred")
                    or step.get("action_deferred"))

    def capture(page, step: dict, terminal: bool = False) -> None:
        """Screenshot policy. Taken after Jev's answer and before execution, so the picture is the page
        Jev decided on: every step with True, only terminal or flagged steps with "key", never with False."""
        if step.get("screenshot") or mode is False:
            return
        if mode is True or terminal or key_step(step):
            step["screenshot"] = shot(page, f"{step['n']:03d}.png", step)

    def finish(page, step: dict, new_status: str, executed: dict) -> None:
        """Every terminal site ends here: set the status, record what was (not) executed, take the terminal
        screenshot according to the policy, append the step. The caller then breaks out of the loop."""
        nonlocal status
        status = new_status
        step["executed"] = executed
        capture(page, step, terminal=True)
        trace["steps"].append(step)

    def ask_reason(step: dict, state: dict) -> None:
        """Lever F1: `blocked_reason` is asked only where it is read, on the terminal step of a `blocked`, `stuck`
        or `low_confidence` ending, as one follow-up request over the state the step was decided on (the final
        look asks it in its own request). Recorded on the step as the per-step answer used to be, with
        `reason_request: true` and its latency added to the step's. Never fatal: the run is ending anyway."""
        if step.get("blocked_reason") is not None:
            return
        questions, offered = build_reason_questions()
        step["reason_request"] = True
        t_r = time.perf_counter()
        try:
            resp = jev.system_one(state, questions)
            step.setdefault("latency_ms", {})["jev"] = step.get("latency_ms", {}).get("jev", 0) + latency_of(resp, t_r)
            step["usage"] = add_usage(step.get("usage"), resp.get("usage"))
            answers = resp["answers"] if isinstance(resp.get("answers"), dict) else {}
            got = read_choice(answers, "blocked_reason", offered["blocked_reason"])
            if got is None:
                note_invalid(step, f"blocked_reason: {validate_choice(answers.get('blocked_reason'), offered['blocked_reason'])}")
            step["blocked_reason"] = got
        except Exception as e:  # noqa: BLE001 - JevError or a malformed body: the ending stands, its typed reason is missing
            step["blocked_reason"] = None
            note_invalid(step, f"blocked_reason: {type(e).__name__}: {str(e)[:200]}")

    def park(step: dict, reason: str, entry: dict | None, sig: str, pause: bool = True,
             wait_ms: int | None = None, before: dict | None = None) -> None:
        """A step the runner refuses to act on (a pending confirmation, a low-confidence decision, a stale
        decision): recorded as a WAIT, pictured per the policy, `entry` (when given) appended to Jev's
        recent_actions, then a real wait like the WAIT operation - `wait_ms` (default settle_ms), ending as soon
        as the page differs from `before` when a fingerprint is given, then the event-based settle - and the
        step is appended. Every runner-inserted WAIT goes through here, so they all wait the same."""
        step["executed"] = {"action": "WAIT", "ok": True, "error": None, "reason": reason}
        capture(page, step)
        if entry is not None:
            record(entry, step, sig)
        t_b = time.perf_counter()
        if pause:
            ms = spec["browser"]["settle_ms"] if wait_ms is None else wait_ms
            step["executed"]["wait_ms"] = ms
            step["executed"]["wait"] = wait_for_change(page, before, ms)
        step["settle"] = settle(page, spec, net=net, since=action_started)
        step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
        trace["steps"].append(step)

    STOP = {"action": "STOP", "ok": True, "error": None}

    def outcome_when(name: str) -> str:
        """The statement the adjudication quotes against: the outcome's `when`, else its checks' statements."""
        o = outcomes[name]
        return o.get("when") or " and ".join(spec["checks"][r] for r in o["requires"])

    def settle_pass(page, step: dict, obs: dict, seen: dict, action: str, jev, prefetched: dict | None = None,
                    assertions: list[dict] | None = None, skip_evidence: str | None = None) -> None:
        """A confirmed pass: run the assertions on this final observation and end passed / assert_failed. With
        `prefetched` (the evidence questions rode in this step's request) the adjudication costs no request; with
        `assertions` (already evaluated on this page by the confirm-by-assertions path) they are not run again; with
        `skip_evidence` (a replayed run decided by its assertions) the evidence line is not asked, and that is why."""
        final["outcome"] = seen
        final["seen_at_step"] = step["n"]
        final.setdefault("first_seen_at_step", step["n"])
        final["confirmed"] = True
        final.setdefault("confirmed_by", "recheck")
        final["assertions"] = check_assertions(spec, page, obs, secret_values, diagnostics) if assertions is None else assertions
        ok = all(a["ok"] for a in final["assertions"])
        step["assertions"] = final["assertions"]
        finish(page, step, "passed" if ok else "assert_failed", {"action": action, "ok": True, "error": None, "confirmed": True})
        if ok and not spec["setup"] and not spec.get("login") and not any("reason" not in h for h in history):
            trace["passed_without_actions"] = True
        if rp is not None and ok:
            # the page a replay of this run should end on
            rp.set_final(obs, int((time.perf_counter() - last_action_end) * 1000), busy=page_busy(obs))
        if skip_evidence:
            final["adjudication"] = {"outcome": seen["name"], "statement": outcome_when(seen["name"]), "line": None, "line_id": None,
                                     "present": None, "confidence": None, "skipped": skip_evidence}
            return
        if ok and final["assertions"] and prefetched is None and spec.get("evidence") == "failures":
            # The assertions held in code: they are the proof, and the spec said not to spend a request on the line.
            final["adjudication"] = {"outcome": seen["name"], "statement": outcome_when(seen["name"]), "line": None, "line_id": None,
                                     "present": None, "confidence": None,
                                     "skipped": "pass confirmed by its assertions; the spec's evidence is \"failures\""}
            return
        final["adjudication"] = adjudicate(page, jev, seen["name"], outcome_when(seen["name"]), secret_values, prefetched,
                                           announced_lines(step["n"]), deep=deep)

    def accepted(seen: list[dict], step: dict) -> list[dict]:
        """Outcomes with `requires_action` do not count before the first executed action (a statement such as
        "nothing changed" is true of the untouched start page too), and an outcome with `after` not before the
        actions it names have been executed ("only after a click on Search"): policy.deferred_outcomes. Deferred
        sightings are recorded on the step (`outcome_deferred`) and the run goes on."""
        deferred = deferred_outcomes(seen, outcomes, history)
        if deferred:
            step["outcome_deferred"] = deferred
        return [s for s in seen if s["name"] not in deferred]

    def end_with_outcome(page, step: dict, seen: dict, jev) -> None:
        """A non-pass outcome is terminal at first confident sighting (fail_fast): the picture is forced."""
        final["outcome"] = seen
        final["seen_at_step"] = final["first_seen_at_step"] = step["n"]
        step["outcome_seen"] = seen["name"]
        finish(page, step, "outcome", dict(STOP))
        final["adjudication"] = adjudicate(page, jev, seen["name"], outcome_when(seen["name"]), secret_values,
                                           extra_lines=announced_lines(step["n"]), deep=deep)

    timing: dict = {}  # where the wall-clock went: launch, navigation, setup, steps, final

    def lap(name: str, since: float) -> float:
        timing[name] = int((time.perf_counter() - since) * 1000)
        return time.perf_counter()

    def look() -> dict:
        """Observe the page with every secret value masked in what Jev and the trace will see. A navigation landing
        during the observation is waited out and the new page observed instead (`trace.observation_retries`)."""
        def bump() -> None:
            trace["observation_retries"] = trace.get("observation_retries", 0) + 1
        return observe_after_navigation(
            page, spec, lambda: mask_secrets(observe(page, obs_cfg["max_elements"], obs_cfg["max_text_chars"],
                                                     frames=obs_cfg.get("frames") or None, shadow_dom=deep,
                                                     file_inputs=bool(spec.get("files"))), secret_values), bump)

    def on_announce(raw) -> None:
        """The page reports a toast / live message (observe.ANNOUNCE_INIT_JS): keep it until the next observation."""
        try:
            entry = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return
        if isinstance(entry, dict) and isinstance(entry.get("text"), str):
            announced_raw.append(entry)

    def take_announcements(n: int, obs: dict) -> list[dict]:
        """The messages announced since the previous observation, masked, with how long before this observation each
        appeared (the page's own clock on both sides); recorded for the run under step n and returned for the step."""
        taken, announced_raw[:] = list(announced_raw), []
        now = obs.get("now")
        out = []
        for a in taken:
            rec = {"text": mask_text(a["text"], secret_values), "kind": a.get("kind") or "toast"}
            if a.get("tone"):
                rec["tone"] = a["tone"]
            rec["ms_before_observation"] = (max(0, int(now - a["t"]))
                                            if isinstance(now, (int, float)) and isinstance(a.get("t"), (int, float)) else None)
            out.append(rec)
        all_announcements.extend({"step": n, **a} for a in out)
        acted = next((h for h in reversed(history) if "reason" not in h), None)
        if out and acted is not None:
            # on the last executed action, whatever runner waits followed it: what the app said in answer to it
            acted.setdefault("announced", []).extend(a["text"] for a in out)
        return out

    def announced_lines(n: int) -> list[str]:
        return announcement_lines(recent_announcements(all_announcements, n))

    def final_page(checks: dict) -> dict:
        """trace.final for a run that ends without a fresh observation: url and title masked like a step's."""
        try:
            url, title = page.url, page.title()
        except Exception:  # noqa: BLE001 - the page is gone
            url, title = None, None
        return {"url": mask_text(url, secret_values), "title": mask_text(title, secret_values), "checks": checks}

    os.makedirs(os.path.join(out_dir, "steps"), exist_ok=True)  # before any tab is opened: nothing to close if it fails
    warm = getattr(jev, "warm_up", None)  # JevClient opens its connection now, while the browser launches; a test double may lack it
    if callable(warm):
        try:
            warm()
        except Exception:  # noqa: BLE001 - the first request opens the connection itself, as before
            pass
    with sync_playwright() as p:
        t_lap = time.perf_counter()
        cdp_url = spec["browser"]["cdp_url"]
        sess_cfg = spec.get("session") or {}
        # reuse a saved login: only for a spec that names its login steps, and never in a browser that is not ours
        sessions_on = bool(sess_cfg.get("reuse")) and bool(spec.get("login")) and not cdp_url
        session, session_info, cache_slot, sess_file = None, None, None, None
        if sessions_on:
            sess_dir = sess_cfg.get("dir") or DEFAULT_SESSION_DIR
            sess_file = session_file(sess_dir, session_key(spec, sess_dir))
        headless = bool(spec["browser"]["headless"])
        viewport = {"width": spec["browser"]["viewport"][0], "height": spec["browser"]["viewport"][1]}
        created_context = True
        # Say which mode this is before anything opens: the question "why can't I see it" (or "why can I") is
        # answered by the run itself, and the trace keeps the answer (trace.browser.headless).
        if cdp_url:
            print(f"browser: attached to {cdp_url} (that browser's own window; --headed/--headless do not apply)", file=sys.stderr)
        elif headless:
            print(f"browser: headless (add --headed, or {HEADED_ENV}=1 in .env, to watch)", file=sys.stderr)
        else:
            print("browser: headed (a window opens; --headless hides it)", file=sys.stderr)
        try:
            if cdp_url:
                # Attach to a browser the user already runs (Chrome started with --remote-debugging-port). Its
                # logged-in profile is the point: SSO-walled apps get tested without scripting the login.
                # storage_state is meaningless here and ignored. We open one tab and close only that tab.
                browser = p.chromium.connect_over_cdp(cdp_url)
                if browser.contexts:
                    context, created_context = browser.contexts[0], False
                else:
                    context = browser.new_context(viewport=viewport)
                context.add_init_script(ANNOUNCE_INIT_JS)  # before the tab exists: it runs in every document the tab loads
                page = context.new_page()
                page.set_viewport_size(viewport)
                trace["browser"] = {"attached": True, "cdp_url": cdp_url,
                                    "storage_state_ignored": bool(spec["browser"]["storage_state"])}
            else:
                device = spec["browser"].get("device")
                # a device's viewport, user agent, pixel ratio and touch replace the spec's viewport (a phone is its screen)
                ctx_kwargs = device_settings(p, device) if device else {"viewport": viewport}
                if sessions_on:
                    # a saved session for this login on this site (session.py): tried now, checked once its page is open
                    session, why_not = load_session(sess_file, sess_cfg.get("max_age_s", DEFAULT_MAX_AGE_S))
                    session_info = {"reused": False, **({"not_reused": why_not} if session is None else {"age_s": session["age_s"]})}
                state = session["state"] if session else spec["browser"]["storage_state"]
                if spec["browser"].get("http_cache"):
                    cache_slot = CacheSlot.acquire(spec["browser"].get("http_cache_dir") or DEFAULT_CACHE_DIR)
                if cache_slot is not None:
                    # The browser on a profile that keeps its HTTP cache between runs and nothing else (strip_profile).
                    strip_profile(cache_slot.path)
                    browser = None
                    context = p.chromium.launch_persistent_context(cache_slot.path, headless=headless, channel=spec["browser"]["channel"], **ctx_kwargs)
                    if state:  # such a context takes no storage_state: cookies and localStorage are put back by hand
                        if isinstance(state, str):
                            with open(state, encoding="utf-8") as f:
                                state = json.load(f)
                        if state.get("cookies"):
                            context.add_cookies(state["cookies"])
                        restore = local_storage_script(state)
                        if restore:
                            context.add_init_script(restore)
                    context.add_init_script(ANNOUNCE_INIT_JS)
                    page = context.pages[0] if context.pages else context.new_page()
                else:
                    browser = p.chromium.launch(headless=headless, channel=spec["browser"]["channel"])
                    if state:
                        ctx_kwargs["storage_state"] = state
                    context = browser.new_context(**ctx_kwargs)
                    context.add_init_script(ANNOUNCE_INIT_JS)
                    page = context.new_page()
                trace["browser"] = {"attached": False, "headless": headless}
                if spec["browser"].get("http_cache"):
                    trace["browser"]["http_cache"] = os.path.basename(cache_slot.path) if cache_slot else "no free slot: ran without"
                if device:
                    trace["browser"]["device"] = device
                    trace["browser"]["viewport"] = ctx_kwargs.get("viewport")
        except Exception as e:  # noqa: BLE001 - nothing to trace yet: this is the environment, not the test
            what = (f"could not attach to the browser at {cdp_url} (is Chrome running with --remote-debugging-port?)"
                    if cdp_url else "could not launch the browser")
            if cache_slot is not None:
                cache_slot.release()
            for d in (os.path.join(out_dir, "steps"), out_dir):  # leave no empty run directory behind
                try:
                    os.rmdir(d)
                except OSError:
                    pass
            if isinstance(e, BrowserUnavailable):  # device_settings said what is wrong already
                raise
            raise BrowserUnavailable(f"{what}: {type(e).__name__}: {str(e).split(chr(10), 1)[0][:300]}") from None
        # Tabs the flow itself opens (target=_blank, window.open) are ours to close: launch mode closes them
        # with the context; in attached mode they would otherwise stay in the user's browser.
        popups: list = []

        def track_popup(popup) -> None:
            popups.append(popup)
            popup.on("popup", track_popup)

        page.on("popup", track_popup)
        page.expose_function(ANNOUNCE_FUNCTION, on_announce)  # the page's announcements land in announced_raw, across navigations
        page.set_default_timeout(spec["browser"]["action_timeout_ms"])
        diagnostics.attach(page)
        if net is not None:
            net.attach(page)
        first_page = page  # `page` moves on to a new tab when browser.follow_new_tabs says so; this one is still ours to close

        def note_diagnostics(step: dict) -> None:
            """What the browser reported since the previous observation (flags JS-ERROR, HTTP-5xx, ... in the summary)."""
            fresh = diagnostics.take(step["n"])
            if fresh:
                step["diagnostics"] = fresh
        t_lap = lap("launch_ms", t_lap)
        try:
            phase = "navigation"
            try:
                nav_timeout = spec["browser"]["navigation_timeout_ms"]
                setup_from = 0
                if session is not None:
                    # The page the login ended on, with the saved cookies and storage; or, when the setup's first step is
                    # a `goto`, that page at once (the post-login page would only be loaded to be left). The session counts
                    # only if the page answers as itself and shows what the login waited for; otherwise it is thrown away
                    # and the run logs in like any other.
                    first = spec["setup"][0] if spec["setup"] and spec["setup"][0].get("action") == "goto" else None
                    opened = first["url"] if first else session["url"]
                    page.goto(opened, wait_until="domcontentloaded", timeout=nav_timeout)
                    settle(page, spec, net=net, since=action_started)
                    stale = page_mismatch(opened, page.url)
                    for st in ([] if stale else spec["login"]):
                        if st["action"] == "wait_for" and st.get("selector"):
                            try:
                                step_locator(page, st).wait_for(state=st.get("state", "visible"),
                                                                timeout=min(int(st.get("timeout_ms", VALIDATE_WAIT_MS)), VALIDATE_WAIT_MS))
                            except Exception:  # noqa: BLE001
                                stale = f"the page of the saved session does not show what the login waited for ({st['selector']})"
                                break
                    if stale:
                        session_info.update({"reused": False, "not_reused": stale, "expired": True})
                        drop_session(sess_file)
                        session = None
                        context.clear_cookies()
                        try:
                            page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }")
                        except Exception:  # noqa: BLE001
                            pass
                        # What the application said to the expired session (an alert "log in first", a 404 for the page)
                        # was said to the probe. Live: saucedemo's ten-minute cookie had run out, its "You can only access
                        # '/inventory.html' when you are logged in" reached Jev as an announcement on the first step of the
                        # run that had just logged in, and Jev ended the run blocked on an application error.
                        announced_raw.clear()
                        diagnostics.reset()
                    else:
                        session_info["reused"] = True
                        if first:
                            setup_from = 1
                            trace["setup"].append({"n": 0, "action": "goto", "selector": None, "ok": True, "error": None, "url": first["url"],
                                                   "by": "session"})  # opened while the saved session was checked
                if session is None:
                    page.goto(spec["start_url"], wait_until="domcontentloaded", timeout=nav_timeout)
                    settle(page, spec, net=net, since=action_started)
                t_lap = lap("navigation_ms", t_lap)
                phase = "setup"
                if spec.get("login"):
                    if session is None:
                        run_steps(page, spec, spec["login"], trace["login"], "login", net)
                        if sessions_on:
                            try:
                                save_session(sess_file, context.storage_state(), page.url)
                                session_info["saved"] = True
                            except Exception as e:  # noqa: BLE001 - the run goes on logged in; the next one logs in again
                                session_info["save_error"] = f"{type(e).__name__}: {str(e)[:120]}"
                    t_lap = lap("login_ms", t_lap)
                run_setup(page, spec, trace["setup"], net, setup_from)  # records into trace["setup"] as it goes, so a failed step is kept
                t_lap = lap("setup_ms", t_lap)
                last_action_end = action_started = time.perf_counter()
            except Exception:
                # Nothing was observed, so the flow was not exercised: a slow or unreachable host (navigation), a setup
                # selector that did not match (setup). Reported apart from the flow's outcomes: result.reason.phase,
                # exit 2, and run_suite lists it as an environment/setup failure instead of a flow outcome.
                trace["failed_before_observation"] = phase
                raise

            def read_attrs(indices: list[int]) -> dict:
                """The stable attributes (test ids, id, name) of observed elements of the main frame, by index."""
                try:
                    return page.evaluate(ATTRS_JS, {"idx": indices, "deep": deep, "names": list(STABLE_ATTRS)}) if indices else {}
                except Exception:  # noqa: BLE001 - the page is navigating: nothing to tell the candidates apart by
                    return {}

            def replay_wait(obs: dict, budget_ms: int, spent_ms: int) -> dict:
                """Between two looks for a saved step's page: wait for the page to change (at most POLL_MS and what is
                left of the step's wait), let a change settle, observe again."""
                waited = wait_for_change(page, obs.get("fingerprint"), max(min(POLL_MS, budget_ms - spent_ms), 1))
                if waited["ended"] != "timeout":
                    settle(page, spec, net=net, since=action_started)
                return look()

            def replay_look(obs: dict) -> tuple[dict, dict | None, str | None]:
                """The next saved step against the page: (observation, decision, None) once it applies, looking again
                while the page is on its way and the step's wait is not spent, else (observation, None, why not)."""
                saved = rp.next_step()
                budget_ms = rp.wait_budget(saved.get("wait_ms"))
                t0 = time.perf_counter()
                waited_for = None
                while True:
                    decision, why = None, None
                    if page_busy(obs) and not saved.get("busy"):
                        why = "the page is still loading (controls under a blank layer, or none yet)"
                    else:
                        decision, why = rp.decide(saved, obs, read_attrs)
                    spent = int((time.perf_counter() - t0) * 1000)
                    if decision is not None or spent >= budget_ms:
                        rp.waited_ms += spent
                        if decision is not None:
                            decision.update({"saved": saved, "waited_ms": spent, "waited_for": waited_for})
                        return obs, decision, why
                    waited_for = why  # what the page was missing on the last look before it fitted
                    obs = replay_wait(obs, budget_ms, spent)

            def replay_final(obs: dict) -> tuple[dict, list[dict] | None, str | None]:
                """After the last saved step: wait, as long as the recorded run did and a little more, for the ending to be
                there to decide. With assertions that is the moment they all hold (what a pass needs anyway, and exact);
                without, the page the recorded run ended on, no longer loading. Returns (observation, the assertions as
                last evaluated or None, why this is not the recorded ending or None)."""
                saved = rp.path.get("final") or {}
                budget_ms = rp.wait_budget(saved.get("wait_ms"))
                t0 = time.perf_counter()
                while True:
                    checked = None
                    why = match_final(saved, page_print(obs, rp.tokens))
                    if why is None and page_busy(obs) and not saved.get("busy"):
                        why = "the page is still loading (controls under a blank layer, or none yet)"
                    ready = why is None
                    if spec["assert"]:
                        checked = check_assertions(spec, page, obs, secret_values, diagnostics)
                        ready = all(a["ok"] for a in checked)
                        why = why or (None if ready else "the assertions do not hold on the page yet")
                    spent = int((time.perf_counter() - t0) * 1000)
                    if ready or spent >= budget_ms:
                        rp.waited_ms += spent
                        return obs, checked, why
                    obs = replay_wait(obs, budget_ms, spent)

            def options_shown(obs: dict) -> int:
                return sum(1 for e in obs["elements"] if e["role"] == "option")

            def batch_next(obs: dict, announced: list[dict]) -> tuple[dict | None, dict | None, str | None]:
                """The next field of the batch on this observation, as (item, element, None), or (None, None, why the
                batch ends here). It ends the moment the page has reacted to what was typed: a message announced, a field
                or button that appeared or went, any change of the visible text (a validation line, a counter), a layer,
                a list of options; or when the field is not found again as itself, empty."""
                if announced:
                    return None, None, f"the page announced a message ({announced[0]['text'][:60]!r})"
                why = match_page(batch["print"], page_print(obs, tokens))
                if why:
                    return None, None, why
                if obs.get("covered", 0) != batch["covered"] or obs.get("loading_options"):
                    return None, None, "a layer or a loading list appeared over the form"
                if options_shown(obs) != batch["options"]:
                    return None, None, "a list of suggestions opened"
                if obs["visible_text"] != batch["text"]:
                    return None, None, "the page's text changed after a field was typed (a validation message, a hint, a counter)"
                item = batch["items"][0]
                el, _, why = find_target(item["target"], obs["elements"], "TYPE_TEXT", spec, tokens, read_attrs)
                if el is None:
                    return None, None, why
                if el.get("value"):
                    return None, None, f"the field {item['label']} already has a value"
                return item, el, None

            def act(n: int, step: dict, obs: dict, sig: str, operation: str, target: dict | None, value_key: str | None,
                    state_fn, saved: dict | None = None) -> bool:
                """Execute a decided action and record it: repeat detection, the WAIT backoff, the picture, the action, the
                settle, a new tab, the history. Shared by Jev's decisions and a saved path's (`saved`: the path step being
                replayed). `state_fn()` builds Jev's state for the follow-up question of a `stuck` ending. Returns True
                when the run ends here."""
                nonlocal page, wait_streak, last_wait_sig, last_operation, last_action_end, action_started
                # Repeat detection: the same action on an unchanged page max_repeat times is `stuck`. A WAIT is
                # not an action on the page: Jev choosing it again on a page that still says "Loading..." is the
                # right answer for as long as the page keeps loading (measured live: a 5 s loader ended `stuck`
                # after 1.5 s with stuck_reason still_loading), so only the budget bounds a streak of WAITs.
                if operation != "WAIT":
                    key = (sig, operation, target["choice"] if target and not target.get("missing") else None, value_key)
                    repeats[key] = repeats.get(key, 0) + 1
                    step["repeat_count"] = repeats[key]
                    if repeats[key] >= th["max_repeat"]:
                        ask_reason(step, state_fn())
                        finish(page, step, "stuck", dict(STOP))
                        return True

                # Lever F4: a WAIT chosen again on a page that has not changed since the last WAIT pauses twice as
                # long as the last one, settle_ms x 1, 2, 4 and then 4 (measured on a 5 s loader: every WAIT is a
                # full request, six of them at settle_ms cost ten requests a run). The first WAIT on a page, and any
                # WAIT after the page changed, pause settle_ms as before; a non-WAIT action resets the streak.
                wait_ms = None
                if operation == "WAIT":
                    wait_streak = wait_streak + 1 if sig == last_wait_sig else 0
                    last_wait_sig = sig
                    wait_ms = spec["browser"]["settle_ms"] * min(2 ** wait_streak, WAIT_BACKOFF_MAX)
                    step["wait_streak"] = wait_streak
                else:
                    wait_streak, last_wait_sig = 0, None

                # The page Jev decided on, before anything changes it. The last allowed step is terminal
                # for the budget (the for-else below), so it gets its picture like every terminal step.
                capture(page, step, terminal=(n == budget["max_steps"]))
                t_b = time.perf_counter()
                target_el = next((e for e in obs["elements"] if e["idx"] == (target or {}).get("element")), {})
                tabs_before = len(popups)
                path_attrs, path_wait = None, int((t_b - last_action_end) * 1000)
                if operation != "WAIT":
                    action_started = t_b
                if rp is not None and saved is None and target_el and not target_el.get("frame"):
                    # recorded now, before the action can remove the element: what identifies it across renders
                    path_attrs = read_attrs([target_el["idx"]]).get(str(target_el["idx"]))
                executed = execute(page, spec, operation, target, value_key, wait_ms, obs.get("fingerprint"), target_el.get("frame"))
                if rp is not None and operation in REPLAYABLE:
                    if executed["ok"]:
                        option_text = next((o["text"] for o in target_el.get("options") or [] if o["i"] == (target or {}).get("option")), None)
                        rp.record(operation, obs, target_el or None, path_attrs, value_key, option_text if operation == "SELECT" else None,
                                  path_wait, busy=page_busy(obs), replayed_from=saved, read_attrs=read_attrs)
                    elif saved is not None:
                        step["replay_handback"] = f"the replayed {operation} failed: {executed.get('error')}"
                        rp.hand_back(n, step["replay_handback"])
                if not executed["ok"]:
                    step["screenshot_after_failure"] = shot(page, f"{n:03d}-failed.png", step)
                step["settle"] = settle(page, spec, after=(operation, None if target_el.get("datalist") else target_el.get("role")),
                                        net=net, since=action_started)
                if len(popups) > tabs_before:
                    # The action opened a new tab (target=_blank, window.open; the popup event arrives during the settle
                    # above, not with the click). A person's eyes go with it; the run's do when the spec says so
                    # (browser.follow_new_tabs), and otherwise the step says a tab opened.
                    newest = popups[-1]
                    step["new_tab"] = {"followed": False}
                    try:
                        step["new_tab"]["url"] = mask_text(newest.url, secret_values)
                        if spec["browser"]["follow_new_tabs"] and not newest.is_closed():
                            try:
                                newest.wait_for_load_state("domcontentloaded", timeout=spec["browser"]["navigation_timeout_ms"])
                            except Exception:  # noqa: BLE001 - settle() below waits for the document either way
                                pass
                            try:
                                newest.expose_function(ANNOUNCE_FUNCTION, on_announce)
                            except Exception:  # noqa: BLE001 - announcements from this tab are lost; the page text is not
                                pass
                            newest.set_default_timeout(spec["browser"]["action_timeout_ms"])
                            diagnostics.attach(newest)
                            if net is not None:
                                net.attach(newest)
                            page = newest
                            step["new_tab"] = {"followed": True, "url": mask_text(page.url, secret_values)}
                            step["settle"] = settle(page, spec, net=net, since=action_started)  # the new tab's document, before it is observed
                    except Exception as e:  # noqa: BLE001 - the tab closed itself again: the run stays where it was
                        step["new_tab"]["error"] = f"{type(e).__name__}: {str(e)[:120]}"
                step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                step["executed"] = executed
                record(history_entry(n, operation, target, value_key, executed), step, sig)
                last_operation = operation if executed["ok"] else None
                if operation != "WAIT":
                    last_action_end = time.perf_counter()
                trace["steps"].append(step)
                return False

            for n in range(1, budget["max_steps"] + 1):
                if time.perf_counter() - t_start > budget["max_seconds"]:
                    status = "budget_exhausted"
                    break
                obs = look()
                replay_decision, replay_why, replay_checked, verify_look = None, None, None, False
                if rp is not None and rp.active:
                    # the next saved step, if it applies to this page (given the time the recorded run took to get here)
                    obs, replay_decision, replay_why = replay_look(obs)
                    if replay_decision is None:
                        rp.hand_back(n, replay_why)  # Jev decides this step, on this observation, and every step after it
                elif rp is not None and rp.at_end:
                    rp.verify_asked = True
                    if spec["auto_done"]:
                        # every saved step was executed: the ending is still to be decided, on the page it left
                        obs, replay_checked, replay_why = replay_final(obs)
                        verify_look = True
                    else:
                        rp.hand_back(n, "the spec ends on Jev's DONE (auto_done: false)")
                sig = signature(obs)
                announced = take_announcements(n, obs)  # what the page said since the last observation (toasts, live messages)
                note_page_change(sig)  # did the previous action change what Jev sees?
                step: dict = {
                    "n": n,
                    "at_ms": int((time.perf_counter() - t_start) * 1000),  # when this page was observed, from the start of the run
                    "url": obs["url"],
                    "title": obs["title"],
                    "signature": sig,
                    "screenshot": None,  # taken after Jev's answer, per the screenshot policy (capture)
                    "elements": obs["elements"],
                    "truncated_elements": obs["truncated"],
                    "visible_text": obs["visible_text"][:600],
                }
                if obs.get("covered"):
                    step["covered_controls"] = obs["covered"]  # controls on screen but under another layer: not offered
                    step["layer_controls"] = obs.get("layer_controls", 0)  # the layer's own controls among the offered: 0 is a blank layer
                if obs.get("loading_options"):
                    step["loading_options"] = obs["loading_options"]  # autocomplete rows that only say the suggestions are loading: not offered
                if announced:
                    step["announcements"] = announced  # flag ANNOUNCED; in Jev's state for this and the next two steps
                if obs.get("frames"):
                    step["frames"] = obs["frames"]  # what each listed <iframe> contributed to the table, or why nothing
                for hint in ("iframes", "shadow_hosts"):
                    if obs.get(hint):
                        step[hint] = obs[hint]  # controls may sit where the observer does not look: summarize_trace's hint
                note_diagnostics(step)
                if after_no_effect:
                    step["after_no_effect"] = True  # this is the page the previous action failed to change
                recent_ann = recent_announcements(all_announcements, n)
                if replay_decision is not None:
                    # A saved step decides this one: no request. From here on it is an ordinary executed action.
                    operation, target, value_key = replay_decision["operation"], replay_decision["target"], replay_decision["value_key"]
                    step.update({"replayed": True, "replay_waited_ms": replay_decision["waited_ms"], "offered_operations": [],
                                 "latency_ms": {"jev": 0}, "usage": None, "checks": {}, "operation": {"choice": operation, "replayed": True},
                                 "target": target, "low_confidence": False})
                    if operation == "TYPE_TEXT":
                        step["type_value"] = {"choice": value_key, "replayed": True}
                    if operation == "UPLOAD_FILE":
                        step["upload_file"] = {"choice": value_key, "replayed": True}
                    if replay_decision.get("waited_for"):
                        step["replay_waited_for"] = replay_decision["waited_for"]  # why the saved step did not apply at first
                    stale_streak, low_streak, last_low_sig = 0, 0, None
                    if act(n, step, obs, sig, operation, target, value_key,
                           lambda: build_state(spec, obs, n, history, recent_ann), replay_decision["saved"]):
                        break
                    continue
                if batch is not None:
                    # A field Jev assigned its value to in the request that typed the previous one: typed now, without a
                    # request, unless the page has reacted since (then Jev decides, on this observation).
                    item, el, why = batch_next(obs, announced)
                    if item is None:
                        step["batch_stopped"] = why
                        batch_account["stopped"].append({"step": n, "reason": why, "fields_left": len(batch["items"])})
                        batch = None
                    else:
                        batch["items"].pop(0)
                        conf = round(item["confidence"], 3)
                        operation, value_key = "TYPE_TEXT", item["value_key"]
                        target = {"question": "type_target", "choice": str(el["idx"]), "element": el["idx"], "confidence": conf,
                                  "label": f'[{el["idx"]}] {element_label(el)}', "batched": True}
                        step.update({"batched": True, "offered_operations": [], "latency_ms": {"jev": 0}, "usage": None, "checks": {},
                                     "operation": {"choice": operation, "confidence": conf, "batched": True}, "target": target,
                                     "type_value": {"choice": value_key, "confidence": conf, "batched": True},
                                     "low_confidence": False, "decision_confidence": conf})
                        stale_streak, low_streak, last_low_sig = 0, 0, None
                        batch_account["fields_typed"] += 1
                        if not batch["items"]:
                            batch = None
                        if act(n, step, obs, sig, operation, target, value_key, lambda: build_state(spec, obs, n, history, recent_ann)):
                            break
                        if not step["executed"]["ok"]:
                            batch = None  # the typing failed: whatever is left is Jev's to decide
                        continue
                if replay_why and not verify_look:
                    step["replay_handback"] = replay_why  # why the saved path stopped here; Jev decides from this step on
                if verify_look:
                    step["replay_verify"] = True  # the look that decides the ending of a replayed run
                    if replay_why:
                        step["replay_final_mismatch"] = replay_why
                    expected = rp.path["outcome"]
                    if (rp.verify == "assert" and replay_why is None and replay_checked and all(a["ok"] for a in replay_checked)
                            and (outcomes.get(expected) or {}).get("verdict") == "pass"):
                        # replay.verify "assert": the page the recorded run ended on, and every assertion holds on it. That
                        # is the pass; Jev is not asked, and the result says so (confirmed_by, replay.verified_by, evidence).
                        rp.verified_by = "assertions"
                        step.update({"offered_operations": [], "latency_ms": {"jev": 0}, "usage": None, "checks": {}, "operation": None})
                        final["confirmed_by"] = "assertions"
                        settle_pass(page, step, obs, {"name": expected, "verdict": "pass", "probability": None, "confidence": None},
                                    "AUTO_DONE", jev, assertions=replay_checked,
                                    skip_evidence="replayed run decided by its assertions (replay.verify: \"assert\"); Jev was not asked")
                        break
                state = build_state(spec, obs, n, history, recent_ann)
                questions, meta = build_questions(spec, obs, last_operation, outcomes, ask_stuck=last_page_changed is False,
                                                  announcements=recent_ann)
                offered = meta["offered"]
                step["offered_operations"] = meta["operations"]
                merged_adj = None
                adj_for = pending.get("name") if pending else None
                if verify_look:
                    # One request decides the ending of a replayed run: which declared outcome the page shows, the spec's
                    # checks and, for the outcome the recorded run ended in, the evidence line. No operation is asked:
                    # if nothing declared is in sight, the next step is an ordinary one and Jev has the run.
                    questions = {k: v for k, v in questions.items() if k in spec["checks"] or k == "outcome"}
                    step["offered_operations"] = []
                    adj_for = expected if expected in outcomes else None
                if adj_for and not (spec.get("evidence") == "failures" and spec["assert"]):
                    # (with evidence "failures" and assertions the line is asked only if the pass then fails them)
                    # The confirmation of a pass sighting: ask the evidence questions in the same request (speculative
                    # fan-out), so a confirmed pass needs no adjudication round trip. The Choices point at state.lines.
                    merged_adj = adjudication_request(page, adj_for, outcome_when(adj_for), secret_values,
                                                      announced_lines(n), deep)
                    if merged_adj:
                        state["lines"] = merged_adj["state"]["lines"]
                        questions.update(merged_adj["questions"])
                        step["adjudication_merged"] = True
                try:
                    t_jev = time.perf_counter()
                    resp = jev.system_one(state, questions)
                    step["latency_ms"] = {"jev": latency_of(resp, t_jev)}
                    step["usage"] = resp.get("usage")  # this request's tokens (a retry or the reason follow-up adds to it)
                    answers = resp["answers"]
                    op_problem = None if verify_look else validate_choice(answers.get("operation"), offered["operation"])
                    if op_problem:
                        # A malformed or missing operation answer is not a decision. Jev calls are
                        # read-only, so the same state and questions are sent once more before the
                        # run gives up; both round trips count toward this step's Jev latency.
                        note_invalid(step, f"operation: {op_problem}")
                        step["retried"] = True
                        t_jev = time.perf_counter()
                        resp = jev.system_one(state, questions)
                        step["latency_ms"]["jev"] += latency_of(resp, t_jev)
                        step["usage"] = add_usage(step.get("usage"), resp.get("usage"))
                        answers = resp["answers"]
                        op_problem = validate_choice(answers.get("operation"), offered["operation"])
                        if op_problem:
                            note_invalid(step, f"operation after retry: {op_problem}")
                except JevError as e:
                    error = step["error"] = str(e)
                    finish(page, step, "error", dict(STOP))
                    break
                checks = read_checks(answers, spec)
                step["checks"] = checks
                op = None if verify_look else read_choice(answers, "operation", offered["operation"])  # None iff op_problem
                step["operation"] = op

                # The results contract: which declared outcome does this page show?
                outcome_answer = None
                if "outcome" in offered:
                    outcome_answer = read_outcome(answers, offered["outcome"])
                    if outcome_answer is None:
                        note_invalid(step, f"outcome: {validate_choice(answers.get('outcome'), offered['outcome'])}")
                    step["outcome"] = outcome_answer
                for reason_q in ("blocked_reason", "stuck_reason"):
                    if reason_q in offered:
                        got = read_choice(answers, reason_q, offered[reason_q])
                        if got is None:
                            note_invalid(step, f"{reason_q}: {validate_choice(answers.get(reason_q), offered[reason_q])}")
                        step[reason_q] = got
                seen = accepted(seen_outcomes(outcomes, checks, outcome_answer, th["outcome_true"]), step)
                non_pass = [s for s in seen if s["verdict"] != "pass"]
                passes = [s for s in seen if s["verdict"] == "pass"]
                if verify_look and seen:
                    rp.verified_by = "jev"
                bad = [n_ for n_ in spec["never"] if checks.get(n_, 0.0) >= th["never_true"]]
                if bad:
                    step["never_violated"] = bad  # kept for readers of old traces; the outcome below is the verdict

                if non_pass:
                    if spec["fail_fast"]:
                        end_with_outcome(page, step, non_pass[0], jev)
                        break
                    step["outcome_seen"] = non_pass[0]["name"]  # recorded; the run goes on

                if pending:
                    # A pass was in sight last step (or Jev said DONE); the page has now had a full settle
                    # (reloads, toasts, redirects). This observation is the verdict.
                    was = pending
                    pending = None
                    nav_ms = spec["browser"]["navigation_timeout_ms"]
                    waited = was.get("waited_ms", 0)

                    def recheck_wait(rechecks: int) -> int:
                        # settle_ms x 2, 4, 4, ... (WAIT_BACKOFF_MAX); past the count bound, on a busy page, never beyond
                        # what is left of navigation_timeout_ms
                        ms = spec["browser"]["settle_ms"] * min(2 ** rechecks, WAIT_BACKOFF_MAX)
                        return ms if rechecks <= recheck_limit(True) else max(min(ms, nav_ms - waited), spec["browser"]["settle_ms"])

                    if passes:
                        checked = check_assertions(spec, page, obs, secret_values, diagnostics) if spec["assert"] else []
                        if assertions_can_wait(checked, page_busy(obs), sig != was["sig"], was["rechecks"], waited, nav_ms):
                            # The pass is in sight (a toast announced the save) but the page is still busy (controls under
                            # the saving overlay, the next page's empty shell) or changed during the pause, and the assertions
                            # do not hold yet (the URL still the form's, the name not rendered): not the settled page. Look
                            # again, as for a page that shows no pass yet.
                            wait_ms = recheck_wait(was["rechecks"] + 1)
                            pending = {**was, "sig": sig, "rechecks": was["rechecks"] + 1, "waited_ms": waited + wait_ms}
                            step["pending_outcome"] = passes[0]["name"]
                            step["recheck_again"] = pending["rechecks"]
                            step["recheck_waited_ms"] = pending["waited_ms"]  # the confirmation's waits so far, against navigation_timeout_ms on a busy page
                            step["assertions_pending"] = [a for a in checked if not a["ok"]]
                            step["assertions_checked"] = checked  # the whole evaluation: result.reason.assertions_at_last_look if the run ends unverified
                            final.setdefault("first_seen_at_step", n)
                            park(step, "pass in sight but the page is still busy and the assertions do not hold yet; looking again",
                                 wait_entry(n, was["action"], "the page was still busy while the result was being checked; checking again"), sig,
                                 wait_ms=wait_ms, before=obs.get("fingerprint"))
                            continue
                        pre = {**merged_adj, "answers": answers} if merged_adj and merged_adj["name"] == passes[0]["name"] else None
                        settle_pass(page, step, obs, passes[0], was["action"], jev, pre, assertions=checked or None)
                        break
                    if (sig != was["sig"] or page_busy(obs)) and can_recheck(page_busy(obs), was["rechecks"], waited, nav_ms):
                        # The page changed during the pause, or is still busy (a blank layer over controls, an empty shell),
                        # and shows no pass yet: this is not the settled page, so the look has not ruled out timing. Look
                        # again, pausing settle_ms x 2, x 4 (ending the moment the page changes again), until two consecutive
                        # looks agree on a settled page or the bound is reached: by count, and on a busy page for as long as
                        # navigation_timeout_ms. Live: a slow Save navigated during the pause and the confirmation saw the
                        # next page's loading overlay; a DONE on a form under its saving spinner; a record page rendering
                        # 30 s after Save, one look past the count of four.
                        wait_ms = recheck_wait(was["rechecks"] + 1)
                        pending = {**was, "sig": sig, "rechecks": was["rechecks"] + 1, "waited_ms": waited + wait_ms}
                        step["pending_outcome"] = was["name"]
                        step["recheck_again"] = pending["rechecks"]
                        step["recheck_waited_ms"] = pending["waited_ms"]
                        park(step, "page still changing during the confirmation; looking again",
                             wait_entry(n, was["action"], "the page changed while the result was being checked; checking again"), sig,
                             wait_ms=wait_ms, before=obs.get("fingerprint"))
                        continue
                    if was["action"] == "DONE":
                        finish(page, step, "done_unverified", {"action": "DONE", "ok": True, "error": None, "confirmed": True})
                        break
                    step["outcome_unconfirmed"] = was["name"]  # a transient sighting: carry on with this step's answers
                    final.pop("first_seen_at_step", None)  # it was not the first sighting of the pass

                def confirm_later(name: str | None, action: str, reason: str, entry_op: str) -> None:
                    nonlocal pending
                    pending = {"name": name, "action": action, "sig": sig, "rechecks": 0, "waited_ms": 0}  # sig: the page the sighting / DONE was made on
                    step["pending_outcome"] = name
                    if name:
                        final["first_seen_at_step"] = n  # the sighting; seen_at_step will be the confirming step
                    park(step, reason, wait_entry(n, entry_op, "checking the result before finishing"), sig)

                if passes and spec["auto_done"]:
                    if spec["confirm"] == "assert" and spec["assert"]:
                        # Confirm in code when the spec lets us: every assertion already holds on the page the pass was
                        # seen on, so the settle-and-recheck (a 400 ms pause, one observation, one request) is not needed
                        # to know the page really shows the ending. The evidence line is asked in its own request.
                        checked = check_assertions(spec, page, obs, secret_values, diagnostics)
                        if all(a["ok"] for a in checked):
                            final["confirmed_by"] = "assertions"
                            # (a replayed run's deciding look asked the evidence line in the same request: `pre`)
                            pre = {**merged_adj, "answers": answers} if merged_adj and merged_adj["name"] == passes[0]["name"] else None
                            settle_pass(page, step, obs, passes[0], "AUTO_DONE", jev, pre, assertions=checked)
                            break
                        step["assertions_pending"] = [a for a in checked if not a["ok"]]  # not yet: the recheck decides
                        step["assertions_checked"] = checked
                    confirm_later(passes[0]["name"], "AUTO_DONE", f"confirming outcome {passes[0]['name']}", "WAIT")
                    continue

                if verify_look:
                    # After the last saved step the page shows no declared outcome (or one that only counts later): the
                    # replay is over without an ending, and the next step is an ordinary one, on this page.
                    why = "after the last saved step the page shows no declared outcome" + (f" ({replay_why})" if replay_why else "")
                    step["replay_handback"] = why
                    rp.hand_back(n, why)
                    park(step, "the saved path ended with no declared outcome in sight; Jev decides from here", None, sig, pause=False)
                    continue
                if op is None:
                    error = step["error"] = f"invalid operation answer: {op_problem}"
                    finish(page, step, "error", dict(STOP))
                    break
                operation = op["choice"]
                target = resolve_target(operation, answers, obs, meta)
                step["target"] = target
                if target and target.get("invalid"):
                    # Not retried: the missing-target path below fails the action safely.
                    note_invalid(step, f"{target['question']}: {target['invalid']}")
                value_key = None
                tv = None
                if operation == "TYPE_TEXT":
                    tv = read_choice(answers, "type_value", offered.get("type_value", []))
                    if tv is None:
                        note_invalid(step, "type_value: " + validate_choice(answers.get("type_value"), offered.get("type_value", [])))
                    step["type_value"] = tv
                    value_key = tv["choice"] if tv else None
                uf = None
                if operation == "UPLOAD_FILE":
                    uf = read_choice(answers, "upload_file", offered.get("upload_file", []))
                    if uf is None:
                        note_invalid(step, "upload_file: " + validate_choice(answers.get("upload_file"), offered.get("upload_file", [])))
                    step["upload_file"] = uf
                    value_key = uf["choice"] if uf else None

                # Confidence gate. Jev reporting low confidence on the operation, the target, or (for
                # TYPE_TEXT) which value to type is a typed "I don't know", and the runner never acts on
                # one: it would type wrong values into fields or stop mid-reload. A low decision is
                # treated as a WAIT (the page may still be settling) and counts toward
                # max_low_confidence_steps; the same undecided answer on an unchanged page then ends the
                # run as `low_confidence`, which is Claude's cue to fix the spec.
                confs = [op["confidence"]]
                if target and not target.get("missing"):
                    confs.append(target["confidence"])
                if operation == "TYPE_TEXT" and tv:
                    confs.append(tv["confidence"])
                if operation == "UPLOAD_FILE" and uf:
                    confs.append(uf["confidence"])
                low = min(confs) < th["min_confidence"]
                step["low_confidence"] = low
                step["decision_confidence"] = round(min(confs), 3)

                if low:
                    # Undecided steps are counted on one page: a page that changes under them (a loader finishing,
                    # a form appearing) restarts the count, and each undecided step waits like a chosen WAIT,
                    # settle_ms x 1, 2, 4 (WAIT_BACKOFF_MAX), ending the moment the page changes. Measured live:
                    # three flat settle_ms pauses (~2 s in all) ended a run low_confidence while a 5 s loader was
                    # still visibly running and Jev split WAIT against DONE at 0.47 / 0.46.
                    low_streak = low_streak + 1 if sig == last_low_sig else 1
                    last_low_sig = sig
                    stale_streak = 0  # a refused decision is not a stale one: `max_stale` counts consecutive stale steps
                    step["low_streak"] = low_streak
                    if not page_loading(obs):
                        # asked only now, for an undecided decision on a page with no blank layer: is something else
                        # saying "loading"? (one small script; an ordinary step never pays for it)
                        found = loading_indicators(page, obs["fingerprint"].get("frames"))
                        if found:
                            step["loading_indicators"] = found
                    if low_streak >= low_confidence_limit(th, page_loading(obs) or loading_indicated(step)):
                        if not moved_since(page, obs.get("fingerprint")):
                            ask_reason(step, state)
                            finish(page, step, "low_confidence", dict(STOP))
                            break
                        # the page moved while Jev was deciding (a loader that ended after the observation, before the
                        # indicator check): the looks were about a page that is gone, so the count starts again
                        step["moved_while_deciding"] = True
                        low_streak, last_low_sig = 0, None
                    park(step, f"low confidence; {operation} not executed",
                         wait_entry(n, "WAIT", "undecided between the offered options; nothing was executed"), sig,
                         wait_ms=spec["browser"]["settle_ms"] * min(2 ** (low_streak - 1), WAIT_BACKOFF_MAX),
                         before=obs.get("fingerprint"))
                    continue
                low_streak, last_low_sig = 0, None

                if defer_action(operation, obs.get("covered", 0), min(confs), th["covered_action_confidence"], obs.get("layer_controls", 0),
                                obs.get("loading_options", 0)):
                    # A marginal action while controls sit under a blank layer: the page is busy (a form still loading,
                    # a request in flight before a dialog opens) and the free control Jev picked is probably not the one
                    # (live: the first name went into the sidebar's menu filter in every PIM run; a Leave flow clicked
                    # the next tab at 0.71-0.74 before the confirmation dialog had opened). Wait, settle_ms x 1, 2, 4, 4,
                    # 4 (WAIT_BACKOFF_MAX), each wait ending the moment the page changes, deferral_limit times on one
                    # page; the next such decision on the same page is then executed, whatever it is (a layer that stays
                    # that long is the page now). A layer with controls of its own (a dialog, an open list) defers
                    # nothing: defer_action reads layer_controls. Measured: the once-per-page deferral (2.5 s) lost to a
                    # loader of 5-17 s in every slow-hour run, and the second decision was the same wrong one.
                    defer_streak = defer_streak + 1 if sig == last_defer_sig else 1
                    last_defer_sig = sig
                    if defer_streak <= deferral_limit(th):
                        step["action_deferred"] = {"operation": operation, "covered": obs.get("covered", 0), "loading": obs.get("loading_options", 0)}
                        step["deferrals"] = defer_streak
                        busy_why = (f"{obs['covered']} controls are under a blank layer" if obs.get("covered")
                                    else f"{obs.get('loading_options')} autocomplete row(s) still say the suggestions are loading")
                        park(step, f"{operation} deferred: {busy_why}; waiting for the page ({defer_streak}/{deferral_limit(th)})",
                             wait_entry(n, "WAIT", f"{operation} deferred: {obs['covered']} controls were under another layer (the page "
                                                   f"still loading or a request in flight?); the page was given time to finish"), sig,
                             wait_ms=spec["browser"]["settle_ms"] * min(2 ** (defer_streak - 1), WAIT_BACKOFF_MAX), before=obs.get("fingerprint"))
                        continue
                    step["deferrals_exhausted"] = deferral_limit(th)  # executed on a page still under its layer, after the last deferral

                # Freshness guard. Jev decided on the observation; the page may have moved on while it
                # was deciding (a toast, a re-render, a redirect). Re-read identity and meaning of what the
                # decision depends on - the target node for CLICK/TYPE_TEXT/SELECT, the whole page for
                # DONE/BLOCKED/PRESS_ENTER - and if it differs, execute nothing and observe again. A
                # mutation is never retried; max_stale consecutive stale decisions end the run.
                guard = operation not in GUARD_SKIPPED and not (
                    operation in TARGET_OPERATIONS and (not target or target.get("missing"))
                )
                if guard:
                    try:
                        reason = compare_fingerprint(obs["fingerprint"],
                                                     fingerprint(page, obs["fingerprint"].get("frames"), obs["fingerprint"].get("deep")),
                                                     operation, (target or {}).get("element"))
                    except Exception:  # noqa: BLE001 - the document navigated under us
                        reason = "document navigated"
                    if reason:
                        stale_streak += 1
                        step["stale"] = reason
                        if stale_streak >= th["max_stale"]:
                            finish(page, step, "unstable_page", dict(STOP))
                            break
                        # not in recent_actions: nothing was decided on this page; no extra pause either, the
                        # page is already moving and the event-based settle is what waits for it to stop
                        park(step, f"page changed during the decision: {reason}", None, sig, pause=False)
                        continue
                stale_streak = 0

                if operation == "DONE":
                    if n >= budget["max_steps"] and not passes:
                        finish(page, step, "done_unverified", {"action": "DONE", "ok": True, "error": None})
                        break
                    # Jev says the goal is reached. Whether or not a pass outcome is already in sight, give the
                    # page one full settle and look again before calling it (a reload or redirect is often
                    # still in flight when Jev declares victory).
                    confirm_later(passes[0]["name"] if passes else None, "DONE", "confirming DONE", "DONE")
                    continue
                if operation == "BLOCKED":
                    ask_reason(step, state)
                    finish(page, step, "blocked", {"action": "BLOCKED", "ok": True, "error": None})
                    break

                if operation == "TYPE_TEXT" and spec.get("batch_fields") and target and not target.get("missing") and any(
                        k.startswith(FILL_PREFIX) for k in offered):
                    # One request per form: the other empty fields Jev assigned a value to in this same request are typed
                    # next, one step each, without asking again (batch_next, at the top of the loop).
                    planned = plan_batch(spec, obs, answers, offered, target["element"], value_key, th["batch_confidence"])
                    step["fill"] = {k[len(FILL_PREFIX):]: {"choice": a["choice"], "confidence": round(a["confidence"], 3)}
                                    for k in offered if k.startswith(FILL_PREFIX) for a in [read_choice(answers, k, offered[k])] if a}
                    if planned:
                        by_idx = {e["idx"]: e for e in obs["elements"]}
                        attrs = read_attrs([p["element"] for p in planned if not by_idx[p["element"]].get("frame")])
                        items = [{"target": describe_target(by_idx[p["element"]], attrs.get(str(p["element"])), tokens),
                                  "value_key": p["value_key"], "confidence": p["confidence"],
                                  "label": f'{by_idx[p["element"]]["role"]} "{by_idx[p["element"]].get("name") or ""}"'} for p in planned]
                        step["batch_planned"] = [{"field": i["label"], "value_key": i["value_key"], "confidence": round(i["confidence"], 3)} for i in items]
                        batch = {"items": items, "print": page_print(obs, tokens), "text": obs["visible_text"],
                                 "covered": obs.get("covered", 0), "options": options_shown(obs)}
                if act(n, step, obs, sig, operation, target, value_key, lambda: state):
                    break
                if batch is not None and not step["executed"]["ok"]:
                    batch = None  # the first field was not typed: nothing follows from it
            else:
                status = "budget_exhausted"
            t_lap = lap("steps_ms", t_lap)

            if status == "budget_exhausted":
                # The final look, as one more terminal step: the page after the last allowed action, asked only
                # the check and outcome questions. It is the recheck of a sighting made on the last step (or of
                # Jev's DONE there), so such a pass ends confirmed like any other; a non-pass outcome ends the
                # run under the same fail_fast rule as inside the loop; a pass FIRST seen here has had no
                # settle-and-recheck, so it stays budget_exhausted with `pending_outcome` naming it (the next
                # run gets one more step). Any other ending stays budget_exhausted.
                n = (trace["steps"][-1]["n"] + 1) if trace["steps"] else 1
                obs = look()
                sig = signature(obs)
                announced = take_announcements(n, obs)
                note_page_change(sig)
                step = {
                    "n": n, "url": obs["url"], "title": obs["title"], "signature": sig, "screenshot": None,
                    "elements": obs["elements"], "truncated_elements": obs["truncated"],
                    "visible_text": obs["visible_text"][:600], "final_look": True, "offered_operations": [],
                }
                if obs.get("covered"):
                    step["covered_controls"] = obs["covered"]
                    step["layer_controls"] = obs.get("layer_controls", 0)
                if obs.get("loading_options"):
                    step["loading_options"] = obs["loading_options"]
                if announced:
                    step["announcements"] = announced
                if obs.get("frames"):
                    step["frames"] = obs["frames"]
                for hint in ("iframes", "shadow_hosts"):
                    if obs.get(hint):
                        step[hint] = obs[hint]
                note_diagnostics(step)
                recent_ann = recent_announcements(all_announcements, n)
                questions, meta = build_questions(spec, obs, last_operation, outcomes, ask_blocked=True, announcements=recent_ann)
                last_look = {k: v for k, v in questions.items() if k in spec["checks"] or k in ("outcome", "blocked_reason")}
                checks, outcome_answer = {}, None
                try:
                    t_jev = time.perf_counter()
                    resp = jev.system_one(build_state(spec, obs, n, history, recent_ann), last_look)
                    step["latency_ms"] = {"jev": latency_of(resp, t_jev)}
                    step["usage"] = resp.get("usage")
                    checks = read_checks(resp["answers"], spec)
                    if "outcome" in last_look:
                        outcome_answer = read_outcome(resp["answers"], meta["offered"]["outcome"])
                        step["outcome"] = outcome_answer
                    step["blocked_reason"] = read_choice(resp["answers"], "blocked_reason", meta["offered"]["blocked_reason"])
                except JevError as e:
                    error = step["error"] = str(e)
                step["checks"] = checks
                seen = accepted(seen_outcomes(outcomes, checks, outcome_answer, th["outcome_true"]), step)
                non_pass = [s for s in seen if s["verdict"] != "pass"]
                passes = [s for s in seen if s["verdict"] == "pass"]
                trace["final"] = {"url": obs["url"], "title": obs["title"], "checks": checks}
                if non_pass and spec["fail_fast"]:
                    end_with_outcome(page, step, non_pass[0], jev)
                elif passes and pending:
                    settle_pass(page, step, obs, passes[0], pending["action"], jev)
                else:
                    if non_pass:
                        step["outcome_seen"] = non_pass[0]["name"]
                    if passes:
                        step["pending_outcome"] = passes[0]["name"]  # seen, not rechecked: undetermined
                    finish(page, step, "budget_exhausted", dict(STOP))
            else:
                last = trace["steps"][-1] if trace["steps"] else {}
                trace["final"] = final_page(last.get("checks", {}))
            last = trace["steps"][-1] if trace["steps"] else {}
            if last.get("screenshot") and (last.get("executed") or {}).get("action") in ("AUTO_DONE", "DONE", "STOP", "BLOCKED"):
                # nothing happened after the terminal step's picture: final.png is that picture (a copy, not a capture)
                shutil.copyfile(os.path.join(out_dir, *last["screenshot"].split("/")), os.path.join(out_dir, "steps", "final.png"))
                trace["final"]["screenshot"] = "steps/final.png"
            else:
                trace["final"]["screenshot"] = shot(page, "final.png", trace["final"])
            lap("final_ms", t_lap)
        except Exception as e:  # noqa: BLE001
            status, error = "error", f"{type(e).__name__}: {str(e)[:500]}"
            trace["final"] = final_page({})
            try:
                trace["final"]["screenshot"] = shot(page, "final.png", trace["final"])
            except Exception:  # noqa: BLE001 - no picture of a page that is gone
                pass
        finally:
            diagnostics.take((trace["steps"][-1]["n"] + 1) if trace["steps"] else 0)  # what arrived after the last look
            if spec["teardown"] and trace.get("failed_before_observation") != "navigation":
                # After the verdict and its picture, whatever the verdict was (a start page that never loaded has
                # nothing to clean up). Best effort: recorded, never part of the result.
                t_td = time.perf_counter()
                teardown_summary = run_teardown(page, spec, trace["teardown"], net)
                timing["teardown_ms"] = int((time.perf_counter() - t_td) * 1000)
            if cdp_url:
                # Only what we opened goes away: the user's tabs stay. On a connected browser,
                # browser.close() just disconnects (and drops a context only if we created it).
                for tab in [*popups, first_page]:
                    try:
                        tab.close()
                    except Exception:  # noqa: BLE001 - already gone
                        pass
                if created_context:
                    context.close()
            else:
                context.close()
            if browser is not None:
                browser.close()
            if cache_slot is not None:
                cache_slot.release()

    if session_info is not None:
        trace["session"] = session_info  # was a saved login reused, and if not, why; was this run's saved
    trace["status"] = status or "error"
    trace["status_meaning"] = TERMINAL_STATUSES.get(trace["status"], "")
    trace["pass"] = trace["status"] == "passed"
    trace["error"] = error
    trace["ended_at"] = now_iso()
    trace["duration_ms"] = int((time.perf_counter() - t_start) * 1000)
    connect_ms = getattr(jev, "connect_ms", None)
    if isinstance(connect_ms, int):
        timing["jev_connect_ms"] = connect_ms  # paid while the browser launched, not on the first request
    trace["timing"] = timing
    trace["actions_executed"] = sum(1 for s in trace["steps"] if is_action_step(s))
    trace["usage"] = jev.usage_summary()
    trace["adjudication"] = final.get("adjudication")
    if diagnostics.any():
        trace["diagnostics"] = diagnostics.for_trace()
    result = build_result(trace, spec, outcomes, final, out_dir)
    if diagnostics.any():
        # the browser's own account of what went wrong, beside the page's: exceptions, 5xx responses, failed requests
        result["diagnostics"] = diagnostics.for_result()
    if teardown_summary is not None:
        result["teardown"] = trace["teardown_result"] = teardown_summary
    if spec.get("expect"):
        # an expected-red spec (a documented breakage): the run is green when the result matches what was declared
        result["expected"] = match_expect(result, spec["expect"])
    trace["expected"] = result.get("expected")
    trace["outcome"], trace["verdict"] = result["outcome"], result["verdict"]
    if session_info is not None:
        result["session"] = session_info
    if spec.get("batch_fields"):
        result["batch"] = trace["batch"] = batch_account  # fields typed without a request of their own, and where a batch stopped
    if rp is not None:
        # steps replayed, where Jev took over and why, and whether this run's path was saved (a passing run's is)
        result["replay"] = trace["replay"] = rp.finish(trace, save=rp_cfg.get("save", True))
    trace["result"] = result
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "trace.json"), "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
    return trace


def main(argv: list[str]) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", help="output directory (default runs/<spec id>/<timestamp>)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--headed", action="store_true",
                      help=f"show the browser window (beats {HEADED_ENV} and the spec's browser.headless)")
    mode.add_argument("--headless", action="store_true",
                      help=f"hide it (beats {HEADED_ENV}=1 and the spec); the default when nothing says otherwise")
    ap.add_argument("--screenshots", choices=("all", "key", "none"),
                    help="all = every step, key = terminal and flagged steps only (spec default), none = not even final.png")
    ap.add_argument("--no-screenshots", action="store_true", help="alias for --screenshots none")
    ap.add_argument("--model", help="override TYPESAFE_MODEL (default jev-latest)")
    ap.add_argument("--cdp-url", help="attach to a running browser (overrides browser.cdp_url), e.g. http://127.0.0.1:9222")
    ap.add_argument("--device", help="emulate a Playwright device (overrides browser.device), e.g. 'iPhone 13', 'Pixel 7'")
    ap.add_argument("--evidence", choices=("always", "failures"),
                    help="failures = do not ask for the evidence line of a pass whose assertions hold (one request fewer per pass); overrides the spec")
    ap.add_argument("--hover", action="store_true", help="offer the HOVER operation (adds it to the spec's extra_operations)")
    deep = ap.add_mutually_exclusive_group()
    deep.add_argument("--shadow-dom", action="store_true", help="observe inside open shadow roots (observation.shadow_dom; the default)")
    deep.add_argument("--no-shadow-dom", action="store_true", help="observe the document's own tree only (observation.shadow_dom false)")
    ap.add_argument("--junit", metavar="FILE", help="also write the result as a JUnit XML report (one test case) for a CI dashboard")
    ap.add_argument("--reuse-sessions", action="store_true",
                    help="a spec with a `login` block starts from the session an earlier run with the same login on the same site "
                         "saved (.jev/sessions) and skips the login; the first run saves it (spec: \"session\": true)")
    ap.add_argument("--session-dir", metavar="DIR", help="where sessions are kept (default .jev/sessions)")
    ap.add_argument("--http-cache", action="store_true",
                    help="keep the browser's HTTP cache between runs (.jev/http-cache; cookies and storage are not kept)")
    ap.add_argument("--http-cache-dir", metavar="DIR", help="where the cache profiles are kept (default .jev/http-cache)")
    ap.add_argument("--settle", choices=("dom", "network"),
                    help="when a page counts as settled after an action: dom = quiet for browser.quiet_ms (the default); network = "
                         "the requests the action started have finished and the DOM has been quiet for browser.network_quiet_ms")
    ap.add_argument("--batch-fields", action="store_true",
                    help="one request per form: on a page with several empty text fields Jev assigns a value to each in the request "
                         "that types the first, and the others are typed without asking again (spec: \"batch_fields\": true)")
    rpl = ap.add_mutually_exclusive_group()
    rpl.add_argument("--replay", action="store_true",
                     help="walk the path saved by this spec's last passing run without asking Jev, for as long as each step still "
                          "applies to the page, and save the path when this run passes (spec: \"replay\": true)")
    rpl.add_argument("--no-replay", action="store_true", help="ignore a saved path and the spec's `replay`: every step is Jev's")
    ap.add_argument("--replay-record", action="store_true",
                    help="with replay on: do not read the saved path, only write this run's when it passes (record afresh)")
    ap.add_argument("--replay-verify", choices=VERIFY_MODES,
                    help="how a fully replayed run's ending is decided: jev = one request asks which outcome the page shows (default); "
                         "assert = a spec with assertions is decided by them alone")
    ap.add_argument("--replay-dir", metavar="DIR", help="where saved paths are kept (default .jev/paths; overrides replay.dir)")
    args = ap.parse_args(argv[1:])

    load_dotenv()  # ./.env, if present; exported variables win
    try:
        spec = load_spec(args.spec)
        spec["browser"]["headless"] = resolve_headless(spec["browser"]["headless"], headed=args.headed, headless=args.headless)
        if args.device:
            spec["browser"]["device"] = args.device
        if args.evidence:
            spec["evidence"] = args.evidence
        if args.hover and "HOVER" not in spec["extra_operations"]:
            spec["extra_operations"] = [*spec["extra_operations"], "HOVER"]
        if args.shadow_dom or args.no_shadow_dom:
            spec["observation"]["shadow_dom"] = bool(args.shadow_dom)
        if args.batch_fields:
            spec["batch_fields"] = True
        if args.settle:
            spec["browser"]["settle"] = args.settle
        if args.reuse_sessions and not spec["session"].get("never"):
            spec["session"]["reuse"] = True
        if args.session_dir:
            spec["session"]["dir"] = args.session_dir
        if args.http_cache:
            spec["browser"]["http_cache"] = True
        if args.http_cache_dir:
            spec["browser"]["http_cache_dir"] = args.http_cache_dir
        if args.replay or args.no_replay:
            spec["replay"]["enabled"] = bool(args.replay) and not spec["replay"].get("never")  # "replay": "never" beats --replay
        if args.replay_record:
            spec["replay"]["use"] = False
        if args.replay_verify:
            spec["replay"]["verify"] = args.replay_verify
        if args.replay_dir:
            spec["replay"]["dir"] = args.replay_dir
        missing_files = [f"{k}: {v}" for k, v in spec["files"].items() if not os.path.isfile(v)]
        if missing_files:
            raise ValueError("Spec problems:\n  - files: no such file (paths are relative to " + os.getcwd() + "): " + ", ".join(missing_files))
        if args.cdp_url:
            spec["browser"]["cdp_url"] = args.cdp_url
            problems = validate(spec)
            if problems:
                raise ValueError("Spec problems:\n  - " + "\n  - ".join(problems))
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for note in spec_warnings(spec):  # advisory (a secret too short to mask safely); never changes the exit code
        print(f"warning: {note}", file=sys.stderr)
    try:
        jev = JevClient(model=args.model)
    except JevError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Playwright is not installed: pip install -r scripts/requirements.txt && python -m playwright install chromium", file=sys.stderr)
        return 2

    out_dir = args.out or os.path.join("runs", spec["id"], datetime.now().strftime("%Y%m%d-%H%M%S"))
    screenshots = {"all": True, "key": "key", "none": False, None: None}["none" if args.no_screenshots else args.screenshots]
    try:
        trace = run(spec, jev, out_dir, screenshots=screenshots)
    except BrowserUnavailable as e:
        print(str(e), file=sys.stderr)
        return 2
    finally:
        close = getattr(jev, "close", None)  # the seam only requires system_one() and usage_summary()
        if close:
            close()
    print(summarize(trace, out_dir))
    if args.junit:
        from junit import run_case, write_junit
        write_junit(args.junit, "jev-browser-test", [run_case(trace["result"], exit_code(trace), trace.get("duration_ms"))])
    return exit_code(trace)


def exit_code(trace: dict) -> int:
    """0 = green, 1 = red, 2 = never a verdict. Green is a pass, or for a spec with `expect` the declared result;
    a start page that never loaded or a setup step that failed (`failed_before_observation`) is 2, like a spec or
    environment problem, because the flow was not exercised."""
    if trace.get("failed_before_observation"):
        return 2
    if trace.get("expected") is not None:
        return 0 if trace["expected"].get("matched") else 1
    return 0 if trace.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
