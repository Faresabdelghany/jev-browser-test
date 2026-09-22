"""Run one Jev browser test from a spec and write a trace.

    python scripts/run_test.py path/to/spec.json [--out runs/<id>] [--headed] [--screenshots all|key|none] [--cdp-url URL]

Exit codes: 0 = passed, 1 = did not pass (see trace status), 2 = spec / environment problem.

No language model sits in this loop. Claude writes the spec beforehand and reads the trace afterwards;
Jev makes one typed decision per step; Playwright executes. Everything here is deterministic given
Jev's answers, which is what makes the trace trustworthy evidence. Those answers are validated
against the options that were offered before anything is executed (policy.validate_choice): a
malformed `operation` answer is asked again once, then ends the run; a malformed target is never acted on.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone

from jev_client import JevClient, JevError
from observe import GUARD_SKIPPED, TARGET_OPERATIONS, compare_fingerprint, fingerprint, observe, signature
from policy import build_questions, build_state, read_checks, read_choice, resolve_target, validate_choice
from spec import load_dotenv, load_spec, validate
from summarize_trace import summarize

class BrowserUnavailable(RuntimeError):
    """The browser could not be launched or attached to: an environment problem (exit 2), not a test result."""


SCREENSHOT_TIMEOUT_MS = 3000  # a capture is ~50-100 ms; a page whose web font never loads must not stall every capture


TERMINAL_STATUSES = {
    "passed": "all done_when checks satisfied",
    "done_unverified": "Jev chose DONE confidently, and after a settle-and-recheck the done_when checks are still not satisfied",
    "blocked": "Jev chose BLOCKED: it saw no way to make progress",
    "never_violated": "a 'never' check became true",
    "stuck": "the same action on the same page repeated max_repeat times",
    "low_confidence": "max_low_confidence_steps consecutive low-confidence decisions (none of them executed): Jev could not choose between the offered options",
    "budget_exhausted": "max_steps or max_seconds reached",
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
  const optionVisible = () => {
    for (const e of document.querySelectorAll('[role="option"]')) {
      const r = e.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight &&
          (!e.checkVisibility || e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }))) return true;
    }
    return false;
  };
  const tick = () => {
    if (done) return;
    frames++;
    const now = performance.now();
    if (frames >= 2 && now - lastMutation >= quietMs) {
      if (!waitForOptions) return finish('quiet');
      if (optionVisible()) return finish('options');
      if (now - t0 >= 200) return finish('options_timeout');
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})
"""

AUTOCOMPLETE_ROLES = ("combobox", "searchbox")


