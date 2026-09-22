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
<!-- a product grid of plain divs: three identical "Add to cart" buttons, two cards at the same price, and per card
     an image link and a title link with the same name (the same product twice: no context must be invented) -->
<div class="grid" style="display:flex;gap:16px;margin-top:12px">
  <div class="card"><div class="img"><a href="#w" aria-label="Widget 12-pack"><img alt="" width="12" height="12"></a></div>
    <div class="body"><div class="title"><a href="#w">Widget 12-pack</a></div><div class="desc">Twelve widgets</div><div class="pricebar">$29.99 <button>Add to cart</button></div></div></div>
  <div class="card"><div class="img"><a href="#g" aria-label="Gadget 6-pack"><img alt="" width="12" height="12"></a></div>
    <div class="body"><div class="title"><a href="#g">Gadget 6-pack</a></div><div class="desc">Six gadgets</div><div class="pricebar">$9.99 <button>Add to cart</button></div></div></div>
  <div class="card"><div class="img"><a href="#z" aria-label="Gizmo 3-pack"><img alt="" width="12" height="12"></a></div>
    <div class="body"><div class="title"><a href="#z">Gizmo 3-pack</a></div><div class="desc">Three gizmos</div><div class="pricebar">$9.99 <button>Add to cart</button></div></div></div>
</div>
<div style="height:2200px"></div>
<!-- below the fold: the assertion oracle must see these, the table Jev chooses from must not -->
<a href="#logout">Logout</a>
<div role="alert">Session expired</div>
<label>Coupon <input id="coupon" value="SAVE10"></label>
</body></html>
"""


SETTLE_PAGE = """<!doctype html><html><head><title>Settle</title></head><body>
<button id="burst" onclick="burst()">Burst</button>
<button id="forever" onclick="forever()">Forever</button>
<input id="cb" role="combobox" aria-label="Product" oninput="suggest()">
<ul id="list" role="listbox"></ul>
<input id="sb" role="searchbox" aria-label="Find">
<input id="sync" role="combobox" aria-label="Colour" oninput="filterSync()">
<ul id="synclist" role="listbox"></ul>
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
 function filterSync(){  // client-side filtering: the suggestions are on screen before the input handler returns
   const ul = document.getElementById('synclist'); ul.innerHTML = '';
   for (const c of ['blue', 'black', 'red']) if (c.startsWith(document.getElementById('sync').value)) {
     const li = document.createElement('li'); li.setAttribute('role', 'option'); li.textContent = c; ul.appendChild(li); } }
</script></body></html>"""


# A page that loads for a while after a click: Start hides itself, "Loading..." shows, and after ?ms=<n>
# milliseconds (default 1200; 0 = never) "Hello World!" replaces it. Nothing else is on the page, so the only
# sensible decision while it loads is WAIT, again and again, on a page whose signature does not change.
LOADING_PAGE = """<!doctype html><html><head><title>Loading</title></head><body>
<h1>Dynamically loaded content</h1>
<div id="start"><button onclick="start()">Start</button></div>
<div id="loading" style="display:none">Loading...</div>
<div id="finish" style="display:none">Hello World!</div>
<script>
 function start(){
   document.getElementById('start').style.display = 'none';
   document.getElementById('loading').style.display = 'block';
   const ms = parseInt(new URLSearchParams(location.search).get('ms') || '1200', 10);
   if (ms > 0) setTimeout(() => {
     document.getElementById('loading').style.display = 'none';
     document.getElementById('finish').style.display = 'block'; }, ms);
 }
