"""Offline self-test for the runner: no API key, no network.

    python scripts/selftest.py

Serves a tiny local shop page from a temp file and replaces Jev with a rule-based stand-in that
answers the same question shapes. Exercises the terminal states: passed (auto-done on checks), never_violated (an error appeared),
blocked (needed data missing), low_confidence (Jev unsure which value to type: nothing gets typed),
plus the two DONE rules: a low-confidence DONE is a WAIT, and a confident DONE with unsatisfied
checks gets one settle-and-recheck before the verdict, and the answer validation: an operation
answer that fails validation is re-asked once (the run goes on), twice ends the run as error.
Also checks that a ./.env is loaded.
Run this after installing to confirm Playwright + Chromium work before spending TypeSafe credit.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

from run_test import run
from spec import load_dotenv
from summarize_trace import summarize

PAGE = """<!doctype html><html><head><title>Mini Shop</title>
<style>
 body{font-family:sans-serif;margin:24px}
 #banner{position:fixed;bottom:0;left:0;right:0;background:#333;color:#fff;padding:16px}
 .item{margin:8px 0}
</style></head><body>
<header><a href="#home">Home</a> &nbsp; <span id="cart">Cart: 0 items</span></header>
<h1>Mini Shop</h1>
<form id="search" onsubmit="event.preventDefault(); showResults();">
  <input id="q" placeholder="Search products">
  <button type="submit">Search</button>
</form>
<div id="results" hidden>
  <div class="item">Blue Hoodie <button onclick="addToCart()">Add to cart</button></div>
  <div class="item">Red Hoodie <button onclick="addToCart()">Add to cart</button></div>
</div>
<div id="error" hidden role="alert">Something went wrong. Please try again later.</div>
<div id="banner">We use cookies. <button onclick="document.getElementById('banner').remove()">Accept cookies</button></div>
<script>
 const FAIL = location.search.includes('fail=1');
 function showResults(){ document.getElementById('results').hidden = false; }
 let count = 0;
 const SLOW = location.search.includes('slow=1');
 function addToCart(){
   if (FAIL) { document.getElementById('error').hidden = false; return; }
   count++;
   const paint = () => { document.getElementById('cart').textContent = 'Cart: ' + count + ' items'; };
   if (SLOW) setTimeout(paint, 250); else paint();
 }