def settle(page, spec: dict, after: tuple[str | None, str | None] | None = None) -> dict:
    """Wait for the page to stop changing after an action, then return how the wait ended.

    Event-based, not a fixed pause: `domcontentloaded` (short timeout, ignored on failure), then a page-side
    promise that resolves once two animation frames have passed AND the DOM has had no mutation for
    `browser.quiet_ms`, capped at `browser.settle_ms`. After TYPE_TEXT into a combobox/searchbox
    (`after=(operation, target_role)`) it also waits, up to 200 ms, for a visible `[role=option]`, so a
    prediction is not paid for before the autocomplete suggestions arrive. If the evaluate throws because
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


def run_setup(page, spec: dict) -> list[dict]:
    """Deterministic Playwright steps before Jev takes over (login, cookie banner, fixtures)."""
    results = []
    timeout = spec["browser"]["action_timeout_ms"]
    for i, step in enumerate(spec["setup"]):
        act = step["action"]
        rec = {"n": i, "action": act, "selector": step.get("selector"), "ok": True, "error": None}
        try:
            if act == "goto":
                page.goto(step["url"], wait_until="domcontentloaded")
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
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            results.append(rec)
            raise RuntimeError(f"setup[{i}] ({act}) failed: {rec['error']}") from None
        results.append(rec)
    return results


def execute(page, spec: dict, operation: str, target: dict | None, value_key: str | None) -> dict:
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
            page.wait_for_timeout(spec["browser"]["settle_ms"])  # then the loop's normal settle
        else:
            raise RuntimeError(f"unknown operation {operation}")
    except Exception as e:  # noqa: BLE001
        res["ok"] = False
        res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    return res


def note_invalid(step: dict, text: str) -> None:
    """Append one '<question>: <reason>' to step["invalid_answer"] (several are joined with '; ')."""
    step["invalid_answer"] = f"{step['invalid_answer']}; {text}" if step.get("invalid_answer") else text


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


def wait_entry(n: int, operation: str, reason: str) -> dict:
    """A runner-inserted wait (low confidence, DONE confirmation) as Jev should see it in recent_actions."""
    return {"step": n, "operation": operation, "reason": reason, "ok": True, "page_changed": None}


SCREENSHOT_MODES = (True, False, "key")


def run(spec: dict, jev, out_dir: str, screenshots: bool | str | None = None, headed: bool = False) -> dict:
    """Execute the spec. `jev` is anything with .system_one(state, questions) and .usage_summary().

    `screenshots`: True (every step), False (none, not even final.png) or "key" (terminal and flagged
    steps only); None takes the spec's `observation.screenshots`.
    """
    from playwright.sync_api import sync_playwright

    mode = spec["observation"]["screenshots"] if screenshots is None else screenshots
    if not (mode is True or mode is False or mode == "key"):
        raise ValueError(f"screenshots must be one of {SCREENSHOT_MODES}, got {mode!r}")
    th = spec["thresholds"]
    budget = spec["budget"]
    obs_cfg = spec["observation"]

    trace: dict = {
        "spec_id": spec["id"],
        "started_at": now_iso(),
        "status": None,
        "pass": False,
        "steps": [],
        "setup": [],
        "final": None,
        "spec": redacted_spec(spec),
    }
    t_start = time.perf_counter()
    history: list[dict] = []
    last_operation: str | None = None
    low_streak = 0
    stale_streak = 0
    pending_done = False  # a confident DONE with unsatisfied checks gets one settle-and-recheck
    pending_change: tuple[dict, dict, str] | None = None  # (history entry, trace step, signature decided on)
    repeats: dict = {}
    status: str | None = None
    error: str | None = None

    def record(entry: dict, step: dict, sig: str) -> None:
        """Append a history entry and remember which observation it was decided on, so the next
        observation can say whether the page changed (`page_changed` on the entry and the step)."""
        nonlocal pending_change
        history.append(entry)
        pending_change = (entry, step, sig)

    def note_page_change(sig: str) -> None:
        nonlocal pending_change
        if pending_change:
            entry, prev_step, before = pending_change
            entry["page_changed"] = prev_step["page_changed"] = sig != before
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
                    or step.get("repeat_count", 0) >= 2)

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

    STOP = {"action": "STOP", "ok": True, "error": None}

    def satisfied(checks: dict) -> bool:
        return bool(spec["done_when"]) and all(checks.get(c, 0.0) >= th["check_true"] for c in spec["done_when"])

    def violated(checks: dict) -> list[str]:
        return [c for c in spec["never"] if checks.get(c, 0.0) >= th["never_true"]]

    timing: dict = {}  # where the wall-clock went: launch, navigation, setup, steps, final

    def lap(name: str, since: float) -> float:
        timing[name] = int((time.perf_counter() - since) * 1000)
        return time.perf_counter()

    with sync_playwright() as p:
        t_lap = time.perf_counter()
        cdp_url = spec["browser"]["cdp_url"]
        viewport = {"width": spec["browser"]["viewport"][0], "height": spec["browser"]["viewport"][1]}
        created_context = True
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
                page = context.new_page()
                page.set_viewport_size(viewport)
                trace["browser"] = {"attached": True, "cdp_url": cdp_url,
                                    "storage_state_ignored": bool(spec["browser"]["storage_state"])}
            else:
                browser = p.chromium.launch(
                    headless=not headed and spec["browser"]["headless"],
                    channel=spec["browser"]["channel"],
                )
                ctx_kwargs = {"viewport": viewport}
                if spec["browser"]["storage_state"]:
                    ctx_kwargs["storage_state"] = spec["browser"]["storage_state"]
                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()
                trace["browser"] = {"attached": False}
        except Exception as e:  # noqa: BLE001 - nothing to trace yet: this is the environment, not the test
            what = (f"could not attach to the browser at {cdp_url} (is Chrome running with --remote-debugging-port?)"
                    if cdp_url else "could not launch the browser")
            raise BrowserUnavailable(f"{what}: {type(e).__name__}: {str(e).splitlines()[0][:300]}") from None
        # Tabs the flow itself opens (target=_blank, window.open) are ours to close: launch mode closes them
        # with the context; in attached mode they would otherwise stay in the user's browser.
        popups: list = []

        def track_popup(popup) -> None:
            popups.append(popup)
            popup.on("popup", track_popup)

        page.on("popup", track_popup)
        page.set_default_timeout(spec["browser"]["action_timeout_ms"])
        os.makedirs(os.path.join(out_dir, "steps"), exist_ok=True)
        t_lap = lap("launch_ms", t_lap)
        try:
            page.goto(spec["start_url"], wait_until="domcontentloaded")
            settle(page, spec)
            t_lap = lap("navigation_ms", t_lap)
            trace["setup"] = run_setup(page, spec)
            t_lap = lap("setup_ms", t_lap)

            for n in range(1, budget["max_steps"] + 1):
                if time.perf_counter() - t_start > budget["max_seconds"]:
                    status = "budget_exhausted"
                    break
                obs = observe(page, obs_cfg["max_elements"], obs_cfg["max_text_chars"])
                sig = signature(obs)
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
                state = build_state(spec, obs, n, history)
                questions, meta = build_questions(spec, obs, last_operation)
                offered = meta["offered"]
                step["offered_operations"] = meta["operations"]
                try:
                    t_jev = time.perf_counter()
                    resp = jev.system_one(state, questions)
                    step["latency_ms"] = {"jev": latency_of(resp, t_jev)}
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

                bad = violated(checks)
                if bad:
                    step["never_violated"] = bad
                    if spec["fail_fast"]:
                        finish(page, step, "never_violated", dict(STOP))
                        break

                if pending_done:
                    # Jev said DONE last step while done_when was unsatisfied; the page has now had a
                    # full settle (reloads, toasts, redirects). This observation is the verdict.
                    finish(page, step, "passed" if satisfied(checks) else "done_unverified",
                           {"action": "DONE", "ok": True, "error": None, "confirmed": True})
                    break

                if satisfied(checks) and spec["auto_done"]:
                    finish(page, step, "passed", {"action": "AUTO_DONE", "ok": True, "error": None})
                    if n == 1 and not spec["setup"]:
                        trace["passed_without_actions"] = True
                    break

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
                    low_streak += 1
                    stale_streak = 0  # a refused decision is not a stale one: `max_stale` counts consecutive stale steps
                    if low_streak >= th["max_low_confidence_steps"]:
                        finish(page, step, "low_confidence", dict(STOP))
                        break
                    step["executed"] = {"action": "WAIT", "ok": True, "error": None,
                                        "reason": f"low confidence; {operation} not executed"}
                    capture(page, step)
                    record(wait_entry(n, "WAIT", "undecided between the offered options; nothing was executed"), step, sig)
                    t_b = time.perf_counter()
                    page.wait_for_timeout(spec["browser"]["settle_ms"])  # a real wait, like the WAIT operation
                    step["settle"] = settle(page, spec)
                    step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                    trace["steps"].append(step)
                    continue
                low_streak = 0

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
                        step["executed"] = {"action": "WAIT", "ok": True, "error": None,
                                            "reason": f"page changed during the decision: {reason}"}
                        capture(page, step)
                        t_b = time.perf_counter()
                        step["settle"] = settle(page, spec)
                        step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                        trace["steps"].append(step)
                        continue
                stale_streak = 0

                if operation == "DONE":
                    if satisfied(checks):
                        finish(page, step, "passed", {"action": "DONE", "ok": True, "error": None})
                        break
                    if n >= budget["max_steps"]:
                        finish(page, step, "done_unverified", {"action": "DONE", "ok": True, "error": None})
                        break
                    # Confident DONE but the checks disagree: give the page one full settle and look
                    # again before calling it (a reload or redirect is often still in flight).
                    pending_done = True
                    step["executed"] = {"action": "WAIT", "ok": True, "error": None, "reason": "confirming DONE"}
                    capture(page, step)
                    record(wait_entry(n, "DONE", "checking the result before finishing"), step, sig)
                    t_b = time.perf_counter()
                    page.wait_for_timeout(spec["browser"]["settle_ms"])
                    step["settle"] = settle(page, spec)
                    step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                    trace["steps"].append(step)
                    continue
                if operation == "BLOCKED":
                    finish(page, step, "blocked", {"action": "BLOCKED", "ok": True, "error": None})
                    break

                key = (sig, operation, target["choice"] if target and not target.get("missing") else None, value_key)
                repeats[key] = repeats.get(key, 0) + 1
                step["repeat_count"] = repeats[key]
                if repeats[key] >= th["max_repeat"]:
                    finish(page, step, "stuck", dict(STOP))
                    break

                # The page Jev decided on, before anything changes it. The last allowed step is terminal
                # for the budget (the for-else below), so it gets its picture like every terminal step.
                capture(page, step, terminal=(n == budget["max_steps"]))
                t_b = time.perf_counter()
                executed = execute(page, spec, operation, target, value_key)
                if not executed["ok"]:
                    step["screenshot_after_failure"] = shot(page, f"{n:03d}-failed.png", step)
                target_role = next((e["role"] for e in obs["elements"] if e["idx"] == (target or {}).get("element")), None)
                step["settle"] = settle(page, spec, after=(operation, target_role))
                step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
                step["executed"] = executed
                record(history_entry(n, operation, target, value_key, executed), step, sig)
                last_operation = operation if executed["ok"] else None
                trace["steps"].append(step)
            else:
                status = "budget_exhausted"
            t_lap = lap("steps_ms", t_lap)

            if status == "budget_exhausted":
                # One last look: did the final action happen to reach the goal?
                obs = observe(page, obs_cfg["max_elements"], obs_cfg["max_text_chars"])
                note_page_change(signature(obs))
                questions, _ = build_questions(spec, obs, last_operation)
                only_checks = {k: v for k, v in questions.items() if k in spec["checks"]}
                final_checks = {}
                if only_checks:
                    try:
                        resp = jev.system_one(build_state(spec, obs, len(trace["steps"]) + 1, history), only_checks)
                        final_checks = read_checks(resp["answers"], spec)
                    except JevError as e:
                        error = str(e)
                if satisfied(final_checks) and spec["auto_done"] and not violated(final_checks):
                    status = "passed"
                trace["final"] = {"url": obs["url"], "title": obs["title"], "checks": final_checks}
            else:
                last = trace["steps"][-1] if trace["steps"] else {}
                trace["final"] = {
                    "url": page.url,
                    "title": page.title(),
                    "checks": last.get("checks", {}),
                }
            trace["final"]["screenshot"] = shot(page, "final.png", trace["final"])
            lap("final_ms", t_lap)
        except Exception as e:  # noqa: BLE001
            status, error = "error", f"{type(e).__name__}: {str(e)[:500]}"
            try:
                trace["final"] = {"url": page.url, "title": page.title(), "checks": {}}
                trace["final"]["screenshot"] = shot(page, "final.png", trace["final"])
            except Exception:
                trace["final"] = {"url": None, "title": None, "checks": {}}
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
    trace["timing"] = timing
    trace["actions_executed"] = sum(
        1 for s in trace["steps"]
        if s.get("executed", {}).get("action") not in (None, "STOP", "DONE", "AUTO_DONE", "BLOCKED")
        and not s.get("executed", {}).get("reason")  # runner-inserted waits (low confidence, DONE recheck) are not actions
    )
    trace["usage"] = jev.usage_summary()
    with open(os.path.join(out_dir, "trace.json"), "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
    return trace


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", help="output directory (default runs/<spec id>/<timestamp>)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--screenshots", choices=("all", "key", "none"),
                    help="all = every step, key = terminal and flagged steps only (spec default), none = not even final.png")
    ap.add_argument("--no-screenshots", action="store_true", help="alias for --screenshots none")
    ap.add_argument("--model", help="override TYPESAFE_MODEL (default jev-latest)")
    ap.add_argument("--cdp-url", help="attach to a running browser (overrides browser.cdp_url), e.g. http://127.0.0.1:9222")
    args = ap.parse_args(argv[1:])

    load_dotenv()  # ./.env, if present; exported variables win
    try:
        spec = load_spec(args.spec)
        if args.cdp_url:
            spec["browser"]["cdp_url"] = args.cdp_url
            problems = validate(spec)
            if problems:
                raise ValueError("Spec problems:\n  - " + "\n  - ".join(problems))
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
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
        trace = run(spec, jev, out_dir, screenshots=screenshots, headed=args.headed)
    except BrowserUnavailable as e:
        print(str(e), file=sys.stderr)
        return 2
    finally:
        close = getattr(jev, "close", None)  # the seam only requires system_one() and usage_summary()
        if close:
            close()
    print(summarize(trace, out_dir))
    return 0 if trace["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
