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
    fingerprint, mask_secrets, mask_text, observe, signature,
)
from policy import (
    ADJUDICATION_MAX_LINES, ADJUDICATION_NONE, announcement_lines, build_adjudication, build_questions, build_reason_questions,
    build_state, defer_action, deferred_outcomes, evidence_line_keys, is_field, quoted_pick, read_checks, read_choice,
    read_outcome, recent_announcements, resolve_target, seen_outcomes, suggested_verdict, validate_choice,
)
from spec import (HEADED_ENV, UNDETERMINED, effective_outcomes, load_dotenv, load_spec, match_expect, resolve_headless,
                  spec_warnings, validate)
from summarize_trace import is_action_step, summarize


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
    for step in s["setup"]:
        if step.get("action") == "fill":
            step["value"] = "<redacted>"
    return s


SETTLE_JS = r"""
(args) => new Promise(resolve => {
  const { quietMs, capMs, waitForOptions } = args;
  const t0 = performance.now();
  let frames = 0, lastMutation = t0, done = false, cap = null;
  const mo = new MutationObserver(() => { lastMutation = performance.now(); });
  try {
    mo.observe(document.documentElement || document, { subtree: true, childList: true, attributes: true, characterData: true });
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


def settle(page, spec: dict, after: tuple[str | None, str | None] | None = None) -> dict:
    """Wait for the page to stop changing after an action, then return how the wait ended.

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
    operation, role = after or (None, None)
    args = {"quietMs": quiet, "capMs": cap, "waitForOptions": operation == "TYPE_TEXT" and role in AUTOCOMPLETE_ROLES}
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
    result["ms"] = int((time.perf_counter() - t0) * 1000)
    return result


def run_setup(page, spec: dict, results: list[dict] | None = None) -> list[dict]:
    """Deterministic Playwright steps before Jev takes over (login, cookie banner, fixtures). Records land in
    `results` as they run (pass the trace's list, so a failing step is recorded even though this raises)."""
    results = [] if results is None else results
    timeout = spec["browser"]["action_timeout_ms"]
    for i, step in enumerate(spec["setup"]):
        act = step["action"]
        rec = {"n": i, "action": act, "selector": step.get("selector"), "ok": True, "error": None}
        before = fingerprint(page) if act in ("click", "press", "select") else None  # to tell a slow navigation from a failure
        try:
            if act == "goto":
                page.goto(step["url"], wait_until="domcontentloaded", timeout=spec["browser"]["navigation_timeout_ms"])
                rec["url"] = step["url"]
            elif act == "click":
                page.locator(step["selector"]).first.click(timeout=timeout)
            elif act == "fill":
                page.locator(step["selector"]).first.fill(step["value"], timeout=timeout)
            elif act == "press":
                page.locator(step["selector"]).first.press(step["key"], timeout=timeout)
            elif act == "select":
                page.locator(step["selector"]).first.select_option(step["value"], timeout=timeout)
            elif act == "wait":
                page.wait_for_timeout(int(step["ms"]))
            elif act == "wait_for":
                t = int(step.get("timeout_ms", timeout))
                if step.get("selector"):
                    page.locator(step["selector"]).first.wait_for(state=step.get("state", "visible"), timeout=t)
                if step.get("url"):
                    page.wait_for_url(step["url"], timeout=t)
            settle(page, spec)
        except Exception as e:  # noqa: BLE001 - we want every failure in the trace
            if navigation_pending(str(e)):
                rec["slow_navigation"] = await_navigation(page, spec, before, timeout)  # landed; the page is on its way
                settle(page, spec)
                results.append(rec)
                continue
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            results.append(rec)
            raise RuntimeError(f"setup[{i}] ({act}) failed: {rec['error']}") from None
        results.append(rec)
    return results


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


def low_confidence_limit(th: dict, blank: bool) -> int:
    """How many consecutive undecided (low-confidence) decisions on one page end the run `low_confidence`: the spec's
    max_low_confidence_steps on a settled page, BUSY_EXTRA_LOOKS more while a blank layer covers controls (the page is
    still loading or saving, and each undecided look already waits with backoff). Live: three undecided looks on a
    form under its loader, 2.5 + 5 + 10 s, ended a run one look before the fields rendered in a slow hour."""
    return th["max_low_confidence_steps"] + (BUSY_EXTRA_LOOKS if blank else 0)


