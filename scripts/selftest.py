"""Offline self-test for the runner: no API key, no network.

    python scripts/selftest.py

Serves a tiny local shop page from a temp file and replaces Jev with a rule-based stand-in that
answers the same question shapes. Exercises the terminal states: passed (auto-done on checks), never_violated (an error appeared),
blocked (needed data missing), low_confidence (Jev unsure which value to type: nothing gets typed),
plus the two DONE rules: a low-confidence DONE is a WAIT, and a confident DONE with unsatisfied
checks gets one settle-and-recheck before the verdict, and the answer validation: an operation
answer that fails validation is re-asked once (the run goes on), twice ends the run as error.
The freshness guard is exercised with a slow fake Jev: a target that changes during the decision
makes the step stale (nothing executed, re-observe, the run still passes) and a page that never
holds still ends as unstable_page. The screenshot policy is checked in all three modes (every step,
"key" = terminal and flagged steps only, none). Also checks that a ./.env is loaded.
Run this after installing to confirm Playwright + Chromium work before spending TypeSafe credit.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time

from run_test import run
from spec import load_dotenv
from summarize_trace import summarize

PAGE = """<!doctype html><html><head><title>Mini Shop</title>
<style>
 body{font-family:sans-serif;margin:24px}
 #banner{position:fixed;bottom:0;left:0;right:0;background:#333;color:#fff;padding:16px}
 .item{margin:8px 0}
</style></head><body>
<div id="filler" style="position:absolute;top:3000px;left:0;width:600px" hidden></div>
<header><a href="#home">Home</a> &nbsp; <span id="cart">Cart: 0 items</span> &nbsp;
  <button id="apply" onclick="void 0">Apply filter</button> &nbsp; <a id="help" href="#help" target="_blank">Help</a></header>
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
 const STALE_ONCE = location.search.includes('stale_once=1');
 function showResults(){
   document.getElementById('results').hidden = false;
   if (STALE_ONCE) {
     // The first "Add to cart" button goes disabled 200 ms after the results appear (long after the
     // observation, well before a 400 ms decision lands) and comes back 2 s later.
     const first = document.querySelector('#results button');
     setTimeout(() => { first.disabled = true; }, 200);
     setTimeout(() => { first.disabled = false; }, 2000);
   }
 }
 if (location.search.includes('longtext=1')) {
   // 5,000+ chars that come FIRST in DOM order but sit far below the fold: viewport-first text must put
   // what is on screen before them, and keep them after it.
   const f = document.getElementById('filler');
   f.textContent = 'Lorem ipsum filler sentence number ' + Array.from({length: 600}, (_, i) => i).join(' lorem ') + '.';
   f.hidden = false;
   // ... and 600+ chars of whitespace-padded in-view text nodes (pretty-printed HTML), so the 500-char
   // text head is cut inside the in-view part: it must still be a prefix of the 4,000-char text.
   const ul = document.createElement('ul');
   ul.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;list-style:none;padding:0;margin:4px 0';  // wraps: stays in view
   for (let i = 0; i < 80; i++) { const li = document.createElement('li'); li.textContent = '\\n   item ' + i + '  \\n'; ul.appendChild(li); }
   document.getElementById('results').before(ul);
 }
 if (location.search.includes('unstable=1')) {
   // The cookie banner's text changes every 70 ms, so the Accept button's surroundings never hold still.
   let tick = 0;
   setInterval(() => { document.getElementById('banner').firstChild.textContent = 'We use cookies (' + (++tick) + '). '; }, 70);
 }
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
    <td><a href="#c1">SKU-1004</a></td><td>Widget 12-pack</td><td>Warehouse A</td></tr>
<tr class="ant-table-row"><td><label class="ant-checkbox-wrapper"><span class="ant-checkbox"><input class="ant-checkbox-input" type="checkbox"><span class="ant-checkbox-inner"></span></span></label></td>
    <td><a href="#c2">SKU-1005</a></td><td>Gadget 6-pack</td><td>Acme Ltd</td></tr>
</tbody></table>
<div><input type="checkbox" class="custom-control-input" id="terms"><label class="custom-control-label" for="terms">I accept the terms</label></div>
<div><span class="mui-box"><svg viewBox="0 0 20 20"><rect x="2" y="2" width="16" height="16" fill="none" stroke="#666"/></svg><input type="checkbox" aria-label="Notify me"></span></div>
<input type="checkbox" class="sr-only" aria-label="genuinely hidden, should NOT appear">
<button>Continue</button>
<form id="fields" style="margin-top:12px">
  <label for="u" style="cursor:pointer">Username</label> <input id="u" type="text">
  <input type="search" placeholder="Find">
  <input list="dl" placeholder="Pick"><datalist id="dl"><option value="A"></option></datalist>
  <input type="submit" value="Send">
  <textarea aria-label="Notes">hello there</textarea>
  <div contenteditable="true" aria-label="Editor" style="border:1px solid #ccc;display:inline-block;min-width:80px">draft</div>
  <select aria-label="Grouped"><option>open-1</option><optgroup label="Closed" disabled><option>closed-1</option></optgroup></select>