</script></body></html>"""


# Real-world checkbox patterns that hid from earlier observers: antd (opacity-0 input over a styled span,
# inside a cursor:pointer row), Bootstrap (input parked offscreen, label is the target), MUI (styled svg
# over the input), plus one genuinely hidden sr-only input that must stay out of the table.
CONTROLS_PAGE = """<!doctype html><html><head><title>Controls</title><style>
 tr.ant-table-row{cursor:pointer}
 td{padding:6px 12px;border-bottom:1px solid #eee}
 .ant-checkbox-wrapper{cursor:pointer;display:inline-flex}
 .ant-checkbox{position:relative;display:inline-block;width:16px;height:16px}
 .ant-checkbox-input{position:absolute;inset:0;z-index:1;width:100%;height:100%;cursor:pointer;opacity:0;margin:0}
 .ant-checkbox-inner{position:relative;display:block;width:16px;height:16px;border:1px solid #d9d9d9;border-radius:4px;background:#fff}
 .ant-checkbox-checked .ant-checkbox-inner{background:#1677ff}
 /* Bootstrap-style: input parked offscreen, label is the click target */
 .custom-control-input{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}
 .custom-control-label{cursor:pointer;padding-left:24px;position:relative;display:inline-block}
 .custom-control-label::before{content:"";position:absolute;left:0;top:2px;width:16px;height:16px;border:1px solid #999}
 /* MUI-style: styled span on top, input underneath covering the box, pointer-events on span */
 .mui-box{position:relative;display:inline-flex;width:20px;height:20px}
 .mui-box svg{position:absolute;inset:0;z-index:1}
 .mui-box input{position:absolute;inset:0;width:100%;height:100%;opacity:0;margin:0;cursor:pointer}
 .sr-only{position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;clip:rect(0,0,0,0)}
</style></head><body>
<table><tbody>
<tr class="ant-table-row"><td><label class="ant-checkbox-wrapper"><span class="ant-checkbox"><input class="ant-checkbox-input" type="checkbox"><span class="ant-checkbox-inner"></span></span></label></td>
    <td><a href="#c1">1000-04-660L</a></td><td>Cardboard 660L</td><td>Provas2 Depot</td></tr>
<tr class="ant-table-row"><td><label class="ant-checkbox-wrapper"><span class="ant-checkbox"><input class="ant-checkbox-input" type="checkbox"><span class="ant-checkbox-inner"></span></span></label></td>
    <td><a href="#c2">1000-05-1100L</a></td><td>Residual 1100L</td><td>Nile Bakery</td></tr>
</tbody></table>
<div><input type="checkbox" class="custom-control-input" id="terms"><label class="custom-control-label" for="terms">I accept the terms</label></div>
<div><span class="mui-box"><svg viewBox="0 0 20 20"><rect x="2" y="2" width="16" height="16" fill="none" stroke="#666"/></svg><input type="checkbox" aria-label="Notify me"></span></div>
<input type="checkbox" class="sr-only" aria-label="genuinely hidden, should NOT appear">
<button>Continue</button>
</body></html>
"""


SETTLE_PAGE = """<!doctype html><html><head><title>Settle</title></head><body>
<button id="burst" onclick="burst()">Burst</button>
<button id="forever" onclick="forever()">Forever</button>
<input id="cb" role="combobox" aria-label="Product" oninput="suggest()">
<ul id="list" role="listbox"></ul>
<div id="counter">0</div>
<script>
 let n = 0;
 const paint = () => { document.getElementById('counter').textContent = ++n; };
 function burst(){ const t = setInterval(paint, 20); setTimeout(() => clearInterval(t), 150); }
 function forever(){ setInterval(paint, 20); }
 function suggest(){ setTimeout(() => {
   const li = document.createElement('li'); li.setAttribute('role', 'option'); li.textContent = 'Blue Hoodie';
   document.getElementById('list').appendChild(li); }, 120); }
</script></body></html>"""


def settle_check(url: str) -> list[str]:
    """settle() ends on DOM quiet, on the cap, or on a visible autocomplete option. No Jev involved."""
    from playwright.sync_api import sync_playwright
    from run_test import settle
    from spec import DEFAULTS, _merge

    failures = []

    def sp(cap: int, quiet: int) -> dict:
        return _merge(DEFAULTS, {"id": "settle", "start_url": url, "goal": "x", "browser": {"settle_ms": cap, "quiet_ms": quiet}})

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 800, "height": 600})
        pg.goto(url)
        pg.click("#burst")  # mutates every 20 ms for 150 ms, then stops
        r1 = settle(pg, sp(1000, 50))
        if r1["ended"] != "quiet" or not (150 <= r1["ms"] < 800):
            failures.append(f"settle after a 150 ms burst should end quiet at >= 150 ms and well under the cap: {r1}")
        pg.click("#forever")  # never stops mutating
        r2 = settle(pg, sp(300, 50))
        if r2["ended"] != "cap" or not (280 <= r2["ms"] <= 700):
            failures.append(f"settle on a never-quiet page should end at the cap (300 ms): {r2}")
        pg.goto(url)  # a fresh document: no interval running
        pg.fill("#cb", "blu")  # the option appears 120 ms later
        r3 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "combobox"))
        visible = pg.locator('[role="option"]').count()
        if r3["ended"] != "options" or not (120 <= r3["ms"] < 600) or visible != 1:
            failures.append(f"settle after typing into a combobox should wait for the option: {r3}, options visible={visible}")
        r4 = settle(pg, sp(1000, 50))  # a plain settle right after: nothing changes, quiet within ~quiet_ms
        if r4["ended"] != "quiet" or r4["ms"] >= 400:
            failures.append(f"a quiet page should settle in about quiet_ms: {r4}")
        b.close()
    print(f"settle check: burst={r1} forever={r2} combobox={r3} quiet={r4}")
    print()
    return failures


def observer_check(url: str) -> list[str]:
    """Observation + execution sanity on CONTROLS_PAGE. No Jev involved."""
    from playwright.sync_api import sync_playwright
    from observe import observe
    from run_test import execute
    from spec import DEFAULTS, _merge

    failures = []
    sp = _merge(DEFAULTS, {"id": "obs", "start_url": url, "goal": "x", "checks": {}, "done_when": [],
                           "browser": {"action_timeout_ms": 1500, "settle_ms": 50, "quiet_ms": 20}})
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(url)
        pg.evaluate("() => { window.changes = 0; document.addEventListener('change', () => window.changes++); }")
        obs = observe(pg)
        boxes = [e for e in obs["elements"] if e["role"] == "checkbox"]
        if len(boxes) != 4:
            failures.append(f"expected 4 checkboxes in the table, got {len(boxes)}: {[e['name'] for e in boxes]}")
        if not any("Nile Bakery" in (e.get("context") or "") for e in boxes):
            failures.append("antd row checkbox has no row context")
        if not any(e["name"] == "I accept the terms" for e in boxes):
            failures.append("offscreen-input label not offered as a checkbox")
        if any("genuinely hidden" in e["name"] for e in obs["elements"]):
            failures.append("sr-only input leaked into the table")
        if any(e.get("value") == "on" for e in boxes):
            failures.append("checkbox value noise")
        for key in ("Notify me", "Nile Bakery", "terms"):
            e = next((e for e in boxes if key in e["name"] or key in (e.get("context") or "")), None)
            if not e:
                continue
            res = execute(pg, sp, "CLICK", {"element": e["idx"], "choice": str(e["idx"]), "label": e["name"], "confidence": 1.0}, None)
            if not res["ok"]:
                failures.append(f"click on checkbox '{key}' failed: {res['error']}")
        states = pg.evaluate("() => Array.from(document.querySelectorAll('input[type=checkbox]')).map(c => +c.checked).join('')")
        changes = pg.evaluate("() => window.changes")
        if states != "01110" or changes != 3:
            failures.append(f"checkbox clicks did not toggle the right inputs: states={states} change_events={changes}")
        b.close()
    print(f"observer check: {len(obs['elements'])} elements, checkboxes={len(boxes)}, states={states}, change_events={changes}")
    print()
    return failures


class FakeJev:
    """Rule-based stand-in for Jev. Answers exactly the shapes the real API returns."""

    def __init__(self, mode: str = "normal") -> None:
        # normal | hedge_value | early_low_done | early_confident_done | done_after_add
        # | invalid_operation_once | invalid_operation_always
        self.mode = mode
        self.requests = 0
        self.op_requests = 0
        self.seen_states: list[dict] = []

    def _choice(self, label: str, options: dict, conf: float = 0.9) -> dict:
        """A Choice answer that passes policy.validate_choice: `label` carries the top probability,
        the rest is spread evenly. Like the real API, `confidence` is a concentration measure rather
        than the top probability, so a hedged answer (low conf) still keeps `label` narrowly on top."""
        others = [k for k in options if k != label]
        top = max(conf, 1 / len(options) + 0.01) if others else 1.0
        probs = {k: (1 - top) / len(others) for k in others}
        probs[label] = top
        return {"type": "choice", "choice": label, "confidence": conf, "probabilities": probs}

    @staticmethod
    def _find(options: dict, needle: str) -> str | None:
        """First option whose description (a string, or any string inside an object) mentions `needle`."""
        for k, v in options.items():
            text = v if isinstance(v, str) else " ".join(str(x) for x in v.values()) if isinstance(v, dict) else str(v)
            if needle.lower() in text.lower():
                return k
        return None

    def system_one(self, state: dict, questions: dict) -> dict:
        self.requests += 1
        self.seen_states.append(state)
        text = state["visible_text"]
        answers: dict = {}
        for key, q in questions.items():
            if q["type"] == "noul":
                if key == "cart_has_item":
                    answers[key] = {"type": "noul", "noul": 1.0 if re.search(r"Cart: [1-9]", text) else 0.02}
                elif key == "error_visible":
                    answers[key] = {"type": "noul", "noul": 0.98 if "Something went wrong" in text else 0.01}
                else:
                    answers[key] = {"type": "noul", "noul": 0.5}
        if "operation" not in questions:
            return {"answers": answers, "usage": {"input_tokens": 300, "output_tokens": 20}, "model": "fake-jev", "latency_ms": 1}

        ops = questions["operation"]["criteria"]
        self.op_requests += 1
        usage = {"input_tokens": 400, "output_tokens": 60}
        # Scripted deviations that reproduce failure modes seen in real runs.
        if self.mode == "early_low_done" and self.op_requests == 1:
            answers["operation"] = self._choice("DONE", ops, conf=0.3)      # "I think we're done?" (run C, 0.36)
            return {"answers": answers, "usage": usage, "model": "fake-jev", "latency_ms": 1}
        if self.mode == "early_confident_done" and self.op_requests == 1:
            answers["operation"] = self._choice("DONE", ops, conf=0.9)      # confidently wrong
            return {"answers": answers, "usage": usage, "model": "fake-jev", "latency_ms": 1}
        recent = state["recent_actions"]
        if self.mode == "done_after_add" and any("Add to cart" in (a.get("target") or "") for a in recent):
            answers["operation"] = self._choice("DONE", ops, conf=0.9)      # right, but the page is still painting
            return {"answers": answers, "usage": usage, "model": "fake-jev", "latency_ms": 1}
        clicks = questions.get("click_target", {}).get("criteria", {})
        types = questions.get("type_target", {}).get("criteria", {})
        results_shown = self._find(clicks, "Add to cart") is not None
        typed_before = any(a["operation"] == "TYPE_TEXT" for a in recent)
        search_box_visible = any(e["label"] == "Search products" for e in state["elements"])

        if self._find(clicks, "Accept cookies"):
            op, target = "CLICK", ("click_target", self._find(clicks, "Accept cookies"))
        elif not results_shown and self._find(types, "Search products") and not typed_before and "TYPE_TEXT" in ops:
            op, target = "TYPE_TEXT", ("type_target", self._find(types, "Search products"))
            value_conf = 0.36 if self.mode == "hedge_value" else 0.9   # run A: username 0.68 / password 0.32
            answers["type_value"] = self._choice("search_query", questions["type_value"]["criteria"], conf=value_conf)
        elif not results_shown and search_box_visible and "TYPE_TEXT" not in ops:
            op, target = "BLOCKED", None  # wants to type but no data value was prepared
        elif "PRESS_ENTER" in ops and not results_shown:
            op, target = "PRESS_ENTER", None
        elif results_shown:
            op, target = "CLICK", ("click_target", self._find(clicks, "Add to cart"))
        else:
            op, target = "DONE", None

        answers["operation"] = self._choice(op, ops)
        if self.mode == "invalid_operation_always" or (self.mode == "invalid_operation_once" and self.op_requests == 1):
            answers["operation"]["choice"] = "FLY"  # a well-formed distribution, but the pick was never offered
        if target:
            qkey, label = target
            answers[qkey] = self._choice(label, questions[qkey]["criteria"])
        return {"answers": answers, "usage": {"input_tokens": 400, "output_tokens": 60}, "model": "fake-jev", "latency_ms": 1}

    def usage_summary(self) -> dict:
        return {"jev_requests": self.requests, "input_tokens": 400 * self.requests, "output_tokens": 60 * self.requests, "model": "fake-jev"}


STATE_KEYS = ["goal", "hints", "step", "page", "elements", "truncated_elements", "visible_text",
              "available_data_values", "recent_actions"]


def state_shape_check(state: dict, trace: dict) -> list[str]:
    """The structured state of the last request of the happy path, and page_changed on the trace."""
    failures = []
    if list(state) != STATE_KEYS:
        failures.append(f"state keys are {list(state)}, expected {STATE_KEYS}")
    if state.get("step") != {"n": len(trace["steps"]), "max": 10}:
        failures.append(f"state.step is {state.get('step')}")
    els = state.get("elements") or []
    if not els or not all(isinstance(e.get("index"), int) and isinstance(e.get("operations"), list) for e in els):
        failures.append(f"state.elements is not a list of {{index:int, operations:list}} records: {els[:2]}")
    if not any(e["label"] == "Home" and e["role"] == "link" and e["operations"] == ["CLICK"] for e in els):
        failures.append(f"the Home link is not described with operations [CLICK]: {[e for e in els if e['label'] == 'Home']}")
    if state.get("available_data_values") != [{"key": "search_query", "value": "blue hoodie"}, {"key": "password", "value": "<secret>"}]:
        failures.append(f"available_data_values wrong: {state.get('available_data_values')}")
    recent = state.get("recent_actions") or []
    by_op = {a["operation"]: a for a in recent}
    if set(by_op) != {"CLICK", "TYPE_TEXT", "PRESS_ENTER"}:
        failures.append(f"recent_actions do not cover the executed operations: {recent}")
    click = next((a for a in recent if "Add to cart" in (a.get("target") or "")), None)
    if not click or click.get("page_changed") is not True or click.get("ok") is not True or click.get("value_key") is not None:
        failures.append(f"the Add-to-cart entry lacks page_changed/ok: {click}")
    typed = by_op.get("TYPE_TEXT") or {}
    if typed.get("value_key") != "search_query" or typed.get("page_changed") is not True:
        failures.append(f"the TYPE_TEXT entry lacks value_key/page_changed: {typed}")
    steps = {s["n"]: s for s in trace["steps"]}
    if steps.get(click["step"], {}).get("page_changed") is not True if click else True:
        failures.append("the trace step for the click does not carry page_changed true")
    if "page_changed" in trace["steps"][-1]:
        failures.append("the terminal step has a page_changed (no action followed it)")
    return failures


def base_spec(url: str) -> dict:
    from spec import DEFAULTS, _merge, validate

    spec = _merge(
        DEFAULTS,
        {
            "id": "selftest",
            "start_url": url,
            "goal": "Search for a blue hoodie and add it to the cart.",
            "notes": "Accept the cookie banner first if it is shown.",
            "data": {"search_query": "blue hoodie", "password": "hunter2-not-real"},
            "secrets": ["password"],
            "checks": {
                "cart_has_item": "The header shows the cart contains at least one item",
                "error_visible": "An error message such as 'something went wrong' is visible",
            },
            "done_when": ["cart_has_item"],
            "never": ["error_visible"],
            "budget": {"max_steps": 10, "max_seconds": 60},
            # cap 300 / quiet 50: the ?slow=1 fixture paints 250 ms after the click, so the DONE
            # confirmation (a settle_ms pause, then settle) must still see it
            "browser": {"settle_ms": 300, "quiet_ms": 50},
        },
    )
    problems = validate(spec)
    assert not problems, problems
    return spec


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="jev-selftest-")
    html = os.path.join(tmp, "shop.html")
    with open(html, "w", encoding="utf-8") as f:
        f.write(PAGE)
    url = "file://" + html
    controls = os.path.join(tmp, "controls.html")
    with open(controls, "w", encoding="utf-8") as f:
        f.write(CONTROLS_PAGE)
    settle_html = os.path.join(tmp, "settle.html")
    with open(settle_html, "w", encoding="utf-8") as f:
        f.write(SETTLE_PAGE)
    failures = []

    # 0. observer: hidden-input checkboxes are seen, described with their row, and clickable
    failures += observer_check("file://" + controls)
    # 0b. settle: ends on DOM quiet, on the cap, or on a visible autocomplete option
    failures += settle_check("file://" + settle_html)

    # 1. happy path -> passed via auto_done
    spec = base_spec(url)
    jev = FakeJev()
    out = os.path.join(tmp, "run-pass")
    trace = run(spec, jev, out, screenshots=True)
    print(summarize(trace, out))
    print()
    ops = [s.get("executed", {}).get("action") for s in trace["steps"]]
    if trace["status"] != "passed":
        failures.append(f"expected passed, got {trace['status']} ({trace.get('error')})")
    if ops != ["CLICK", "TYPE_TEXT", "PRESS_ENTER", "CLICK", "AUTO_DONE"]:
        failures.append(f"unexpected action sequence {ops}")
    if trace["spec"]["data"]["password"] != "<secret>":
        failures.append("secret not redacted in trace spec")
    if any("hunter2" in json.dumps(st) for st in jev.seen_states):
        failures.append("secret value leaked into Jev state")
    if not os.path.exists(os.path.join(out, "steps", "001.png")):
        failures.append("screenshot missing")
    if not os.path.exists(os.path.join(out, "trace.json")):
        failures.append("trace.json missing")
    failures += state_shape_check(jev.seen_states[-1], trace)
    settles = [s.get("settle") for s in trace["steps"] if (s.get("executed") or {}).get("action") == "CLICK"]
    if not settles or not all(isinstance(s, dict) and s.get("ended") in ("quiet", "cap") and isinstance(s.get("ms"), int) for s in settles):
        failures.append(f"action steps do not carry a settle record: {settles}")

    # 2. the app shows an error -> never_violated
    spec = base_spec(url + "?fail=1")
    out = os.path.join(tmp, "run-error")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "never_violated":
        failures.append(f"expected never_violated, got {trace['status']} ({trace.get('error')})")

    # 3. needed data missing -> blocked
    spec = base_spec(url)
    spec["data"] = {}
    spec["secrets"] = []
    out = os.path.join(tmp, "run-blocked")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "blocked":
        failures.append(f"expected blocked, got {trace['status']} ({trace.get('error')})")

    # 4. Jev unsure WHICH value to type -> nothing is typed, run ends low_confidence (was: typed anyway)
    spec = base_spec(url)
    out = os.path.join(tmp, "run-hedge-value")
    trace = run(spec, FakeJev("hedge_value"), out, screenshots=False)
    print(summarize(trace, out))
    print()
    ops = [s.get("executed", {}).get("action") for s in trace["steps"]]
    if trace["status"] != "low_confidence":
        failures.append(f"expected low_confidence, got {trace['status']} ({trace.get('error')})")
    if "TYPE_TEXT" in ops or trace["actions_executed"] != 1:
        failures.append(f"a low-confidence value choice was executed: {ops}")

    # 5. a low-confidence DONE is a WAIT, not a verdict -> the flow continues and passes
    spec = base_spec(url)
    out = os.path.join(tmp, "run-early-low-done")
    trace = run(spec, FakeJev("early_low_done"), out, screenshots=False)
    print(summarize(trace, out))
    print()
    ops = [s.get("executed", {}).get("action") for s in trace["steps"]]
    if trace["status"] != "passed" or ops[:2] != ["WAIT", "CLICK"]:
        failures.append(f"low-confidence DONE was terminal: {trace['status']} {ops}")

    # 6. confident DONE while the page is still updating -> confirmation pass -> passed (run C race)
    spec = base_spec(url + "?slow=1")
    out = os.path.join(tmp, "run-done-race")
    trace = run(spec, FakeJev("done_after_add"), out, screenshots=False)
    print(summarize(trace, out))
    print()
    ops = [s.get("executed", {}).get("action") for s in trace["steps"]]
    if trace["status"] != "passed" or ops[-2:] != ["WAIT", "DONE"] or not trace["steps"][-1]["executed"].get("confirmed"):
        failures.append(f"DONE race not recovered by confirmation pass: {trace['status']} {ops}")

    # 7. confident DONE and the checks really are unsatisfied -> done_unverified after one recheck
    spec = base_spec(url)
    out = os.path.join(tmp, "run-done-unverified")
    trace = run(spec, FakeJev("early_confident_done"), out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "done_unverified" or len(trace["steps"]) != 2:
        failures.append(f"expected done_unverified in 2 steps, got {trace['status']} in {len(trace['steps'])}")

    # 8. an operation answer that fails validation is re-asked once; the retry answers well -> the run passes
    spec = base_spec(url)
    jev = FakeJev("invalid_operation_once")
    out = os.path.join(tmp, "run-invalid-op-once")
    trace = run(spec, jev, out, screenshots=False)
    print(summarize(trace, out))
    print()
    first = trace["steps"][0]
    if trace["status"] != "passed":
        failures.append(f"expected passed after one retried operation answer, got {trace['status']} ({trace.get('error')})")
    if not first.get("retried") or not str(first.get("invalid_answer", "")).startswith("operation: choice 'FLY'"):
        failures.append(f"step 1 not marked retried/invalid_answer: {first.get('retried')} {first.get('invalid_answer')!r}")
    if jev.requests != len(trace["steps"]) + 1:
        failures.append(f"expected exactly one extra request for the retry, got {jev.requests} for {len(trace['steps'])} steps")
    if any(s.get("retried") or s.get("invalid_answer") for s in trace["steps"][1:]):
        failures.append("later steps carry retried/invalid_answer flags")
    if first["latency_ms"]["jev"] != 2:
        failures.append(f"retry latency not summed into the step: {first['latency_ms']}")

    # 9. still invalid after the retry -> error, and exactly two requests were made for the step
    spec = base_spec(url)
    jev = FakeJev("invalid_operation_always")
    out = os.path.join(tmp, "run-invalid-op-always")
    trace = run(spec, jev, out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "error" or "invalid operation answer" not in (trace.get("error") or ""):
        failures.append(f"expected error 'invalid operation answer', got {trace['status']} ({trace.get('error')})")
    if jev.requests != 2 or len(trace["steps"]) != 1:
        failures.append(f"expected 2 requests for a single step, got {jev.requests} requests, {len(trace['steps'])} steps")
    if trace["steps"][0].get("executed", {}).get("action") != "STOP":
        failures.append(f"invalid-operation stop not recorded as STOP: {trace['steps'][0].get('executed')}")
    if trace["actions_executed"] != 0:
        failures.append("an unvalidated operation answer was counted as an action")

    # 10. .env in the working directory is loaded; already-exported variables win; quotes are stripped
    env_dir = os.path.join(tmp, "dotenv")
    os.makedirs(env_dir)
    with open(os.path.join(env_dir, ".env"), "w", encoding="utf-8") as f:
        f.write("# comment\n\nSELFTEST_PLAIN=abc\nexport SELFTEST_EXPORTED='quoted value'\n"
                "SELFTEST_PRESET=from-file\nnot a variable line\n")
    os.environ["SELFTEST_PRESET"] = "from-shell"
    for name in ("SELFTEST_PLAIN", "SELFTEST_EXPORTED"):
        os.environ.pop(name, None)
    loaded = load_dotenv(os.path.join(env_dir, ".env"))
    if sorted(loaded) != ["SELFTEST_EXPORTED", "SELFTEST_PLAIN"]:
        failures.append(f".env loaded unexpected names: {loaded}")
    if os.environ.get("SELFTEST_PLAIN") != "abc" or os.environ.get("SELFTEST_EXPORTED") != "quoted value":
        failures.append(".env values not loaded or quotes not stripped")
    if os.environ.get("SELFTEST_PRESET") != "from-shell":
        failures.append(".env overrode a variable that was already exported")
    if load_dotenv(os.path.join(env_dir, "missing.env")) != []:
        failures.append("a missing .env should load nothing")
    print("dotenv: loaded", loaded, "| preset kept:", os.environ["SELFTEST_PRESET"])
    print()

    if failures:
        print("SELFTEST FAILED:")
        for fmsg in failures:
            print("  -", fmsg)
        return 1
    print(f"SELFTEST OK (artifacts in {tmp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