def deferral_limit(th: dict) -> int:
    """How many times a marginal action under a blank layer is deferred on one page (each a wait with backoff, settle_ms
    x 1, 2, 4, 4, 4, ending when the page changes) before the next such decision is executed anyway: a layer that
    stays that long with Jev still picking a free control is taken at its word (deferrals_exhausted on the step). The
    same count as undecided looks under a blank layer. Live: the deferral fired once per page, and the second identical
    marginal decision typed the first name into the sidebar's filter, or left the Assign form for the Leave List tab,
    while the loader was still up."""
    return th["max_low_confidence_steps"] + BUSY_EXTRA_LOOKS
WAIT_POLL_MS = 100  # a WAIT re-reads the page's fingerprint this often and ends as soon as the page has changed
NO_EFFECT_ACTIONS = {"CLICK", "TYPE_TEXT", "SELECT", "PRESS_ENTER"}  # an executed one of these that changed nothing is flagged
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
            changed = compare_fingerprint(before, fingerprint(page), "DONE") is not None
        except Exception:  # noqa: BLE001 - the document navigated: that is a change
            return {"ended": "navigated", "ms": int((time.perf_counter() - t0) * 1000)}
        if changed:
            return {"ended": "changed", "ms": int((time.perf_counter() - t0) * 1000)}


def execute(page, spec: dict, operation: str, target: dict | None, value_key: str | None, wait_ms: int | None = None,
            before: dict | None = None) -> dict:
    """Perform one operation. `before` is the observation's fingerprint: a WAIT ends as soon as the page differs from it."""
    timeout = spec["browser"]["action_timeout_ms"]
    res: dict = {"action": operation, "ok": True, "error": None}
    try:
        if operation in ("CLICK", "TYPE_TEXT", "SELECT"):
            if not target or target.get("missing"):
                raise RuntimeError("no target answer for this operation")
            loc = page.locator(f'[data-jev-idx="{target["element"]}"]').first
            res["element"] = target["element"]
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
        elif operation == "PRESS_ENTER":
            page.keyboard.press("Enter")
        elif operation == "SELECT":
            res["option"] = target["option"]
            loc.select_option(index=target["option"], timeout=timeout)
        elif operation == "SCROLL_DOWN":
            page.evaluate("window.scrollBy(0, Math.round(window.innerHeight * 0.8))")
        elif operation == "SCROLL_UP":
            page.evaluate("window.scrollBy(0, -Math.round(window.innerHeight * 0.8))")
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