</form>
<details><summary>Show error</summary>Payment failed: card declined</details>
</body></html>
"""


SETTLE_PAGE = """<!doctype html><html><head><title>Settle</title></head><body>
<button id="burst" onclick="burst()">Burst</button>
<button id="forever" onclick="forever()">Forever</button>
<input id="cb" role="combobox" aria-label="Product" oninput="suggest()">
<ul id="list" role="listbox"></ul>
<input id="sb" role="searchbox" aria-label="Find">
<ul role="listbox" id="sidebar"><li role="option">Always shown</li></ul>
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
        pg.fill("#cb", "blu")  # the option appears 120 ms later; the sidebar's permanent option must not count
        r3 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "combobox"))
        visible = pg.locator('#list [role="option"]').count()
        if r3["ended"] != "options" or not (120 <= r3["ms"] < 600) or visible != 1:
            failures.append(f"settle after typing into a combobox should wait for a NEW option: {r3}, options visible={visible}")
        r4 = settle(pg, sp(1000, 50))  # a plain settle right after: nothing changes, quiet within ~quiet_ms
        if r4["ended"] != "quiet" or r4["ms"] >= 400:
            failures.append(f"a quiet page should settle in about quiet_ms: {r4}")
        pg.fill("#sb", "xyz")  # a searchbox that never produces suggestions: give up after 200 ms
        r5 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "searchbox"))
        if r5["ended"] != "options_timeout" or not (200 <= r5["ms"] < 500):
            failures.append(f"typing into a searchbox with no suggestions should end options_timeout at ~200 ms: {r5}")
        b.close()
    print(f"settle check: burst={r1} forever={r2} combobox={r3} quiet={r4} no-suggestions={r5}")
    print()
    return failures


