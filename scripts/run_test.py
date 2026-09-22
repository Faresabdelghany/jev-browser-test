"""Run one Jev browser test from a spec and write a trace and a result.

    python scripts/run_test.py path/to/spec.json [--out runs/<id>] [--headed] [--screenshots all|key|none] [--cdp-url URL]

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
import re
import sys
import time
from datetime import datetime, timezone

from jev_client import JevClient, JevError
from observe import (
    GUARD_SKIPPED, LINES_JS, TARGET_OPERATIONS, compare_fingerprint, element_label, fingerprint, mask_secrets, mask_text,
    observe, signature,
)
from policy import (
    ADJUDICATION_MAX_LINES, ADJUDICATION_NONE, build_adjudication, build_questions, build_state, is_field, read_checks,
    read_choice, read_outcome, resolve_target, seen_outcomes, suggested_verdict, validate_choice,
)
from spec import UNDETERMINED, effective_outcomes, load_dotenv, load_spec, spec_warnings, validate
from summarize_trace import is_action_step, summarize


class BrowserUnavailable(RuntimeError):
    """The browser could not be launched or attached to: an environment problem (exit 2), not a test result."""


SCREENSHOT_TIMEOUT_MS = 3000  # a capture is ~50-100 ms; a page whose web font never loads must not stall every capture


TERMINAL_STATUSES = {
    "passed": "an outcome with verdict pass was seen, confirmed after a settle-and-recheck, and every assertion held",
    "outcome": "a declared outcome with a verdict other than pass was seen (result.outcome names it)",
    "assert_failed": "a pass outcome was confirmed but an assertion did not hold on the final page (result.assertions)",
    "done_unverified": "Jev chose DONE confidently, and after a settle-and-recheck no pass outcome is visible",
    "blocked": "Jev chose BLOCKED: it saw no way to make progress",
    "never_violated": "a 'never' check became true (runs before the results contract; now status outcome)",
    "stuck": "the same action on the same page repeated max_repeat times",
    "low_confidence": "max_low_confidence_steps consecutive low-confidence decisions (none of them executed): Jev could not choose between the offered options",
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
  const newOptionVisible = () => visibleOptions().some(e => !e.hasAttribute('data-jev-idx'));
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


def check_assertions(spec: dict, page, obs: dict, secrets: list[str] | None = None) -> list[dict]:
    """Evaluate the spec's `assert` block in code on the final page (spec §5.1): free, exact, non-model.

    Each record repeats the assertion, adds `ok` and `actual` (the value found, or what was there instead).
    `url_matches` is a Playwright glob over the final URL; `text_contains` looks in the whole page text;
    `field_value` matches a text field / select whose label contains the given label (case-insensitive) and
    compares its value; `element_present` / `element_absent` match role and, when given, a name substring.
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
        shown = mask_text(arg, secrets) if isinstance(arg, str) else {k: mask_text(v, secrets) for k, v in arg.items()}
        rec: dict = {kind: shown, "ok": False, "actual": None}
        if kind in ELEMENT_ASSERTIONS and elements is None:
            try:
                elements = observe(page, ASSERT_MAX_ELEMENTS, 100, whole_document=True)["elements"]
            except Exception:  # noqa: BLE001 - fall back to what the observer saw
                elements = obs["elements"]
        if kind == "url_matches":
            rec["actual"] = mask_text(url, secrets)
            rec["ok"] = re.fullmatch(glob_to_regex(arg), url) is not None
        elif kind == "text_contains":
            if body_text is None:
                try:
                    body_text = page.evaluate(BODY_TEXT_JS)
                except Exception:  # noqa: BLE001 - fall back to what the observer saw
                    body_text = obs["visible_text"]
            at = body_text.find(arg)
            rec["ok"] = at >= 0
            excerpt = body_text[max(0, at - 60):at + len(arg) + 60] if at >= 0 else re.sub(r"\s+", " ", body_text)[:200]
            rec["actual"] = mask_text(excerpt, secrets)
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