def check_assertions(spec: dict, page, obs: dict, secrets: list[str] | None = None) -> list[dict]:
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
    """
    results = []
    secrets = secrets or []
    body_text: str | None = None
    elements: list[dict] | None = None
    url = page.url
    for a in spec.get("assert") or []:
        (kind, arg), = a.items()
        if isinstance(arg, str):
            shown = mask_text(arg, secrets)
        elif isinstance(arg, list):
            shown = [mask_text(v, secrets) for v in arg]
        else:
            shown = {k: mask_text(v, secrets) for k, v in arg.items()}
        rec: dict = {kind: shown, "ok": False, "actual": None}
        if kind in ELEMENT_ASSERTIONS and elements is None:
            try:
                elements = observe(page, ASSERT_MAX_ELEMENTS, 100, whole_document=True)["elements"]
            except Exception:  # noqa: BLE001 - fall back to what the observer saw
                elements = obs["elements"]
        if kind == "url_matches":
            rec["actual"] = mask_text(url, secrets)
            rec["ok"] = re.fullmatch(glob_to_regex(arg), url) is not None
        elif kind in ("text_contains", "text_order"):
            if body_text is None:
                try:
                    body_text = page.evaluate(BODY_TEXT_JS)
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


def adjudication_request(page, name: str, when: str, secrets: list[str] | None = None, extra_lines: list[str] | None = None) -> dict | None:
    """The evidence questions for a seen outcome (spec §5.4) over the current page's numbered lines, ready to send
    alone (`adjudicate`) or riding in a confirmation step's request (the loop merges them: one round trip fewer
    for every pass). None when the page text cannot be read. The lines are masked like every observation.
    `extra_lines` (the messages the page announced recently, policy.announcement_lines) follow the page's lines, kept
    within the cap: a toast that has faded is then a line Jev can point at, and one still on the page is quoted from it."""
    try:
        lines = [mask_text(ln, secrets or []) for ln in page.evaluate(LINES_JS, ADJUDICATION_MAX_LINES)]
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
               extra_lines: list[str] | None = None) -> dict:
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
    req = adjudication_request(page, name, when, secrets, extra_lines)
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
    outcomes = effective_outcomes(spec)  # declared + synthesized: the runner only knows outcomes

    trace: dict = {
        "spec_id": spec["id"],
        "started_at": now_iso(),
        "status": None,
        "pass": False,
        "outcome": None,
        "verdict": None,
        "steps": [],
        "setup": [],
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
        rel = os.path.join("steps", name)
        try:
            page.screenshot(path=os.path.join(out_dir, rel), timeout=SCREENSHOT_TIMEOUT_MS)
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
        step["settle"] = settle(page, spec)
        step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
        trace["steps"].append(step)

    STOP = {"action": "STOP", "ok": True, "error": None}

    def outcome_when(name: str) -> str:
        """The statement the adjudication quotes against: the outcome's `when`, else its checks' statements."""
        o = outcomes[name]
        return o.get("when") or " and ".join(spec["checks"][r] for r in o["requires"])

    def settle_pass(page, step: dict, obs: dict, seen: dict, action: str, jev, prefetched: dict | None = None,
                    assertions: list[dict] | None = None) -> None:
        """A confirmed pass: run the assertions on this final observation and end passed / assert_failed. With
        `prefetched` (the evidence questions rode in this step's request) the adjudication costs no request; with
        `assertions` (already evaluated on this page by the confirm-by-assertions path) they are not run again."""
        final["outcome"] = seen
        final["seen_at_step"] = step["n"]
        final.setdefault("first_seen_at_step", step["n"])
        final["confirmed"] = True
        final.setdefault("confirmed_by", "recheck")
        final["assertions"] = check_assertions(spec, page, obs, secret_values) if assertions is None else assertions
        ok = all(a["ok"] for a in final["assertions"])
        step["assertions"] = final["assertions"]
        finish(page, step, "passed" if ok else "assert_failed", {"action": action, "ok": True, "error": None, "confirmed": True})
        if ok and not spec["setup"] and not any("reason" not in h for h in history):
            trace["passed_without_actions"] = True
        final["adjudication"] = adjudicate(page, jev, seen["name"], outcome_when(seen["name"]), secret_values, prefetched,
                                           announced_lines(step["n"]))

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
                                           extra_lines=announced_lines(step["n"]))

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
            page, spec, lambda: mask_secrets(observe(page, obs_cfg["max_elements"], obs_cfg["max_text_chars"]), secret_values), bump)

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
                browser = p.chromium.launch(headless=headless, channel=spec["browser"]["channel"])
                ctx_kwargs = {"viewport": viewport}
                if spec["browser"]["storage_state"]:
                    ctx_kwargs["storage_state"] = spec["browser"]["storage_state"]
                context = browser.new_context(**ctx_kwargs)
                context.add_init_script(ANNOUNCE_INIT_JS)
                page = context.new_page()
                trace["browser"] = {"attached": False, "headless": headless}
        except Exception as e:  # noqa: BLE001 - nothing to trace yet: this is the environment, not the test
            what = (f"could not attach to the browser at {cdp_url} (is Chrome running with --remote-debugging-port?)"
                    if cdp_url else "could not launch the browser")
            for d in (os.path.join(out_dir, "steps"), out_dir):  # leave no empty run directory behind
                try:
                    os.rmdir(d)
                except OSError:
                    pass
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
        t_lap = lap("launch_ms", t_lap)
        try:
            phase = "navigation"
            try:
                page.goto(spec["start_url"], wait_until="domcontentloaded", timeout=spec["browser"]["navigation_timeout_ms"])
                settle(page, spec)
                t_lap = lap("navigation_ms", t_lap)
                phase = "setup"
                run_setup(page, spec, trace["setup"])  # records into trace["setup"] as it goes, so a failed step is kept
                t_lap = lap("setup_ms", t_lap)
            except Exception:
                # Nothing was observed, so the flow was not exercised: a slow or unreachable host (navigation), a setup
                # selector that did not match (setup). Reported apart from the flow's outcomes: result.reason.phase,
                # exit 2, and run_suite lists it as an environment/setup failure instead of a flow outcome.
                trace["failed_before_observation"] = phase
                raise

            for n in range(1, budget["max_steps"] + 1):
                if time.perf_counter() - t_start > budget["max_seconds"]:
                    status = "budget_exhausted"
                    break
                obs = look()
                sig = signature(obs)
                announced = take_announcements(n, obs)  # what the page said since the last observation (toasts, live messages)
                note_page_change(sig)  # did the previous action change what Jev sees?
                step: dict = {
                    "n": n,
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
                if after_no_effect:
                    step["after_no_effect"] = True  # this is the page the previous action failed to change
                recent_ann = recent_announcements(all_announcements, n)
                state = build_state(spec, obs, n, history, recent_ann)
                questions, meta = build_questions(spec, obs, last_operation, outcomes, ask_stuck=last_page_changed is False,
                                                  announcements=recent_ann)
                offered = meta["offered"]
                step["offered_operations"] = meta["operations"]
                merged_adj = None
                if pending and pending.get("name"):
                    # The confirmation of a pass sighting: ask the evidence questions in the same request (speculative
                    # fan-out), so a confirmed pass needs no adjudication round trip. The Choices point at state.lines.
                    merged_adj = adjudication_request(page, pending["name"], outcome_when(pending["name"]), secret_values,
                                                      announced_lines(n))
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
                    op_problem = validate_choice(answers.get("operation"), offered["operation"])
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
                op = read_choice(answers, "operation", offered["operation"])  # None iff op_problem
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
                        checked = check_assertions(spec, page, obs, secret_values) if spec["assert"] else []
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
                        checked = check_assertions(spec, page, obs, secret_values)
                        if all(a["ok"] for a in checked):
                            final["confirmed_by"] = "assertions"
                            settle_pass(page, step, obs, passes[0], "AUTO_DONE", jev, assertions=checked)
                            break
                        step["assertions_pending"] = [a for a in checked if not a["ok"]]  # not yet: the recheck decides
                        step["assertions_checked"] = checked
                    confirm_later(passes[0]["name"], "AUTO_DONE", f"confirming outcome {passes[0]['name']}", "WAIT")
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
                    if low_streak >= low_confidence_limit(th, page_loading(obs)):
                        ask_reason(step, state)
                        finish(page, step, "low_confidence", dict(STOP))
                        break
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
                        reason = compare_fingerprint(obs["fingerprint"], fingerprint(page), operation, (target or {}).get("element"))
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

                # Repeat detection: the same action on an unchanged page max_repeat times is `stuck`. A WAIT is
                # not an action on the page: Jev choosing it again on a page that still says "Loading..." is the
                # right answer for as long as the page keeps loading (measured live: a 5 s loader ended `stuck`
                # after 1.5 s with stuck_reason still_loading), so only the budget bounds a streak of WAITs.
                if operation != "WAIT":
                    key = (sig, operation, target["choice"] if target and not target.get("missing") else None, value_key)
                    repeats[key] = repeats.get(key, 0) + 1
                    step["repeat_count"] = repeats[key]
                    if repeats[key] >= th["max_repeat"]:
                        ask_reason(step, state)
                        finish(page, step, "stuck", dict(STOP))
                        break

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
                executed = execute(page, spec, operation, target, value_key, wait_ms, obs.get("fingerprint"))
                if not executed["ok"]:
                    step["screenshot_after_failure"] = shot(page, f"{n:03d}-failed.png", step)
                target_el = next((e for e in obs["elements"] if e["idx"] == (target or {}).get("element")), {})
                step["settle"] = settle(page, spec, after=(operation, None if target_el.get("datalist") else target_el.get("role")))
                step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                step["executed"] = executed
                record(history_entry(n, operation, target, value_key, executed), step, sig)
                last_operation = operation if executed["ok"] else None
                trace["steps"].append(step)
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
                shutil.copyfile(os.path.join(out_dir, last["screenshot"]), os.path.join(out_dir, "steps", "final.png"))
                trace["final"]["screenshot"] = os.path.join("steps", "final.png")
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
            if cdp_url:
                # Only what we opened goes away: the user's tabs stay. On a connected browser,
                # browser.close() just disconnects (and drops a context only if we created it).
                for tab in [*popups, page]:
                    try:
                        tab.close()
                    except Exception:  # noqa: BLE001 - already gone
                        pass
                if created_context:
                    context.close()
            else:
                context.close()
            browser.close()

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
    result = build_result(trace, spec, outcomes, final, out_dir)
    if spec.get("expect"):
        # an expected-red spec (a documented breakage): the run is green when the result matches what was declared
        result["expected"] = match_expect(result, spec["expect"])
    trace["expected"] = result.get("expected")
    trace["outcome"], trace["verdict"] = result["outcome"], result["verdict"]
    trace["result"] = result
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "trace.json"), "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
    return trace


def main(argv: list[str]) -> int:
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
    args = ap.parse_args(argv[1:])

    load_dotenv()  # ./.env, if present; exported variables win
    try:
        spec = load_spec(args.spec)
        spec["browser"]["headless"] = resolve_headless(spec["browser"]["headless"], headed=args.headed, headless=args.headless)
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