</script></body></html>"""


def loading_spec(url: str, max_steps: int = 12) -> dict:
    from spec import DEFAULTS, _merge, validate

    spec = _merge(DEFAULTS, {
        "id": "selftest-loading", "start_url": url,
        "goal": "Press Start and wait for the loading to finish, so that 'Hello World!' is displayed.",
        "outcomes": {"loaded": {"when": "The text 'Hello World!' is displayed", "verdict": "pass"}},
        "assert": [{"text_contains": "Hello World!"}],
        "budget": {"max_steps": max_steps, "max_seconds": 60},
        "browser": {"settle_ms": 100, "quiet_ms": 20},   # a WAIT pauses settle_ms: a 1.2 s load takes many of them
    })
    problems = validate(spec)
    assert not problems, problems
    return spec


def settle_check(url: str) -> list[str]:
    """settle() ends on DOM quiet, on the cap, or on a visible autocomplete option. No Jev involved."""
    from playwright.sync_api import sync_playwright
    from run_test import settle
    from spec import DEFAULTS, _merge

    failures = []

    def sp(cap: int, quiet: int) -> dict:
        return _merge(DEFAULTS, {"id": "settle", "start_url": url, "goal": "x", "browser": {"settle_ms": cap, "quiet_ms": quiet}})

    from observe import observe

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 800, "height": 600})
        pg.goto(url)
        observe(pg)  # as in the loop: the options wait counts an option as new when Jev did not see it (no data-jev-idx)
        pg.click("#burst")  # mutates every 20 ms for 150 ms, then stops
        r1 = settle(pg, sp(1000, 50))
        if r1["ended"] != "quiet" or not (150 <= r1["ms"] < 800):
            failures.append(f"settle after a 150 ms burst should end quiet at >= 150 ms and well under the cap: {r1}")
        pg.click("#forever")  # never stops mutating
        r2 = settle(pg, sp(300, 50))
        if r2["ended"] != "cap" or not (280 <= r2["ms"] <= 700):
            failures.append(f"settle on a never-quiet page should end at the cap (300 ms): {r2}")
        pg.goto(url)  # a fresh document: no interval running
        observe(pg)
        pg.fill("#cb", "blu")  # the option appears 120 ms later; the sidebar's permanent option must not count
        r3 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "combobox"))
        visible = pg.locator('#list [role="option"]').count()
        if r3["ended"] != "options" or not (120 <= r3["ms"] < 600) or visible != 1:
            failures.append(f"settle after typing into a combobox should wait for a NEW option: {r3}, options visible={visible}")
        r4 = settle(pg, sp(1000, 50))  # a plain settle right after: nothing changes, quiet within ~quiet_ms
        if r4["ended"] != "quiet" or r4["ms"] >= 400:
            failures.append(f"a quiet page should settle in about quiet_ms: {r4}")
        observe(pg)  # the option from the previous typing is now one Jev saw
        pg.fill("#sb", "xyz")  # a searchbox that never produces suggestions: give up after 200 ms
        r5 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "searchbox"))
        if r5["ended"] != "options_timeout" or not (200 <= r5["ms"] < 500):
            failures.append(f"typing into a searchbox with no suggestions should end options_timeout at ~200 ms: {r5}")
        pg.fill("#sync", "bl")  # suggestions rendered synchronously by the typing: on screen before the settle begins
        r6 = settle(pg, sp(1000, 50), after=("TYPE_TEXT", "combobox"))
        if r6["ended"] != "options" or r6["ms"] >= 200:
            failures.append(f"suggestions already on screen when the settle starts must count as arrived, not time out: {r6}")
        b.close()
    print(f"settle check: burst={r1} forever={r2} combobox={r3} quiet={r4} no-suggestions={r5} sync={r6}")
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
        # Identical labels: the three "Add to cart" buttons sit in plain <div> cards (no row / list-item), two cards
        # share a price, so the distinguishing level is the card with its title; a label that is unique on the page
        # ("Continue") gets no context, and the row checkboxes keep the row context pass 1 gave them.
        adds = [e for e in obs["elements"] if e["role"] == "button" and e["name"] == "Add to cart"]
        contexts = [e.get("context") or "" for e in adds]
        if len(adds) != 3 or len(set(contexts)) != 3 or not all(t in c for t, c in zip(("Widget 12-pack", "Gadget 6-pack", "Gizmo 3-pack"), contexts)):
            failures.append(f"identical buttons should be told apart by their card: {contexts}")
        if any(("$9.99" in c and "pack" not in c) for c in contexts):
            failures.append(f"the shared price bar must not be taken as the distinguishing context: {contexts}")
        if by_name.get("Continue", {}).get("context"):
            failures.append(f"a unique label needs no context: {by_name.get('Continue')}")
        # The image link and the title link of one card share a name: their common container is the card, and nothing
        # below it tells them apart, so neither gets a context (the first cut of this pass climbed past the card and
        # labelled one product's button with another product's text).
        pairs = [e for e in obs["elements"] if e["role"] == "link" and e["name"] in ("Widget 12-pack", "Gadget 6-pack", "Gizmo 3-pack")]
        if len(pairs) != 6 or any(e.get("context") for e in pairs):
            failures.append(f"same-product duplicates must not be given a context: {[(e['name'], e.get('context')) for e in pairs]}")
        from observe import element_label
        if element_label(adds[1]) != 'button "Add to cart" in "Gadget 6-pack Six gadgets $9.99 Add to cart"':
            failures.append(f"trace labels should carry the distinguishing context: {element_label(adds[1])}")
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
        if by_name.get("Pick", {}).get("datalist") is not True or by_name.get("Find", {}).get("datalist") is not None:
            failures.append(f"a datalist input should be flagged (the settle must not wait for DOM options): {by_name.get('Pick')}")

        # The assertion oracle is the whole document: the Logout link, the alert and the Coupon field sit 2,200 px
        # below the fold, so they are absent from the table Jev chooses from (a 1280x800 viewport) and present to
        # check_assertions; comparisons use the real values and `actual` is masked.
        from run_test import adjudicate, check_assertions
        names = {e["name"] for e in masked["elements"]}
        if "Logout" in names or "Coupon" in names:
            failures.append("below-the-fold controls should not be in the table Jev chooses from")
        got = check_assertions({"assert": [
            {"element_present": {"role": "link", "name": "Logout"}}, {"element_absent": {"role": "alert"}},
            {"field_value": {"label": "Coupon", "equals": "SAVE10"}}, {"field_value": {"label": "Username", "equals": "hunter2-not-real"}},
            {"text_contains": "Session expired"}, {"url_matches": "file://**/controls.html"},
        ]}, pg, masked, ["hunter2-not-real"])
        if [a["ok"] for a in got] != [True, False, True, True, True, True]:
            failures.append(f"assertions should judge the whole document: {[(next(k for k in a if k not in ('ok', 'actual')), a['ok']) for a in got]}")
        if "hunter2" in json.dumps(got) or got[3]["field_value"]["equals"] != "<secret>":
            failures.append(f"assertion records should be masked: {got[3]}")
        if pg.evaluate("() => document.querySelectorAll('[data-jev-idx]').length") != len(masked["elements"]):
            failures.append("the whole-document observation must not re-number the nodes Jev saw")

        # The adjudication lines: viewport-first, masked, and never fatal on a bad answer
        class PickEditor:
            def system_one(self, state, questions):
                self.state = state
                crit = questions["evidence_line"]["criteria"]  # pointers by id (lever F3): the text is in state.lines
                pick = next((ln["id"] for ln in state["lines"] if "note" in ln["text"]), "none")
                return {"answers": {"evidence_line": {"type": "choice", "choice": pick, "confidence": 0.9,
                                                      "probabilities": {k: (1.0 if k == pick else 0.0) for k in crit}},
                                    "evidence_present": {"type": "noul", "noul": 0.9}}, "usage": {}, "latency_ms": 1}
        picker = PickEditor()
        rec = adjudicate(pg, picker, "edited", "The editor holds a note", ["hunter2-not-real"])
        lines = [ln["text"] for ln in picker.state["lines"]]
        if "note <secret> end" not in (rec.get("line") or "") or "hunter2" in json.dumps(picker.state):
            failures.append(f"the adjudication should quote the masked line and send masked lines: {rec.get('line')!r}")
        if not (lines.index("Continue") < lines.index("Logout") and lines.index("Show error") < lines.index("Session expired")):
            failures.append(f"adjudication lines should come viewport-first: {lines[:6]} ... {lines[-4:]}")
        if "Payment failed: card declined" in lines:
            failures.append("a closed details' content is not a quotable line")

        class Broken:
            def system_one(self, state, questions):
                raise ValueError("not JSON")
        rec = adjudicate(pg, Broken(), "edited", "The editor holds a note", [])
        if rec.get("line") is not None or "ValueError" not in (rec.get("error") or ""):
            failures.append(f"a failing adjudication is recorded, never raised: {rec}")
        b.close()
    print(f"observer check: {len(obs['elements'])} elements, checkboxes={len(boxes)}, states={states}, change_events={changes}")
    print()
    return failures


class FakeJev:
    """Rule-based stand-in for Jev. Answers exactly the shapes the real API returns."""

    def __init__(self, mode: str = "normal", delay_ms: int = 0) -> None:
        # normal | hedge_value | early_low_done | early_confident_done | done_after_add
        # | invalid_operation_once | invalid_operation_always | dead_click | blocked_after_dead_click
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
        if "hello" in s:
            return "Hello World!"
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
        line_keys = [k for k in questions if k == "evidence_line" or k.startswith("evidence_line_")]
        if line_keys:
            # The adjudication request: pick the line that states the outcome, verbatim selection; a compound
            # statement asks one Choice per sentence (`evidence_line_1`, …), each judged on its own sentence.
            any_hit = False
            for key in line_keys:
                instructions = questions[key]["instructions"]
                sentence = instructions.get("sentence") if isinstance(instructions, dict) else None
                kw = self._keyword(sentence or state.get("statement", ""))
                hit = next((ln["id"] for ln in state.get("lines", []) if kw and re.search(kw, ln["text"])), "none")
                any_hit = any_hit or hit != "none"
                answers[key] = self._choice(hit, questions[key]["criteria"])
            answers["evidence_present"] = {"type": "noul", "noul": 0.95 if any_hit else 0.1}
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
            answers["stuck_reason"] = self._choice("still_loading" if "Loading..." in text else "control_had_no_effect",
                                                   questions["stuck_reason"]["criteria"])
        if set(questions) == {"blocked_reason"}:
            # The follow-up on a terminal step (lever F1): the reason for the ending, over the step's own state.
            why = "other" if self.mode == "blocked_after_dead_click" else "missing_data_value"
            answers["blocked_reason"] = self._choice(why, questions["blocked_reason"]["criteria"])
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

        if self.mode == "blocked_after_dead_click" and any(a.get("page_changed") is False for a in recent):
            op, target = "BLOCKED", None   # gave up right after the dead click: "something else" is in the way
        elif self.mode in ("dead_click", "blocked_after_dead_click") and self._find(clicks, "Apply filter"):
            op, target = "CLICK", ("click_target", self._find(clicks, "Apply filter"))  # a button that does nothing
        elif self._find(clicks, '"Start"'):
            op, target = "CLICK", ("click_target", self._find(clicks, '"Start"'))       # the loading fixture
        elif "Loading..." in text:
            op, target = "WAIT", None                                                    # the only sensible move while it loads
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
            why = "nothing" if op != "BLOCKED" else ("other" if self.mode == "blocked_after_dead_click" else "missing_data_value")
            answers["blocked_reason"] = self._choice(why, questions["blocked_reason"]["criteria"])
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

    # 1b. the same flow with the default policy ("key"): the pass sighting (the page where the outcome was first
    #     seen) and the terminal step get a picture, the ordinary steps do not, plus final.png
    spec = base_spec(url)
    out = os.path.join(tmp, "run-pass-key")
    trace = run(spec, FakeJev(), out)  # screenshots=None -> the spec default, which is "key"
    print(summarize(trace, out))
    print()
    shots = [s.get("screenshot") for s in trace["steps"]]
    n = len(shots)
    if trace["status"] != "passed" or shots != [None] * (n - 2) + [f"steps/{n - 1:03d}.png", f"steps/{n:03d}.png"]:
        failures.append(f"screenshots=key should capture the sighting and the terminal step of a clean run: {shots}")
    if not os.path.exists(os.path.join(out, "steps", "final.png")) or trace["final"].get("screenshot") != "steps/final.png":
        failures.append("final.png missing in key mode")
    if f"screenshots: steps {n - 1}, {n} + final.png" not in summarize(trace, out):
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
    jev = FakeJev()
    trace = run(spec, jev, out, screenshots=False)
    print(summarize(trace, out))
    print()
    if trace["status"] != "blocked":
        failures.append(f"expected blocked, got {trace['status']} ({trace.get('error')})")
    if any(s.get("screenshot") for s in trace["steps"]) or trace["final"].get("screenshot") or os.listdir(os.path.join(out, "steps")):
        failures.append("screenshots=False still wrote pictures")
    reason = (trace["result"] or {}).get("reason") or {}
    if trace["outcome"] != "undetermined" or reason.get("blocked_reason") != "missing_data_value" or reason.get("suggested_verdict") != "test_issue":
        failures.append(f"blocked should be undetermined with the typed reason missing_data_value -> test_issue: {trace['outcome']} {reason}")
    if (not trace["steps"][-1].get("reason_request") or jev.requests != len(trace["steps"]) + 1
            or any("blocked_reason" in s for s in trace["steps"][:-1])):
        failures.append(f"blocked: blocked_reason is asked once, as a follow-up on the terminal step: {jev.requests} requests for "
                        f"{len(trace['steps'])} steps, asked on {[('blocked_reason' in s) for s in trace['steps']]}")

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

    # 4c. a page that loads for 1.2 s after Start: Jev chooses WAIT on an unchanged page many times over. A WAIT
    #     is not an action, so it never counts toward `stuck` (a live 5 s loader ended stuck after 1.5 s), and the
    #     run passes once "Hello World!" appears; each WAIT after the first carries stuck_reason still_loading.
    loading_html = os.path.join(tmp, "loading.html")
    with open(loading_html, "w", encoding="utf-8") as f:
        f.write(LOADING_PAGE)
    spec = loading_spec("file://" + loading_html)
    jev = FakeJev()
    out = os.path.join(tmp, "run-loading")
    trace = run(spec, jev, out, screenshots="key")
    print(summarize(trace, out))
    print()
    steps = trace["steps"]
    waits = [s for s in steps if (s.get("operation") or {}).get("choice") == "WAIT" and (s.get("executed") or {}).get("action") == "WAIT"]
    if trace["status"] != "passed" or (trace["outcome"], trace["verdict"]) != ("loaded", "pass"):
        failures.append(f"loading: expected passed via 'loaded', got {trace['status']} {trace.get('outcome')} ({trace.get('error')})")
    if len(waits) < 3 or any(s.get("repeat_count") for s in waits):
        failures.append(f"loading: WAIT must not count as a repeated action: {len(waits)} waits, repeat counts {[s.get('repeat_count') for s in waits]}")
    if (steps[0].get("target") or {}).get("label") != '[0] button "Start"' or steps[0].get("repeat_count") != 1:
        failures.append(f"loading: the Start click is the one counted action: {steps[0].get('target')} {steps[0].get('repeat_count')}")
    if not all((s.get("stuck_reason") or {}).get("choice") == "still_loading" for s in waits[1:]):
        failures.append(f"loading: a WAIT on an unchanged page is asked stuck_reason: {[s.get('stuck_reason') for s in waits]}")
    pauses = [s["executed"].get("wait_ms") for s in waits]
    if pauses[:3] != [100, 200, 400] or any(p != 400 for p in pauses[3:]) or [s.get("wait_streak") for s in waits] != list(range(len(waits))):
        failures.append(f"loading: consecutive WAITs on the unchanged page back off settle_ms x 1, 2, 4, 4...: {pauses} streaks {[s.get('wait_streak') for s in waits]}")
    if trace["result"]["assertions"] and not all(a["ok"] for a in trace["result"]["assertions"]):
        failures.append(f"loading: the assertion on the loaded text should hold: {trace['result']['assertions']}")

    # 4d. a loader that never finishes (?ms=0) with a small budget: the budget ends the run, not `stuck`, and the
    #     result carries the last still_loading (the final look asks none) so the suggestion is flaky, not test_issue
    spec = loading_spec("file://" + loading_html + "?ms=0", max_steps=5)
    out = os.path.join(tmp, "run-loading-forever")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    reason = (trace["result"] or {}).get("reason") or {}
    if trace["status"] != "budget_exhausted" or len(trace["steps"]) != 6 or not trace["steps"][-1].get("final_look"):
        failures.append(f"loading forever: expected budget_exhausted after 5 steps + final look, got {trace['status']} {len(trace['steps'])}")
    if reason.get("stuck_reason") != "still_loading" or reason.get("suggested_verdict") != "flaky":
        failures.append(f"loading forever: the result should carry the last still_loading and suggest flaky: {reason}")
    if "stuck_reason" in trace["steps"][-1]:
        failures.append("loading forever: the final look must not be asked stuck_reason")

    # 4e. Jev gives up right after a dead click: BLOCKED with blocked_reason `other` (no row of its own) on a step that
    #     was asked stuck_reason because the click changed nothing -> the result suggests bug from that second answer
    #     (measured live: a Finish button that does nothing ended `blocked` three times with no suggestion)
    spec = base_spec(url)
    out = os.path.join(tmp, "run-blocked-after-dead-click")
    trace = run(spec, FakeJev("blocked_after_dead_click"), out, screenshots=False)
    print(summarize(trace, out))
    print()
    steps = trace["steps"]
    reason = (trace["result"] or {}).get("reason") or {}
    if trace["status"] != "blocked" or len(steps) != 2 or steps[0].get("page_changed") is not False or "stuck_reason" not in steps[1]:
        failures.append(f"blocked after a dead click: expected a no-op click then BLOCKED asked stuck_reason, got {trace['status']} {[(s.get('page_changed'), 'stuck_reason' in s) for s in steps]}")
    if reason != {"status": "blocked", "blocked_reason": "other", "stuck_reason": "control_had_no_effect", "suggested_verdict": "bug"}:
        failures.append(f"blocked right after a no-op with blocked_reason other should suggest bug from stuck_reason: {reason}")

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

    # 13b. the budget's final look. Four actions reach the cart (cookies, type, enter, add), so with max_steps 4 the
    #      pass is first visible on the final look: undetermined, budget_exhausted, `pending_outcome` names it (no
    #      settle-and-recheck happened, so it is not a pass); with max_steps 5 the sighting at step 5 is rechecked by
    #      the final look and confirmed like any other pass (seen_at_step 6, first_seen 5); with auto_done false and
    #      Jev's DONE on the last step the final look confirms too.
    spec = outcome_spec(url)
    spec["budget"]["max_steps"] = 4
    out = os.path.join(tmp, "run-budget-first-seen")
    trace = run(spec, FakeJev(), out, screenshots="key")
    print(summarize(trace, out))
    print()
    res, last = trace["result"], trace["steps"][-1]
    if trace["status"] != "budget_exhausted" or res["outcome"] != "undetermined" or (res["reason"] or {}).get("pending_outcome") != "item_added":
        failures.append(f"budget: a pass first seen on the final look must stay undetermined and be named: {trace['status']} {res['outcome']} {res.get('reason')}")
    if not last.get("final_look") or last["n"] != 5 or last.get("pending_outcome") != "item_added" or not last.get("screenshot"):
        failures.append(f"budget: the final look should be step 5 with pending_outcome and a picture: {last.get('n')} {last.get('pending_outcome')} {last.get('screenshot')}")
    if res["confirmed"] or res["seen_at_step"] is not None or trace["final"].get("checks", {}).get("cart_has_item") != 1.0:
        failures.append(f"budget: nothing is confirmed, final.checks holds the last look: {res['confirmed']} {res['seen_at_step']} {trace['final']}")
    spec = outcome_spec(url)
    spec["budget"]["max_steps"] = 5
    out = os.path.join(tmp, "run-budget-confirmed")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    res = trace["result"]
    if trace["status"] != "passed" or (res["outcome"], res["confirmed"], res["first_seen_at_step"], res["seen_at_step"]) != ("item_added", True, 5, 6):
        failures.append(f"budget: a sighting on the last step is confirmed by the final look: {trace['status']} {res['outcome']} {res['confirmed']} {res['first_seen_at_step']} {res['seen_at_step']}")
    if not trace["steps"][-1].get("final_look") or trace["steps"][-1]["executed"] != {"action": "AUTO_DONE", "ok": True, "error": None, "confirmed": True}:
        failures.append(f"budget: the confirming final look should be the terminal step: {trace['steps'][-1].get('executed')}")
    if len(res["assertions"]) != 5 or not all(a["ok"] for a in res["assertions"]) or "Cart: 1 items" not in (res["evidence"]["line"] or ""):
        failures.append(f"budget: the confirmed pass runs the assertions and the adjudication: {res['assertions']} {res['evidence']}")
    spec = outcome_spec(url + "?fail=1")
    spec["budget"]["max_steps"] = 4
    out = os.path.join(tmp, "run-budget-bug")
    trace = run(spec, FakeJev(), out, screenshots=False)
    print(summarize(trace, out))
    print()
    res = trace["result"]
    if trace["status"] != "outcome" or (res["outcome"], res["verdict"], res["seen_at_step"]) != ("app_error", "bug", 5):
        failures.append(f"budget: a bug outcome on the final look is terminal like in the loop: {trace['status']} {res['outcome']} {res['seen_at_step']}")
    spec = base_spec(url)
    spec["auto_done"] = False
    spec["budget"]["max_steps"] = 5
    out = os.path.join(tmp, "run-budget-done")
    trace = run(spec, FakeJev("done_after_add"), out, screenshots=False)  # DONE right after the add: step 5, the last one
    print(summarize(trace, out))
    print()
    res = trace["result"]
    if trace["status"] != "passed" or (res["outcome"], res["confirmed"], res["seen_at_step"]) != ("goal_reached", True, 6):
        failures.append(f"budget: DONE on the last step with the pass in sight is confirmed by the final look (auto_done false): {trace['status']} {res['outcome']} {res['confirmed']} {res['seen_at_step']}")

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
    if "blocked_reason" in first or "stuck_reason" in first or any(s.get("reason_request") for s in trace["steps"]):
        failures.append(f"outcome pass: blocked_reason is asked only on a terminal step that needs it, stuck_reason only after a no-op action: {first.get('blocked_reason')} {first.get('stuck_reason')}")
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
    if res["seen_at_step"] != len(trace["steps"]) or res["first_seen_at_step"] != len(trace["steps"]):
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

    # 18. a two-sentence outcome statement: one evidence_line Choice per sentence rides in the one adjudication
    #     request, and the most confident sentence's line is quoted (here the second: the first names
    #     nothing the fixture shows and gets `none`)
    spec = outcome_spec(url)
    spec["outcomes"]["item_added"]["when"] = "The order can be placed now. The header shows the cart contains at least one item"
    jev = FakeJev()
    out = os.path.join(tmp, "run-outcome-sentences")
    trace = run(spec, jev, out, screenshots="key")
    print(summarize(trace, out))
    print()
    res = trace["result"]
    adj = trace.get("adjudication") or {}
    sentences = adj.get("sentences") or []
    if trace["status"] != "passed" or (res["outcome"], res["confirmed"]) != ("item_added", True):
        failures.append(f"sentences: expected the pass as before, got {trace['status']} {res['outcome']} {res['confirmed']}")
    if jev.requests != len(trace["steps"]) + 1:
        failures.append(f"sentences: the per-sentence Choices ride in the one adjudication request: {jev.requests} requests for {len(trace['steps'])} steps")
    if (len(sentences) != 2 or sentences[0].get("sentence") != "The order can be placed now" or sentences[0].get("line_id") != "none"
            or sentences[0].get("line") is not None or "Cart: 1 items" not in (sentences[1].get("line") or "")):
        failures.append(f"sentences: expected the first sentence unmatched and the second quoting the header: {sentences}")
    if "Cart: 1 items" not in (res["evidence"]["line"] or "") or (sentences and adj.get("line_id") != sentences[1].get("line_id")):
        failures.append(f"sentences: evidence.line should be the first sentence's line that was found: {res['evidence']} {adj}")
    if not (res["evidence"]["present"] or 0) >= 0.9:
        failures.append(f"sentences: evidence_present is still judged over the whole statement: {res['evidence']}")
    failures += result_shape_check(trace, out)

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