def adjudicate(page, jev, name: str, when: str, secrets: list[str] | None = None) -> dict:
    """One extra request after a seen outcome (spec §5.4): Jev selects the line of the final page that states
    the outcome (`evidence_line`) and re-judges the statement (`evidence_present`). The chosen line is copied
    verbatim into the result: selection is how a quote is produced. The lines are masked like every
    observation, so a secret the page echoes reaches neither Jev nor the result. Never fatal: the run was
    already decided when this is asked, so any failure (transport, a non-JSON body, a malformed answer) is
    recorded on the record instead of raised."""
    rec: dict = {"outcome": name, "statement": when, "line": None, "line_id": None, "present": None, "confidence": None}
    try:
        lines = [mask_text(ln, secrets or []) for ln in page.evaluate(LINES_JS, ADJUDICATION_MAX_LINES)]
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"could not read the page text: {type(e).__name__}"
        return rec
    state, questions, offered = build_adjudication(name, when, lines)
    t0 = time.perf_counter()
    try:
        resp = jev.system_one(state, questions)
        rec["latency_ms"] = latency_of(resp, t0)
        answers = resp["answers"] if isinstance(resp.get("answers"), dict) else {}
        picked = read_choice(answers, "evidence_line", offered)
        if picked is None:
            rec["invalid_answer"] = f"evidence_line: {validate_choice(answers.get('evidence_line'), offered)}"
        else:
            rec["line_id"] = picked["choice"]
            rec["confidence"] = picked["confidence"]
            if picked["choice"] != ADJUDICATION_NONE:
                rec["line"] = state["lines"][int(picked["choice"]) - 1]["text"]
        present = answers.get("evidence_present")
        if isinstance(present, dict) and isinstance(present.get("noul"), (int, float)) and 0 <= present["noul"] <= 1:
            rec["present"] = round(float(present["noul"]), 3)
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
        "story": story,
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
        result["reason"] = {
            "status": status,
            "blocked_reason": blocked,
            "stuck_reason": stuck,
            "suggested_verdict": suggested_verdict(status, [stuck if status in ("stuck", "budget_exhausted") else None,
                                                            blocked if status in BLOCKED_REASON_STATUSES else None]),
        }
        if status == "assert_failed":
            result["reason"]["outcome_seen"] = (final.get("outcome") or {}).get("name")
            result["reason"]["failed_assertions"] = [a for a in result["assertions"] if not a["ok"]]
        if status == "budget_exhausted" and terminal.get("pending_outcome"):
            # a pass first seen on the final look: the budget ran out before it could be rechecked
            result["reason"]["pending_outcome"] = terminal["pending_outcome"]
        if status == "error":
            result["reason"]["error"] = trace.get("error")
    return result


SCREENSHOT_MODES = (True, False, "key")