def cdp_check(url: str, tmp: str) -> list[str]:
    """browser.cdp_url attaches to a browser we did not launch, runs the flow in a new tab and closes only that tab."""
    import socket
    import subprocess
    import urllib.request
    from playwright.sync_api import sync_playwright

    failures = []
    with sync_playwright() as p:
        chromium = p.chromium.executable_path
    with socket.socket() as s:  # a free port: reviewers run selftests concurrently
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"

    def pages() -> list[dict]:
        with urllib.request.urlopen(f"{endpoint}/json/list", timeout=2) as resp:
            return [t for t in json.load(resp) if t.get("type") == "page"]

    proc = subprocess.Popen(
        [chromium, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={os.path.join(tmp, 'cdp-profile')}",
         "--no-first-run", "--no-default-browser-check",
         # Playwright passes these when it launches Chromium itself; without them a fresh profile asks
         # macOS for the keychain ("Chromium Safe Storage") to encrypt cookies, a password prompt per run.
         "--use-mock-keychain", "--password-store=basic",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        before: list[dict] | None = None
        for _ in range(100):  # the debugging endpoint needs a moment to come up
            try:
                listed = pages()
            except Exception:  # noqa: BLE001
                listed = []
            # Ready means the endpoint answers AND lists a page: the DevTools server starts answering a few
            # ms before the initial about:blank target exists, and a snapshot taken in that gap is [].
            if listed:
                before = listed
                break
            time.sleep(0.1)
        if before is None:
            return [f"could not reach the remote-debugging endpoint at {endpoint} (or it listed no tab)"]
        spec = base_spec(url)
        spec["browser"]["cdp_url"] = endpoint
        spec["browser"]["storage_state"] = os.path.join(tmp, "ignored-state.json")  # must be ignored, not opened
        spec["setup"] = [{"action": "click", "selector": "#help"}]  # opens a second tab: the run must close it too
        out = os.path.join(tmp, "run-cdp")
        trace = run(spec, FakeJev(), out, screenshots=False)
        print(summarize(trace, out))
        print()
        after = pages()
        if trace["status"] != "passed":
            failures.append(f"cdp: expected passed, got {trace['status']} ({trace.get('error')})")
        if trace.get("browser") != {"attached": True, "cdp_url": endpoint, "storage_state_ignored": True}:
            failures.append(f"cdp: trace.browser is {trace.get('browser')}")
        if proc.poll() is not None:
            failures.append("cdp: the attached browser was killed by the run")
        if len(after) != len(before) or {t["id"] for t in after} != {t["id"] for t in before}:
            failures.append(f"cdp: the browser's own tabs changed: before={[t['url'] for t in before]} after={[t['url'] for t in after]}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # A browser nobody runs at that address is an environment problem: run() raises BrowserUnavailable
    # before anything is traced, and the CLI turns that into exit 2 with a hint, not a traceback.
    from run_test import BrowserUnavailable, main as run_main
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
    dead = f"http://127.0.0.1:{closed_port}"
    spec = base_spec(url)
    spec["browser"]["cdp_url"] = dead
    out = os.path.join(tmp, "run-cdp-dead")
    try:
        run(spec, FakeJev(), out, screenshots=False)
        failures.append("cdp: an unreachable cdp_url did not raise BrowserUnavailable")
    except BrowserUnavailable as e:
        if dead not in str(e) or "remote-debugging-port" not in str(e):
            failures.append(f"cdp: BrowserUnavailable should name the url and the hint: {e}")
    if os.path.exists(out):
        failures.append("cdp: an unreachable browser left a run directory behind")
    spec_path = os.path.join(tmp, "dead-cdp-spec.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in base_spec(url).items()}, f)
    os.environ.setdefault("TYPESAFE_API_KEY", "selftest-dummy-key-never-sent")  # the browser fails first, no request is made
    code = run_main(["run_test.py", spec_path, "--cdp-url", dead, "--out", os.path.join(tmp, "run-cdp-dead-cli")])
    if code != 2:
        failures.append(f"cdp: the CLI should exit 2 for an unreachable browser, got {code}")
    print(f"cdp: unreachable {dead} -> BrowserUnavailable, CLI exit {code}")
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
        if not any("Acme Ltd" in (e.get("context") or "") for e in boxes):
            failures.append("antd row checkbox has no row context")
        if not any(e["name"] == "I accept the terms" for e in boxes):
            failures.append("offscreen-input label not offered as a checkbox")
        if any("genuinely hidden" in e["name"] for e in obs["elements"]):
            failures.append("sr-only input leaked into the table")
        if any(e.get("value") == "on" for e in boxes):
            failures.append("checkbox value noise")
        for key in ("Notify me", "Acme Ltd", "terms"):
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

        # Fields and their descriptions: a label whose control is in the table is not a clickable; implicit
        # roles for search / datalist inputs; a submit's caption is its name, not a value; a textarea and a
        # contenteditable carry their content as value and no `text`; a disabled optgroup disables its options.
        by_name = {e["name"]: e for e in obs["elements"]}
        if any(e["name"] == "Username" and e["via"] == "cursor" for e in obs["elements"]) or by_name.get("Username", {}).get("role") != "textbox":
            failures.append(f"the label of an offered text field must not be a clickable: {[(e['role'], e['via']) for e in obs['elements'] if e['name'] == 'Username']}")
        if by_name.get("Find", {}).get("role") != "searchbox" or by_name.get("Pick", {}).get("role") != "combobox":
            failures.append(f"implicit roles: search={by_name.get('Find', {}).get('role')} list={by_name.get('Pick', {}).get('role')}")
        if by_name.get("Send", {}).get("role") != "submit" or by_name.get("Send", {}).get("value") is not None:
            failures.append(f"a submit input should be named by its caption and carry no value: {by_name.get('Send')}")
        if by_name.get("Notes", {}).get("value") != "hello there" or by_name.get("Notes", {}).get("text") is not None:
            failures.append(f"a textarea should carry its content as value only: {by_name.get('Notes')}")
        if by_name.get("Editor", {}).get("value") != "draft" or by_name.get("Editor", {}).get("text") is not None or by_name.get("Editor", {}).get("role") != "textbox":
            failures.append(f"a contenteditable should be a textbox with its content as value: {by_name.get('Editor')}")
        grouped = by_name.get("Grouped", {}).get("options") or []
        if [o["disabled"] for o in grouped] != [False, True]:
            failures.append(f"options inside a disabled optgroup should be disabled: {grouped}")
        if "Show error" not in obs["visible_text"] or "Payment failed" in obs["visible_text"]:
            failures.append("visible_text should hold a closed details' summary but not its hidden content")
        if obs["fingerprint"]["text_head"] != obs["visible_text"][:500]:
            failures.append("the fingerprint's text head is not the first 500 chars of visible_text")

        # A secret typed into a plain text field and into a contenteditable comes back as their value; the
        # runner masks it before anything sees the observation (the fingerprint keeps the real value).
        from observe import mask_secrets
        pg.fill("#u", "hunter2-not-real")
        pg.fill('[aria-label="Editor"]', "note hunter2-not-real end")
        masked = mask_secrets(observe(pg), ["hunter2-not-real"])
        shown = json.dumps({k: v for k, v in masked.items() if k != "fingerprint"})
        if "hunter2" in shown:
            failures.append("a typed secret leaked through the observation")
        by_name = {e["name"]: e for e in masked["elements"]}
        if by_name.get("Username", {}).get("value") != "<secret>" or by_name.get("Editor", {}).get("value") != "note <secret> end":
            failures.append(f"typed secrets should show as <secret>: {by_name.get('Username', {}).get('value')!r} {by_name.get('Editor', {}).get('value')!r}")
        if "hunter2-not-real" not in json.dumps(masked["fingerprint"]):
            failures.append("the fingerprint should keep the real value (it is only compared, never sent)")
        b.close()
    print(f"observer check: {len(obs['elements'])} elements, checkboxes={len(boxes)}, states={states}, change_events={changes}")
    print()
    return failures


class FakeJev:
    """Rule-based stand-in for Jev. Answers exactly the shapes the real API returns."""

    def __init__(self, mode: str = "normal", delay_ms: int = 0) -> None:
        # normal | hedge_value | early_low_done | early_confident_done | done_after_add
        # | invalid_operation_once | invalid_operation_always | dead_click
        self.mode = mode
        self.delay_ms = delay_ms  # a slow "model", so a page mutation can land between observation and decision
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

    @staticmethod
    def _keyword(statement: str) -> str | None:
        """The fixture text that makes a check / outcome / adjudication statement true."""
        s = statement.lower()
        if "cart" in s:
            return r"Cart: [1-9]"
        if "error" in s or "wrong" in s:
            return "Something went wrong"
        return None

    def _outcome(self, criteria: dict, text: str) -> str:
        """The outcome Choice by rule: the first declared outcome whose statement is true of the text, else none_yet."""
        for name, when in criteria.items():
            if name == "none_yet":
                continue
            kw = self._keyword(when)
            if kw and re.search(kw, text):
                return name
        return "none_yet"

    def system_one(self, state: dict, questions: dict) -> dict:
        self.requests += 1
        self.seen_states.append(state)
        if self.delay_ms:
            time.sleep(self.delay_ms / 1000)
        answers: dict = {}
        if "evidence_line" in questions:
            # The adjudication request: pick the line that states the outcome, verbatim selection.
            kw = self._keyword(state.get("statement", ""))
            hit = next((ln["id"] for ln in state.get("lines", []) if kw and re.search(kw, ln["text"])), "none")
            answers["evidence_line"] = self._choice(hit, questions["evidence_line"]["criteria"])
            answers["evidence_present"] = {"type": "noul", "noul": 0.95 if hit != "none" else 0.1}
            return {"answers": answers, "usage": {"input_tokens": 200, "output_tokens": 20}, "model": "fake-jev", "latency_ms": 1}
        text = state.get("visible_text", "")
        for key, q in questions.items():
            if q["type"] == "noul":
                if key == "cart_has_item":
                    answers[key] = {"type": "noul", "noul": 1.0 if re.search(r"Cart: [1-9]", text) else 0.02}
                elif key == "error_visible":
                    answers[key] = {"type": "noul", "noul": 0.98 if "Something went wrong" in text else 0.01}
                else:
                    answers[key] = {"type": "noul", "noul": 0.5}
        if "outcome" in questions:
            answers["outcome"] = self._choice(self._outcome(questions["outcome"]["criteria"], text), questions["outcome"]["criteria"])
        if "stuck_reason" in questions:
            answers["stuck_reason"] = self._choice("control_had_no_effect", questions["stuck_reason"]["criteria"])
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

        if self.mode == "dead_click" and self._find(clicks, "Apply filter"):
            op, target = "CLICK", ("click_target", self._find(clicks, "Apply filter"))  # a button that does nothing
        elif self._find(clicks, "Accept cookies"):
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
        if "blocked_reason" in questions:
            answers["blocked_reason"] = self._choice("missing_data_value" if op == "BLOCKED" else "nothing",
                                                     questions["blocked_reason"]["criteria"])
        return {"answers": answers, "usage": {"input_tokens": 400, "output_tokens": 60}, "model": "fake-jev", "latency_ms": 1}

    def usage_summary(self) -> dict:
        return {"jev_requests": self.requests, "input_tokens": 400 * self.requests, "output_tokens": 60 * self.requests, "model": "fake-jev"}


STATE_KEYS = ["goal", "hints", "step", "page", "elements", "truncated_elements", "visible_text",
              "available_data_values", "recent_actions"]


def step_states(jev: "FakeJev") -> list[dict]:
    """The per-step states Jev saw (the final adjudication request has a different, smaller state)."""
    return [s for s in jev.seen_states if "recent_actions" in s]


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
    if not {"CLICK", "TYPE_TEXT", "PRESS_ENTER"} <= set(by_op):
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


def outcome_spec(url: str) -> dict:
    """The same flow written against the results contract: declared outcomes with verdicts, no done_when /
    never, and exact assertions on the final page."""
    from spec import validate

    spec = base_spec(url)
    spec["done_when"], spec["never"] = [], []
    spec["outcomes"] = {
        "item_added": {"when": "The header shows the cart contains at least one item", "verdict": "pass",
                       "note": "the happy path"},
        "app_error": {"when": "An error message such as 'something went wrong' is visible", "verdict": "bug",
                      "note": "adding to the cart failed"},
    }
    spec["assert"] = [
        {"url_matches": "file://**/shop.html*"},
        {"text_contains": "Cart: 1 items"},
        {"element_present": {"role": "button", "name": "Add to cart"}},
        {"element_absent": {"role": "alert"}},
        {"field_value": {"label": "Search products", "equals": "blue hoodie"}},
    ]
    problems = validate(spec)
    assert not problems, problems
    return spec


RESULT_KEYS = ["spec_id", "outcome", "verdict", "note", "probability", "confidence", "seen_at_step", "first_seen_at_step",
               "confirmed", "path_confidence", "reason", "evidence", "assertions", "outcomes_seen_earlier", "story", "status",
               "duration_ms", "usage", "trace"]


def result_shape_check(trace: dict, out: str) -> list[str]:
    """result.json exists, equals trace["result"], and has exactly the documented keys."""
    failures = []
    path = os.path.join(out, "result.json")
    if not os.path.exists(path):
        return [f"result.json missing in {out}"]
    with open(path, encoding="utf-8") as f:
        result = json.load(f)
    if result != trace.get("result"):
        failures.append("result.json differs from trace.result")
    if list(result) != RESULT_KEYS:
        failures.append(f"result.json keys are {list(result)}, expected {RESULT_KEYS}")
    if result["trace"] != os.path.join(out, "trace.json") or result["status"] != trace["status"]:
        failures.append(f"result.json trace/status do not point at the run: {result['trace']} {result['status']}")
    return failures


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
    if ops != ["CLICK", "TYPE_TEXT", "PRESS_ENTER", "CLICK", "WAIT", "AUTO_DONE"] or not trace["steps"][-1]["executed"].get("confirmed"):
        failures.append(f"unexpected action sequence {ops} (a pass sighting gets one settle-and-recheck, then is confirmed)")
    if (trace["outcome"], trace["verdict"]) != ("goal_reached", "pass") or not trace["result"]["confirmed"]:
        failures.append(f"an old-style spec should end in the synthesized goal_reached outcome: {trace['outcome']} {trace['verdict']}")
    if trace["steps"][-2].get("pending_outcome") != "goal_reached" or "outcome" in trace["steps"][-1]:
        failures.append("the sighting step should carry pending_outcome, and no outcome Choice is asked without a `when`")
    failures += result_shape_check(trace, out)
    if trace["spec"]["data"]["password"] != "<secret>":
        failures.append("secret not redacted in trace spec")
    if any("hunter2" in json.dumps(st) for st in jev.seen_states):
        failures.append("secret value leaked into Jev state")
    if not all(s.get("screenshot") == f"steps/{s['n']:03d}.png" and os.path.exists(os.path.join(out, s["screenshot"])) for s in trace["steps"]):
        failures.append(f"screenshots=True should capture every step: {[s.get('screenshot') for s in trace['steps']]}")
    if not os.path.exists(os.path.join(out, "trace.json")):
        failures.append("trace.json missing")
    failures += state_shape_check(step_states(jev)[-1], trace)
    settles = [s.get("settle") for s in trace["steps"] if (s.get("executed") or {}).get("action") == "CLICK"]
    if not settles or not all(isinstance(s, dict) and s.get("ended") in ("quiet", "cap") and isinstance(s.get("ms"), int) for s in settles):
        failures.append(f"action steps do not carry a settle record: {settles}")
    timing = trace.get("timing") or {}
    if set(timing) != {"launch_ms", "navigation_ms", "setup_ms", "steps_ms", "final_ms"} or not all(isinstance(v, int) and v >= 0 for v in timing.values()):
        failures.append(f"trace.timing should hold the five non-negative laps: {timing}")

    # 1b. the same flow with the default policy ("key"): only the terminal step gets a picture, plus final.png
    spec = base_spec(url)
    out = os.path.join(tmp, "run-pass-key")
    trace = run(spec, FakeJev(), out)  # screenshots=None -> the spec default, which is "key"
    print(summarize(trace, out))
    print()
    shots = [s.get("screenshot") for s in trace["steps"]]
    if trace["status"] != "passed" or shots[:-1] != [None] * (len(shots) - 1) or shots[-1] != f"steps/{len(shots):03d}.png":
        failures.append(f"screenshots=key should capture only the terminal step of a clean run: {shots}")
    if not os.path.exists(os.path.join(out, "steps", "final.png")) or trace["final"].get("screenshot") != "steps/final.png":
        failures.append("final.png missing in key mode")
    if f"screenshots: steps {len(shots)} + final.png" not in summarize(trace, out):
        failures.append("summary does not say which steps have screenshots")

    # 2. the app shows an error -> the synthesized never_<check> outcome (verdict bug) ends the run with status
    #    outcome at first sighting; in key mode the terminal step has a picture
    spec = base_spec(url + "?fail=1")
    out = os.path.join(tmp, "run-error")
    trace = run(spec, FakeJev(), out, screenshots="key")
    print(summarize(trace, out))
    print()
    if trace["status"] != "outcome" or (trace["outcome"], trace["verdict"]) != ("never_error_visible", "bug"):
        failures.append(f"expected outcome never_error_visible/bug, got {trace['status']} {trace['outcome']} ({trace.get('error')})")
    if trace["steps"][-1].get("never_violated") != ["error_visible"] or trace["steps"][-1].get("outcome_seen") != "never_error_visible":
        failures.append(f"the terminal step should carry never_violated and outcome_seen: {trace['steps'][-1].get('never_violated')} {trace['steps'][-1].get('outcome_seen')}")
    if not trace["steps"][-1].get("screenshot") or any(s.get("screenshot") for s in trace["steps"][:-1]):
        failures.append(f"key mode: only the outcome step should have a screenshot: {[s.get('screenshot') for s in trace['steps']]}")
    if trace["result"]["evidence"]["line"] != "Something went wrong. Please try again later." or trace["result"]["confirmed"]:
        failures.append(f"a bug outcome should quote its evidence line and not be 'confirmed': {trace['result']['evidence']}")

    # 3. needed data missing -> blocked; screenshots=False writes no picture at all
    spec = base_spec(url)
    spec["data"] = {}
    spec["secrets"] = []
    out = os.path.join(tmp, "run-blocked")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "blocked":
        failures.append(f"expected blocked, got {trace['status']} ({trace.get('error')})")
    if any(s.get("screenshot") for s in trace["steps"]) or trace["final"].get("screenshot") or os.listdir(os.path.join(out, "steps")):
        failures.append("screenshots=False still wrote pictures")
    reason = (trace["result"] or {}).get("reason") or {}
    if trace["outcome"] != "undetermined" or reason.get("blocked_reason") != "missing_data_value" or reason.get("suggested_verdict") != "test_issue":
        failures.append(f"blocked should be undetermined with the typed reason missing_data_value -> test_issue: {trace['outcome']} {reason}")

    # 4. Jev unsure WHICH value to type -> nothing is typed, run ends low_confidence (was: typed anyway);
    #    in key mode every low-confidence step has a picture
    spec = base_spec(url)
    out = os.path.join(tmp, "run-hedge-value")
    trace = run(spec, FakeJev("hedge_value"), out, screenshots="key")
    print(summarize(trace, out))
    print()
    ops = [s.get("executed", {}).get("action") for s in trace["steps"]]
    if trace["status"] != "low_confidence":
        failures.append(f"expected low_confidence, got {trace['status']} ({trace.get('error')})")
    if "TYPE_TEXT" in ops or trace["actions_executed"] != 1:
        failures.append(f"a low-confidence value choice was executed: {ops}")
    if not all(bool(s.get("screenshot")) == bool(s.get("low_confidence") or s is trace["steps"][-1]) for s in trace["steps"]):
        failures.append(f"key mode: low-confidence steps should have screenshots and clean ones not: {[(s.get('low_confidence'), s.get('screenshot')) for s in trace['steps']]}")
    waited = [s for s in trace["steps"] if s.get("low_confidence") and (s.get("executed") or {}).get("action") == "WAIT"]
    if not waited or not all(isinstance(s.get("settle"), dict) and s["latency_ms"]["browser"] >= spec["browser"]["settle_ms"] for s in waited):
        failures.append(f"a low-confidence WAIT should wait settle_ms and record its settle: {[(s.get('settle'), s.get('latency_ms')) for s in waited]}")
    reason = (trace["result"] or {}).get("reason") or {}
    if reason.get("status") != "low_confidence" or reason.get("suggested_verdict") != "test_issue":
        failures.append(f"low_confidence should suggest test_issue: {reason}")

    # 4b. a button that does nothing: the same click on an unchanged page three times -> stuck; the trace and
    #     Jev's recent_actions both say page_changed: false; in key mode the repeat (>= 2) and terminal steps
    #     have pictures, the first click does not
    spec = base_spec(url)
    jev = FakeJev("dead_click")
    out = os.path.join(tmp, "run-dead-click")
    trace = run(spec, jev, out, screenshots="key")
    print(summarize(trace, out))
    print()
    steps = trace["steps"]
    if trace["status"] != "stuck" or trace["actions_executed"] != 2 or len(steps) != 3:
        failures.append(f"dead click: expected stuck after 2 executed clicks and 3 steps, got {trace['status']} {trace['actions_executed']} {len(steps)}")
    if [s.get("page_changed") for s in steps] != [False, False, None] or not all("Apply filter" in (s.get("target") or {}).get("label", "") for s in steps):
        failures.append(f"dead click: page_changed should be false on both executed clicks: {[(s.get('page_changed'), (s.get('target') or {}).get('label')) for s in steps]}")
    recent = step_states(jev)[-1]["recent_actions"]
    if len(recent) != 2 or any(a.get("page_changed") is not False for a in recent):
        failures.append(f"dead click: Jev was not told the clicks changed nothing: {recent}")
    if [bool(s.get("screenshot")) for s in steps] != [False, True, True] or [s.get("repeat_count") for s in steps] != [1, 2, 3]:
        failures.append(f"dead click: key mode should picture the repeat and terminal steps only: {[(s.get('repeat_count'), s.get('screenshot')) for s in steps]}")
    if [("stuck_reason" in s) for s in steps] != [False, True, True] or (steps[-1].get("stuck_reason") or {}).get("choice") != "control_had_no_effect":
        failures.append(f"stuck_reason should be asked only after an action with page_changed false: {[s.get('stuck_reason') for s in steps]}")
    reason = (trace["result"] or {}).get("reason") or {}
    if reason.get("stuck_reason") != "control_had_no_effect" or reason.get("suggested_verdict") != "bug":
        failures.append(f"stuck with a dead control should suggest bug: {reason}")

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
    if trace["status"] != "passed" or ops[-2:] not in (["WAIT", "DONE"], ["WAIT", "AUTO_DONE"]) or not trace["steps"][-1]["executed"].get("confirmed"):
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
    if jev.requests != len(trace["steps"]) + 2:  # one retry, one adjudication
        failures.append(f"expected exactly one extra request for the retry (plus the adjudication), got {jev.requests} for {len(trace['steps'])} steps")
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

    # 10. the target changes while Jev is deciding -> the decision is stale, nothing is executed, the
    #     run re-observes and finishes with the other button (one stale step, same number of actions)
    spec = base_spec(url + "?stale_once=1")
    jev = FakeJev(delay_ms=400)
    out = os.path.join(tmp, "run-stale-once")
    trace = run(spec, jev, out, screenshots="key")
    print(summarize(trace, out))
    print()
    stale_steps = [s for s in trace["steps"] if s.get("stale")]
    if stale_steps and not stale_steps[0].get("screenshot"):
        failures.append("key mode: the stale step should have a screenshot")
    if trace["status"] != "passed" or trace["actions_executed"] != 4:
        failures.append(f"stale_once: expected passed with 4 actions, got {trace['status']} with {trace['actions_executed']} ({trace.get('error')})")
    if len(stale_steps) != 1 or "disabled" not in stale_steps[0]["stale"]:
        failures.append(f"stale_once: expected exactly one stale step naming 'disabled', got {[s.get('stale') for s in trace['steps']]}")
    if stale_steps and stale_steps[0]["executed"] != {"action": "WAIT", "ok": True, "error": None,
                                                        "reason": f"page changed during the decision: {stale_steps[0]['stale']}"}:
        failures.append(f"stale step not recorded as a WAIT with the reason: {stale_steps[0]['executed']}")
    if stale_steps and any(a["step"] == stale_steps[0]["n"] for a in step_states(jev)[-1]["recent_actions"]):
        failures.append("the stale step leaked into recent_actions")
    clicked = [s for s in trace["steps"] if (s.get("executed") or {}).get("action") == "CLICK" and "Add to cart" in (s.get("target") or {}).get("label", "")]
    if not clicked or clicked[-1]["target"]["element"] == stale_steps[0]["target"]["element"] if stale_steps else True:
        failures.append("after the stale step the run did not pick the other Add-to-cart button")

    # 11. the page never holds still -> max_stale consecutive stale decisions -> unstable_page, nothing executed
    spec = base_spec(url + "?unstable=1")
    out = os.path.join(tmp, "run-unstable")
    trace = run(spec, FakeJev(delay_ms=300), out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "unstable_page" or trace["actions_executed"] != 0:
        failures.append(f"unstable: expected unstable_page with no actions, got {trace['status']} with {trace['actions_executed']}")
    if len(trace["steps"]) != spec["thresholds"]["max_stale"] or not all(s.get("stale") for s in trace["steps"]):
        failures.append(f"unstable: expected {spec['thresholds']['max_stale']} stale steps, got {[s.get('stale') for s in trace['steps']]}")
    if trace["steps"] and trace["steps"][-1]["executed"]["action"] != "STOP":
        failures.append(f"unstable: terminal step should be a STOP: {trace['steps'][-1]['executed']}")

    # 12. viewport-first text: a long filler that comes first in the DOM but sits below the fold is
    #     moved after what is on screen, not lost; the flow still passes
    spec = base_spec(url + "?longtext=1")
    jev = FakeJev()
    out = os.path.join(tmp, "run-longtext")
    trace = run(spec, jev, out, screenshots=False)
    print(summarize(trace, out))
    print()
    text = jev.seen_states[0]["visible_text"]
    if trace["status"] != "passed":
        failures.append(f"longtext: expected passed, got {trace['status']} ({trace.get('error')})")
    if not (0 <= text.find("Mini Shop") < text.find("Lorem ipsum")):
        failures.append(f"visible_text is not viewport-first: Mini Shop at {text.find('Mini Shop')}, filler at {text.find('Lorem ipsum')}")
    if "lorem 149" not in text or len(text) != spec["observation"]["max_text_chars"]:
        failures.append(f"visible_text lost the below-the-fold text or ignored max_text_chars: len={len(text)}")
    if trace["steps"][0]["visible_text"] != text[:600]:
        failures.append("the step's visible_text excerpt is not the first 600 chars of what Jev saw")
    if "item 79" not in text or text.find("item 79") > text.find("Lorem ipsum"):
        failures.append(f"in-view list items should all precede the below-the-fold filler: item 79 at {text.find('item 79')}, filler at {text.find('Lorem ipsum')}")
    from observe import fingerprint as _fp, observe as _observe
    from playwright.sync_api import sync_playwright as _sp
    with _sp() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(url + "?longtext=1")
        o = _observe(pg, 200, 4000)
        head_again = _fp(pg)["text_head"]
        b.close()
    if not (len(o["fingerprint"]["text_head"]) == 500 and o["fingerprint"]["text_head"] == o["visible_text"][:500] == head_again):
        failures.append("with the head cut inside the in-view text, visibleText(500) must be the prefix of visibleText(4000) and equal at fingerprint time")

    # 13. browser.cdp_url: attach to a browser we did not launch, leave its tabs alone
    failures += cdp_check(url, tmp)

    # 15. the results contract, happy path: the declared pass outcome is seen, confirmed after a
    #     settle-and-recheck, every assertion holds, the adjudication quotes the evidence line
    spec = outcome_spec(url)
    jev = FakeJev()
    out = os.path.join(tmp, "run-outcome-pass")
    trace = run(spec, jev, out, screenshots="key")
    print(summarize(trace, out))
    print()
    res = trace["result"]
    if trace["status"] != "passed" or (res["outcome"], res["verdict"], res["confirmed"]) != ("item_added", "pass", True):
        failures.append(f"outcome pass: expected passed/item_added/confirmed, got {trace['status']} {res['outcome']} {res['verdict']} {res['confirmed']}")
    if res["seen_at_step"] != len(trace["steps"]) or res["first_seen_at_step"] != len(trace["steps"]) - 1 or res["note"] != "the happy path" or not (res["probability"] or 0) >= 0.8:
        failures.append(f"outcome pass: seen_at_step/first_seen_at_step/note/probability wrong: {res['seen_at_step']} {res['first_seen_at_step']} {res['note']} {res['probability']}")
    if len(res["assertions"]) != 5 or not all(a["ok"] for a in res["assertions"]):
        failures.append(f"outcome pass: every assertion should hold: {res['assertions']}")
    if "Cart: 1 items" not in (res["evidence"]["line"] or "") or not (res["evidence"]["present"] or 0) >= 0.9 or res["evidence"]["checks"].get("cart_has_item") != 1.0:
        failures.append(f"outcome pass: evidence should quote the header line with the cart count: {res['evidence']}")
    story = res["story"]
    story_ok = (len(story) == 4 and 'CLICK [' in story[0] and 'button "Accept cookies"' in story[0]
                and story[1].startswith("2 TYPE_TEXT [") and story[1].endswith('textbox "Search products" <- search_query')
                and story[2] == "3 PRESS_ENTER" and story[3].startswith("4 CLICK [") and 'button "Add to cart"' in story[3])
    if not story_ok or res["path_confidence"] != 0.9 or res["reason"] is not None:
        failures.append(f"outcome pass: story/path_confidence/reason wrong: {story} {res['path_confidence']} {res['reason']}")
    first = trace["steps"][0]
    if (first.get("outcome") or {}).get("choice") != "none_yet" or set((first["outcome"] or {}).get("probabilities", {})) != {"item_added", "app_error", "none_yet"}:
        failures.append(f"outcome pass: the outcome Choice should be asked every step over the declared outcomes + none_yet: {first.get('outcome')}")
    if (first.get("blocked_reason") or {}).get("choice") != "nothing" or "stuck_reason" in first:
        failures.append(f"outcome pass: blocked_reason is asked every step, stuck_reason only after a no-op action: {first.get('blocked_reason')} {first.get('stuck_reason')}")
    if jev.requests != len(trace["steps"]) + 1 or (trace.get("adjudication") or {}).get("line_id") is None:
        failures.append(f"outcome pass: expected one adjudication request after the steps: {jev.requests} requests, {trace.get('adjudication')}")
    failures += result_shape_check(trace, out)

    # 16. the results contract, a bug outcome: terminal at first sighting, picture forced, no confirmation
    spec = outcome_spec(url + "?fail=1")
    out = os.path.join(tmp, "run-outcome-bug")
    trace = run(spec, FakeJev(), out, screenshots="key")
    print(summarize(trace, out))
    print()
    res = trace["result"]
    last = trace["steps"][-1]
    if trace["status"] != "outcome" or (res["outcome"], res["verdict"], res["confirmed"]) != ("app_error", "bug", False):
        failures.append(f"outcome bug: expected outcome/app_error/bug, got {trace['status']} {res['outcome']} {res['verdict']}")
    if res["seen_at_step"] != res["first_seen_at_step"] != len(trace["steps"]):
        failures.append(f"outcome bug: a first-sighting outcome is seen and terminal on the same step: {res['seen_at_step']} {res['first_seen_at_step']}")
    if last.get("outcome_seen") != "app_error" or not last.get("screenshot") or last["executed"]["action"] != "STOP":
        failures.append(f"outcome bug: the sighting step should be terminal with a picture: {last.get('outcome_seen')} {last.get('screenshot')} {last.get('executed')}")
    if res["evidence"]["line"] != "Something went wrong. Please try again later." or res["evidence"]["screenshot"] != last["screenshot"]:
        failures.append(f"outcome bug: evidence should quote the error line and point at the sighting picture: {res['evidence']}")
    if res["note"] != "adding to the cart failed" or res["assertions"] != [] or res["reason"] is not None:
        failures.append(f"outcome bug: note/assertions/reason wrong: {res['note']} {res['assertions']} {res['reason']}")

    # 17. a confirmed pass whose assertions do not hold -> assert_failed, undetermined with the failing
    #     assertions and their actual values (Claude decides whether the assertion or the app is wrong)
    spec = outcome_spec(url)
    spec["assert"] = [{"text_contains": "Cart: 2 items"}, {"url_matches": "**/other.html"}, {"element_present": {"role": "button", "name": "Add to cart"}}]
    out = os.path.join(tmp, "run-outcome-assert")
    trace = run(spec, FakeJev(), out, screenshots="key")
    print(summarize(trace, out))
    print()
    res = trace["result"]
    if trace["status"] != "assert_failed" or res["outcome"] != "undetermined" or res["verdict"] is not None:
        failures.append(f"assert: expected assert_failed/undetermined, got {trace['status']} {res['outcome']} {res['verdict']}")
    reason = res["reason"] or {}
    failed = reason.get("failed_assertions") or []
    if reason.get("status") != "assert_failed" or reason.get("suggested_verdict") is not None or len(failed) != 2 or reason.get("outcome_seen") != "item_added":
        failures.append(f"assert: reason should name the seen outcome and carry the two failing assertions, no suggestion: {reason}")
    if not ("Cart: 1 items" in str(failed[0].get("actual")) and failed[1].get("actual", "").endswith("shop.html")) if len(failed) == 2 else True:
        failures.append(f"assert: failing assertions should report actual values: {failed}")
    if [a["ok"] for a in res["assertions"]] != [False, False, True]:
        failures.append(f"assert: all three assertions should be reported: {res['assertions']}")

    # 14. .env in the working directory is loaded; already-exported variables win; quotes are stripped
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