def run(spec: dict, jev, out_dir: str, screenshots: bool | str | None = None, headed: bool = False) -> dict:
    """Execute the spec. `jev` is anything with .system_one(state, questions) and .usage_summary().

    `screenshots`: True (every step), False (none, not even final.png) or "key" (terminal and flagged
    steps only); None takes the spec's `observation.screenshots`. Writes trace.json and result.json into
    out_dir and returns the trace (the result is under trace["result"]).
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
    low_streak = 0
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
        nonlocal pending_change, last_page_changed
        if pending_change:
            entry, prev_step, before = pending_change
            entry["page_changed"] = prev_step["page_changed"] = sig != before
            last_page_changed = entry["page_changed"] if "reason" not in entry else None
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

    def park(step: dict, reason: str, entry: dict | None, sig: str, pause: bool = True) -> None:
        """A step the runner refuses to act on (a pending confirmation, a low-confidence decision, a stale
        decision): recorded as a WAIT, pictured per the policy, `entry` (when given) appended to Jev's
        recent_actions, then a real wait like the WAIT operation - settle_ms, then the event-based settle -
        and the step is appended. Every runner-inserted WAIT goes through here, so they all wait the same."""
        step["executed"] = {"action": "WAIT", "ok": True, "error": None, "reason": reason}
        capture(page, step)
        if entry is not None:
            record(entry, step, sig)
        t_b = time.perf_counter()
        if pause:
            page.wait_for_timeout(spec["browser"]["settle_ms"])
        step["settle"] = settle(page, spec)
        step["latency_ms"]["browser"] = int((time.perf_counter() - t_b) * 1000)
        trace["steps"].append(step)

    STOP = {"action": "STOP", "ok": True, "error": None}

    def outcome_when(name: str) -> str:
        """The statement the adjudication quotes against: the outcome's `when`, else its checks' statements."""
        o = outcomes[name]
        return o.get("when") or " and ".join(spec["checks"][r] for r in o["requires"])

    def settle_pass(page, step: dict, obs: dict, seen: dict, action: str, jev) -> None:
        """A confirmed pass: run the assertions on this final observation and end passed / assert_failed."""
        final["outcome"] = seen
        final["seen_at_step"] = step["n"]
        final.setdefault("first_seen_at_step", step["n"])
        final["confirmed"] = True
        final["assertions"] = check_assertions(spec, page, obs, secret_values)
        ok = all(a["ok"] for a in final["assertions"])
        step["assertions"] = final["assertions"]
        finish(page, step, "passed" if ok else "assert_failed", {"action": action, "ok": True, "error": None, "confirmed": True})
        if ok and not spec["setup"] and not any("reason" not in h for h in history):
            trace["passed_without_actions"] = True
        final["adjudication"] = adjudicate(page, jev, seen["name"], outcome_when(seen["name"]), secret_values)

    def end_with_outcome(page, step: dict, seen: dict, jev) -> None:
        """A non-pass outcome is terminal at first confident sighting (fail_fast): the picture is forced."""
        final["outcome"] = seen
        final["seen_at_step"] = final["first_seen_at_step"] = step["n"]
        step["outcome_seen"] = seen["name"]
        finish(page, step, "outcome", dict(STOP))
        final["adjudication"] = adjudicate(page, jev, seen["name"], outcome_when(seen["name"]), secret_values)

    timing: dict = {}  # where the wall-clock went: launch, navigation, setup, steps, final

    def lap(name: str, since: float) -> float:
        timing[name] = int((time.perf_counter() - since) * 1000)
        return time.perf_counter()

    def look() -> dict:
        """Observe the page with every secret value masked in what Jev and the trace will see."""
        return mask_secrets(observe(page, obs_cfg["max_elements"], obs_cfg["max_text_chars"]), secret_values)

    def final_page(checks: dict) -> dict:
        """trace.final for a run that ends without a fresh observation: url and title masked like a step's."""
        try:
            url, title = page.url, page.title()
        except Exception:  # noqa: BLE001 - the page is gone
            url, title = None, None
        return {"url": mask_text(url, secret_values), "title": mask_text(title, secret_values), "checks": checks}

    os.makedirs(os.path.join(out_dir, "steps"), exist_ok=True)  # before any tab is opened: nothing to close if it fails
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
        page.set_default_timeout(spec["browser"]["action_timeout_ms"])
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
                obs = look()
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
                questions, meta = build_questions(spec, obs, last_operation, outcomes, ask_stuck=last_page_changed is False)
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
                seen = seen_outcomes(outcomes, checks, outcome_answer, th["outcome_true"])
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
                    if passes:
                        settle_pass(page, step, obs, passes[0], was["action"], jev)
                        break
                    if was["action"] == "DONE":
                        finish(page, step, "done_unverified", {"action": "DONE", "ok": True, "error": None, "confirmed": True})
                        break
                    step["outcome_unconfirmed"] = was["name"]  # a transient sighting: carry on with this step's answers
                    final.pop("first_seen_at_step", None)  # it was not the first sighting of the pass

                def confirm_later(name: str | None, action: str, reason: str, entry_op: str) -> None:
                    nonlocal pending
                    pending = {"name": name, "action": action}
                    step["pending_outcome"] = name
                    if name:
                        final["first_seen_at_step"] = n  # the sighting; seen_at_step will be the confirming step
                    park(step, reason, wait_entry(n, entry_op, "checking the result before finishing"), sig)

                if passes and spec["auto_done"]:
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
                    low_streak += 1
                    stale_streak = 0  # a refused decision is not a stale one: `max_stale` counts consecutive stale steps
                    if low_streak >= th["max_low_confidence_steps"]:
                        finish(page, step, "low_confidence", dict(STOP))
                        break
                    park(step, f"low confidence; {operation} not executed",
                         wait_entry(n, "WAIT", "undecided between the offered options; nothing was executed"), sig)
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
                        finish(page, step, "stuck", dict(STOP))
                        break

                # The page Jev decided on, before anything changes it. The last allowed step is terminal
                # for the budget (the for-else below), so it gets its picture like every terminal step.
                capture(page, step, terminal=(n == budget["max_steps"]))
                t_b = time.perf_counter()
                executed = execute(page, spec, operation, target, value_key)
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
                note_page_change(sig)
                step = {
                    "n": n, "url": obs["url"], "title": obs["title"], "signature": sig, "screenshot": None,
                    "elements": obs["elements"], "truncated_elements": obs["truncated"],
                    "visible_text": obs["visible_text"][:600], "final_look": True, "offered_operations": [],
                }
                questions, meta = build_questions(spec, obs, last_operation, outcomes)
                last_look = {k: v for k, v in questions.items() if k in spec["checks"] or k in ("outcome", "blocked_reason")}
                checks, outcome_answer = {}, None
                try:
                    t_jev = time.perf_counter()
                    resp = jev.system_one(build_state(spec, obs, n, history), last_look)
                    step["latency_ms"] = {"jev": latency_of(resp, t_jev)}
                    checks = read_checks(resp["answers"], spec)
                    if "outcome" in last_look:
                        outcome_answer = read_outcome(resp["answers"], meta["offered"]["outcome"])
                        step["outcome"] = outcome_answer
                    step["blocked_reason"] = read_choice(resp["answers"], "blocked_reason", meta["offered"]["blocked_reason"])
                except JevError as e:
                    error = step["error"] = str(e)
                step["checks"] = checks
                seen = seen_outcomes(outcomes, checks, outcome_answer, th["outcome_true"])
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
    trace["timing"] = timing
    trace["actions_executed"] = sum(1 for s in trace["steps"] if is_action_step(s))
    trace["usage"] = jev.usage_summary()
    trace["adjudication"] = final.get("adjudication")
    result = build_result(trace, spec, outcomes, final, out_dir)
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
