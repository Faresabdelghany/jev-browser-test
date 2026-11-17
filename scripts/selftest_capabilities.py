"""Offline scenarios for the capabilities added in 0.4.0, run by selftest.py (or on their own).

    python scripts/selftest_capabilities.py

Local pages and a scripted stand-in for Jev, like the rest of the self-test: no key, no network beyond a
server on 127.0.0.1. One scenario per capability:

  A. browser diagnostics: an uncaught exception, a console error and a 500 response are recorded with the step they
     preceded, flagged in the summary, repeated in result.json, and fail `no_page_errors` / `no_failed_requests`;
     a clean run records nothing and passes both assertions
  B. teardown: runs after a pass and after a red run alike; a failing step is reported and changes nothing
  C. scripted steps: hover, check / uncheck, upload, drag, and `frame` on a step
  D. frames: the controls of a listed <iframe> join the table and are typed into and clicked (D2: a one-line frame 18 px tall too); an unlisted frame
     contributes nothing and the stalled run's summary says where to look
  E. device emulation: a phone's viewport, touch and user agent reach the page; an unknown device is exit-2 material
  F. new tabs: followed when the spec says so, flagged when it does not
  G. loading indicators: a spinner that covers nothing earns the extra undecided looks, and only those
  H. shadow DOM: controls inside a web component are counted for the hint; a scripted step reaches them
  I. JUnit: a pass, a bug and an environment failure map to no child, <failure> and <error>

and for the three interactions Jev drives itself since 0.5.0, each off until the spec asks:

  J. shadow DOM (`observation.shadow_dom`): the controls and the text inside open shadow roots, nested ones included,
     reach the table and the state; Jev types and clicks there; the evidence line and the assertions read there too
  K. uploads (`files`): UPLOAD_FILE is offered for a visible file field and for one the page hides; Jev picks the
     field and the file; without `files` nothing changes
  L. hover (`extra_operations: ["HOVER"]`): Jev opens a hover-only menu and clicks the item it reveals; without it
     the operation is never offered
  M. `evidence: "failures"`: a pass whose assertions hold costs one request fewer and says why it has no line; a bug,
     a pass without assertions and a pass whose assertions fail still get theirs
"""
from __future__ import annotations

import http.server
import json
import os
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from junit import render_junit, run_case, suite_cases  # noqa: E402
from run_test import BrowserUnavailable, exit_code, run  # noqa: E402
from summarize_trace import summarize  # noqa: E402


class ScriptedJev:
    """A stand-in for Jev that follows a script: a list of moves, each tried in order on every decision, the first
    whose `when` holds being played.

        ("click", "Save")                 click the first offered element whose description mentions "Save"
        ("type", "Card number", "card")   type data value `card` into the field described "Card number"
        ("hover", "Products")             move the pointer over the element described "Products" (needs HOVER offered)
        ("upload", "Resume", "cv")        attach the file named `cv` to the file field described "Resume"
        ("wait",)                         choose WAIT
        ("undecided",)                    choose WAIT at confidence 0.3 (the runner refuses to act on it)
    A move is played once (`once=True`, the default for click and type) and then skipped. When nothing applies the
    answer is DONE. The outcome Choice is answered by `outcome_rules`: {outcome name: substring of the page text}."""

    def __init__(self, moves: list[tuple], outcome_rules: dict[str, str] | None = None, undecided_while: str | None = None):
        self.moves = [list(m) for m in moves]
        self.played: set[int] = set()
        self.outcome_rules = outcome_rules or {}
        self.undecided_while = undecided_while  # text on the page while which every decision is an undecided WAIT
        self.requests = 0
        self.seen_states: list[dict] = []

    @staticmethod
    def _choice(label: str, options: dict, conf: float = 0.9) -> dict:
        others = [k for k in options if k != label]
        top = max(conf, 1 / len(options) + 0.01) if others else 1.0
        probs = {k: (1 - top) / len(others) for k in others}
        probs[label] = top
        return {"type": "choice", "choice": label, "confidence": conf, "probabilities": probs}

    @staticmethod
    def _find(options: dict, needle: str) -> str | None:
        for k, v in options.items():
            text = v if isinstance(v, str) else " ".join(str(x) for x in v.values()) if isinstance(v, dict) else str(v)
            if needle.lower() in text.lower():
                return k
        return None

    def system_one(self, state: dict, questions: dict) -> dict:
        self.requests += 1
        self.seen_states.append(state)
        text = state.get("visible_text", "") + " " + " ".join(a.get("text", "") for a in state.get("announcements") or [])
        answers: dict = {}
        usage = {"input_tokens": 300, "output_tokens": 30}
        line_keys = [k for k in questions if k == "evidence_line" or k.startswith("evidence_line_")]
        for key in line_keys:
            statement = questions[key]["instructions"]
            needle = next((v for n, v in self.outcome_rules.items() if v and v in json.dumps(statement)), None)
            hit = next((ln["id"] for ln in state.get("lines", []) if needle and needle in ln["text"]), "none")
            answers[key] = self._choice(hit, questions[key]["criteria"])
        if line_keys:
            answers["evidence_present"] = {"type": "noul", "noul": 0.95}
        for key, q in questions.items():
            if q["type"] == "noul" and key not in answers:
                answers[key] = {"type": "noul", "noul": 0.5}
        if "outcome" in questions:
            crit = questions["outcome"]["criteria"]
            seen = next((n for n, needle in self.outcome_rules.items() if n in crit and needle in text), "none_yet")
            answers["outcome"] = self._choice(seen, crit)
        for reason in ("stuck_reason", "blocked_reason"):
            if reason in questions:
                answers[reason] = self._choice(next(iter(questions[reason]["criteria"])), questions[reason]["criteria"])
        if "operation" not in questions:
            return {"answers": answers, "usage": usage, "model": "scripted-jev", "latency_ms": 1}
        ops = questions["operation"]["criteria"]
        clicks = questions.get("click_target", {}).get("criteria", {})
        types = questions.get("type_target", {}).get("criteria", {})
        hovers = questions.get("hover_target", {}).get("criteria", {})
        uploads = questions.get("upload_target", {}).get("criteria", {})
        if self.undecided_while and self.undecided_while in text:
            answers["operation"] = self._choice("WAIT", ops, conf=0.3)
            return {"answers": answers, "usage": usage, "model": "scripted-jev", "latency_ms": 1}
        for i, move in enumerate(self.moves):
            kind = move[0]
            if i in self.played:
                continue
            if kind == "click" and "CLICK" in ops and self._find(clicks, move[1]):
                self.played.add(i)
                answers["operation"] = self._choice("CLICK", ops)
                answers["click_target"] = self._choice(self._find(clicks, move[1]), clicks, 0.95)
                break
            if kind == "type" and "TYPE_TEXT" in ops and self._find(types, move[1]):
                self.played.add(i)
                answers["operation"] = self._choice("TYPE_TEXT", ops)
                answers["type_target"] = self._choice(self._find(types, move[1]), types, 0.95)
                answers["type_value"] = self._choice(move[2], questions["type_value"]["criteria"], 0.95)
                break
            if kind == "hover" and "HOVER" in ops and self._find(hovers, move[1]):
                self.played.add(i)
                answers["operation"] = self._choice("HOVER", ops)
                answers["hover_target"] = self._choice(self._find(hovers, move[1]), hovers, 0.95)
                break
            if kind == "upload" and "UPLOAD_FILE" in ops and self._find(uploads, move[1]):
                self.played.add(i)
                answers["operation"] = self._choice("UPLOAD_FILE", ops)
                answers["upload_target"] = self._choice(self._find(uploads, move[1]), uploads, 0.95)
                answers["upload_file"] = self._choice(move[2], questions["upload_file"]["criteria"], 0.95)
                break
            if kind == "wait" and "WAIT" in ops:
                self.played.add(i)
                answers["operation"] = self._choice("WAIT", ops)
                break
            if kind == "undecided":
                answers["operation"] = self._choice("WAIT", ops, conf=0.3)
                break
        else:
            answers["operation"] = self._choice("DONE", ops)
        return {"answers": answers, "usage": usage, "model": "scripted-jev", "latency_ms": 1}

    def usage_summary(self) -> dict:
        return {"jev_requests": self.requests, "input_tokens": 0, "output_tokens": 0, "model": "scripted-jev", "reconnects": 0}


def make_spec(url: str, **over) -> dict:
    from spec import DEFAULTS, _merge, validate

    spec = _merge(DEFAULTS, {
        "id": "capabilities",
        "start_url": url,
        "goal": "Save the form, so that the page says it was saved.",
        "outcomes": {"saved": {"when": "The page says 'Saved successfully'", "verdict": "pass"}},
        "budget": {"max_steps": 8, "max_seconds": 60},
        "browser": {"settle_ms": 300, "quiet_ms": 50, "action_timeout_ms": 3000},
    })
    spec = _merge(spec, over)
    problems = validate(spec)
    assert not problems, problems
    return spec


# ---------------------------------------------------------------------------------------------------------------------
# Pages. One small site on 127.0.0.1: the fetch to /api/save answers 500 on the faulty page and 200 on the healthy one.

APP_PAGE = """<!doctype html><html><head><title>App</title></head><body>
<h1>Profile</h1>
<label>Name <input id="name" value="Ada"></label>
<button id="save" type="button">Save</button>
<p id="msg"></p>
<script>
  const faulty = location.search.includes('faulty=1');
  document.getElementById('save').addEventListener('click', async () => {
    const r = await fetch('/api/save' + (faulty ? '?fail=1' : ''));
    document.getElementById('msg').textContent = r.ok ? 'Saved successfully' : 'Saved successfully';  // the page lies; the network does not
    if (faulty) { console.error('save handler: unexpected status ' + r.status); setTimeout(() => { throw new Error('render failed after save'); }, 0); }
  });
</script></body></html>"""

CLEANUP_PAGE = """<!doctype html><html><head><title>Cleanup</title></head><body>
<h1>Records</h1><p id="state">Record present</p>
<button id="save" type="button" onclick="document.getElementById('msg').textContent='Saved successfully'">Save</button>
<button id="delete" type="button" onclick="document.getElementById('state').textContent='Record deleted'; fetch('/api/deleted')">Delete record</button>
<p id="msg"></p></body></html>"""

STEPS_PAGE = """<!doctype html><html><head><title>Steps</title><style>
  #menu { display: none } #nav:hover #menu { display: block }
  #drop { width: 160px; height: 60px; border: 1px dashed #888 } #chip { width: 80px; height: 30px; background: #cde }
</style></head><body>
<div id="nav"><span id="nav-label">Account</span><div id="menu"><button id="settings" type="button"
  onclick="document.getElementById('log').textContent += ' menu-clicked'">Settings</button></div></div>
<label><input type="checkbox" id="terms"> Accept the terms</label>
<label><input type="checkbox" id="news" checked> Send me news</label>
<input type="file" id="cv" onchange="document.getElementById('log').textContent += ' file:' + this.files[0].name">
<div id="chip" draggable="true" ondragstart="event.dataTransfer.setData('text/plain', 'chip')">chip</div>
<div id="drop" ondragover="event.preventDefault()" ondrop="event.preventDefault(); document.getElementById('log').textContent += ' dropped:' + event.dataTransfer.getData('text/plain')">drop here</div>
<iframe id="inner" title="Inner form" srcdoc="<input id='code' placeholder='Code'><p id='echo'></p><script>document.getElementById('code').addEventListener('input', e => document.getElementById('echo').textContent = 'code:' + e.target.value)</script>" width="300" height="80"></iframe>
<button id="save" type="button" onclick="document.getElementById('msg').textContent='Saved successfully'">Save</button>
<p id="msg"></p><p id="log"></p></body></html>"""

CHECKOUT_PAGE = """<!doctype html><html><head><title>Checkout</title></head><body>
<h1>Checkout</h1><p>Enter your card to pay.</p>
<iframe id="card-frame" title="Secure card payment" src="/card" width="420" height="160"></iframe>
<iframe id="ad" title="Advert" srcdoc="<button>Buy more</button>" width="300" height="60"></iframe>
<p id="msg"></p>
<script>window.addEventListener('message', e => { if (e.data && e.data.paid) document.getElementById('msg').textContent = 'Saved successfully: ' + e.data.paid; });</script>
</body></html>"""

CARD_PAGE = """<!doctype html><html><head><title>Card form</title></head><body>
<label>Card number <input id="card" placeholder="Card number"></label>
<button id="pay" type="button" onclick="document.getElementById('status').textContent='Paid';
  parent.postMessage({paid: document.getElementById('card').value.slice(-4)}, '*')">Pay now</button>
<p id="status"></p></body></html>"""

SLIM_CHECKOUT_PAGE = """<!doctype html><html><head><title>Checkout</title></head><body>
<h1>Checkout</h1><p>Enter your card to pay.</p>
<iframe id="card-line" title="Secure card payment input frame" src="/card-line" width="323" height="18" style="border:0"></iframe>
<iframe id="pixel" title="Tracking" srcdoc="<button>Track</button>" width="1" height="1" style="border:0"></iframe>
<p id="msg"></p>
<script>window.addEventListener('message', e => { if (e.data && e.data.card) document.getElementById('msg').textContent = 'Saved successfully: ' + e.data.card; });</script>
</body></html>"""

CARD_LINE_PAGE = """<!doctype html><html><head><title>Card line</title><style>body{margin:0} input{height:18px;border:0;padding:0;margin:0;font-size:13px;width:300px}</style></head><body>
<input id="card" aria-label="Credit or debit card number" placeholder="Card number"
  oninput="if (this.value.length >= 16) parent.postMessage({card: this.value.slice(-4)}, '*')"></body></html>"""

DEVICE_PAGE = """<!doctype html><html><head><title>Device</title><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>
<p id="info"></p>
<button id="save" type="button" onclick="document.getElementById('msg').textContent='Saved successfully'">Save</button>
<p id="msg"></p>
<script>document.getElementById('info').textContent = 'width:' + window.innerWidth + ' touch:' + (navigator.maxTouchPoints > 0) + ' mobile:' + /Mobile/.test(navigator.userAgent);</script>
</body></html>"""

TABS_PAGE = """<!doctype html><html><head><title>Opener</title></head><body>
<h1>Invoices</h1><a id="open" href="/receipt" target="_blank">Open receipt</a></body></html>"""

RECEIPT_PAGE = """<!doctype html><html><head><title>Receipt</title></head><body>
<h1>Receipt</h1><button id="save" type="button" onclick="document.getElementById('msg').textContent='Saved successfully'">Save</button>
<p id="msg"></p></body></html>"""

SPINNER_PAGE = """<!doctype html><html><head><title>Spinner</title></head><body>
<h1>Report</h1><button id="unrelated" type="button">Help</button>
<div class="report-spinner" id="spin" style="width:24px;height:24px;border:3px solid #999;border-radius:50%"></div>
<p id="msg">Crunching the numbers</p>
<script>
  const ms = Number(new URLSearchParams(location.search).get('ms') || 2500);
  setTimeout(() => { document.getElementById('spin').remove(); document.getElementById('msg').textContent = 'Saved successfully'; }, ms);
</script></body></html>"""

SHADOW_PAGE = """<!doctype html><html><head><title>Shadow</title></head><body>
<h1>Widget</h1><my-widget id="host"></my-widget><p id="msg"></p>
<script>
  const root = document.getElementById('host').attachShadow({mode: 'open'});
  root.innerHTML = '<button id="inner-save" type="button">Save inside</button>';
  root.getElementById('inner-save').addEventListener('click', () => { document.getElementById('msg').textContent = 'Saved successfully'; });
</script></body></html>"""

# A profile form built as web components: the field and its label in one open shadow root, the Save button in a
# second root nested inside it, and the confirmation written into the outer root. Nothing a user needs is in the
# document's own tree except the heading.
SHADOW_APP_PAGE = """<!doctype html><html><head><title>Shadow app</title></head><body>
<h1>Profile</h1><profile-card id="card"></profile-card>
<script>
  customElements.define('save-button', class extends HTMLElement {
    connectedCallback() {
      const root = this.attachShadow({mode: 'open'});
      root.innerHTML = '<style>button{padding:6px}</style><button id="go" type="button">Save profile</button>';
      root.getElementById('go').addEventListener('click', () => this.dispatchEvent(new CustomEvent('save', {bubbles: true, composed: true})));
    }
  });
  customElements.define('profile-card', class extends HTMLElement {
    connectedCallback() {
      const root = this.attachShadow({mode: 'open'});
      root.innerHTML = '<style>p{margin:8px 0}</style><label for="nick">Nickname</label> <input id="nick">' +
                       '<save-button></save-button><p id="out"></p>';
      root.addEventListener('save', () => { root.getElementById('out').textContent = 'Saved successfully: ' + root.getElementById('nick').value; });
    }
  });
</script></body></html>"""

# Two file fields: one in plain sight with a label, one the page hides behind a styled label (display: none), the
# usual "Choose photo" button. Submit confirms only when both hold a file.
UPLOAD_PAGE = """<!doctype html><html><head><title>Upload</title><style>.btn{display:inline-block;padding:6px;border:1px solid #888;cursor:pointer}</style></head><body>
<h1>Application</h1>
<p><label for="cv">Resume</label> <input type="file" id="cv" accept=".txt,.pdf"></p>
<p><label for="photo" class="btn">Choose photo</label><input type="file" id="photo" name="photo" style="display:none"></p>
<button id="submit" type="button">Submit application</button>
<p id="log"></p><p id="msg"></p>
<script>
  for (const id of ['cv', 'photo']) document.getElementById(id).addEventListener('change', e => {
    document.getElementById('log').textContent += ' ' + id + '=' + e.target.files[0].name; });
  document.getElementById('submit').addEventListener('click', () => {
    const ok = document.getElementById('cv').files.length && document.getElementById('photo').files.length;
    document.getElementById('msg').textContent = ok ? 'Saved successfully' : 'Both files are required'; });
</script></body></html>"""

# A navigation bar whose submenu exists only while the pointer is over its parent item (CSS :hover, no script).
HOVER_PAGE = """<!doctype html><html><head><title>Hover menu</title><style>
  nav ul{list-style:none;margin:0;padding:0} nav > ul > li{display:inline-block;position:relative;padding:8px}
  .sub{display:none;position:absolute;left:0;top:100%;background:#fff;border:1px solid #888;padding:8px;width:160px}
  #products:hover .sub{display:block}
</style></head><body>
<nav><ul><li id="products"><a href="#products">Products</a><ul class="sub">
  <li><a href="#pricing" id="pricing" onclick="document.getElementById('msg').textContent='Saved successfully'">Pricing</a></li>
  <li><a href="#docs">Documentation</a></li></ul></li><li><a href="#about">About</a></li></ul></nav>
<h1>Welcome</h1><p id="msg"></p></body></html>"""

# The same menu opened the way jQuery UI opens one: by a script, 300 ms after the pointer arrives (its default delay).
HOVER_DELAY_PAGE = HOVER_PAGE.replace("#products:hover .sub{display:block}", "").replace("</body>", """<script>
const li = document.getElementById('products'), sub = li.querySelector('.sub'); let t;
li.addEventListener('mouseenter', () => { t = setTimeout(() => { sub.style.display = 'block'; }, 300); });
li.addEventListener('mouseleave', () => { clearTimeout(t); sub.style.display = 'none'; });
</script></body>""")

ROUTES = {"/hover-delay": HOVER_DELAY_PAGE, "/shadow-app": SHADOW_APP_PAGE, "/upload": UPLOAD_PAGE, "/hover": HOVER_PAGE, "/app": APP_PAGE, "/cleanup": CLEANUP_PAGE, "/steps": STEPS_PAGE, "/checkout": CHECKOUT_PAGE, "/card": CARD_PAGE, "/checkout-slim": SLIM_CHECKOUT_PAGE, "/card-line": CARD_LINE_PAGE,
          "/device": DEVICE_PAGE, "/tabs": TABS_PAGE, "/receipt": RECEIPT_PAGE, "/spinner": SPINNER_PAGE, "/shadow": SHADOW_PAGE}


class _Site(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []  # the paths requested, for the teardown scenario

    def log_message(self, *args) -> None:  # noqa: D401 - quiet
        pass

    def do_GET(self) -> None:  # noqa: N802 - the handler's name is the protocol's
        path = self.path.split("?", 1)[0]
        type(self).hits.append(self.path)
        if path == "/api/save":
            status, body, ctype = (500, '{"error": "boom"}', "application/json") if "fail=1" in self.path else (200, '{"ok": true}', "application/json")
        elif path == "/api/deleted":
            status, body, ctype = 200, "{}", "application/json"
        elif path == "/favicon.ico":
            status, body, ctype = 204, "", "image/x-icon"
        elif path in ROUTES:
            status, body, ctype = 200, ROUTES[path], "text/html; charset=utf-8"
        else:
            status, body, ctype = 404, "not found", "text/plain"
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start_site() -> tuple[str, type]:
    handler = type("CapabilitiesSite", (_Site,), {"hits": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", handler


SAVED = {"saved": "Saved successfully"}


def flags_of(trace: dict, out: str) -> str:
    return summarize(trace, out)


def run_checks(tmp: str | None = None) -> list[str]:
    tmp = tmp or tempfile.mkdtemp(prefix="jev-capabilities-")
    base, site = start_site()
    failures: list[str] = []

    def go(name: str, spec: dict, jev: ScriptedJev) -> tuple[dict, str]:
        out = os.path.join(tmp, f"cap-{name}")
        trace = run(spec, jev, out, screenshots=False)
        print(summarize(trace, out))
        print()
        return trace, out

    # A. diagnostics ---------------------------------------------------------------------------------------------------
    spec = make_spec(base + "/app?faulty=1", **{"assert": [{"text_contains": "Saved successfully"}, {"no_page_errors": True},
                                                            {"no_failed_requests": True}], "confirm": "recheck"})
    trace, out = go("diag-faulty", spec, ScriptedJev([("click", "Save")], SAVED))
    diag = trace.get("diagnostics") or {}
    counts = diag.get("counts") or {}
    if (counts.get("page_errors"), counts.get("server_errors"), counts.get("console_errors")) != (1, 1, 1):
        failures.append(f"A: expected one exception, one 5xx and one console error, got {counts}")
    if not (diag.get("page_errors") or [{}])[0].get("text", "").endswith("render failed after save"):
        failures.append(f"A: the exception's message is not in trace.diagnostics: {diag.get('page_errors')}")
    if any(e.get("step") != 2 for kind in ("page_errors", "http_errors", "console_errors") for e in diag.get(kind, [])):
        failures.append(f"A: every entry should be stamped with step 2, the first look after the click: {diag}")
    if trace["status"] != "assert_failed":
        failures.append(f"A: the page says saved but the two diagnostic assertions must fail the pass: {trace['status']}")
    failed = [next(k for k in a if k not in ("ok", "actual")) for a in trace["result"]["assertions"] if not a["ok"]]
    if failed != ["no_page_errors", "no_failed_requests"]:
        failures.append(f"A: failed assertions should be the two diagnostic ones, got {failed}")
    rd = trace["result"].get("diagnostics") or {}
    if not (rd.get("server_errors") and rd["server_errors"][0]["status"] == 500 and rd.get("page_errors")):
        failures.append(f"A: result.json should repeat the 5xx and the exception: {rd}")
    text = flags_of(trace, out)
    if not all(f in text for f in ("JS-ERROR:1", "HTTP-5xx:1", "CONSOLE-ERR:1", "browser diagnostics:")):
        failures.append("A: the summary should flag JS-ERROR, HTTP-5xx and CONSOLE-ERR and print the diagnostics line")
    spec = make_spec(base + "/app", **{"assert": [{"no_page_errors": True}, {"no_failed_requests": True}]})
    trace, out = go("diag-clean", spec, ScriptedJev([("click", "Save")], SAVED))
    if trace["status"] != "passed" or "diagnostics" in trace or "diagnostics" in trace["result"]:
        failures.append(f"A: a clean run passes both assertions and records no diagnostics: {trace['status']} {trace.get('diagnostics')}")

    # B. teardown ------------------------------------------------------------------------------------------------------
    td = [{"action": "click", "selector": "#delete"}, {"action": "wait_for", "selector": "text=Record deleted"}]
    site.hits.clear()
    trace, out = go("teardown-pass", make_spec(base + "/cleanup", teardown=td), ScriptedJev([("click", "Save")], SAVED))
    if trace["status"] != "passed" or trace["result"].get("teardown") != {"ok": True, "steps": 2, "ran": 2}:
        failures.append(f"B: teardown after a pass: {trace['status']} {trace['result'].get('teardown')}")
    if not any(h.startswith("/api/deleted") for h in site.hits):
        failures.append("B: the teardown's click never reached the page")
    if "teardown_ms" not in trace["timing"] or "teardown: 2/2" not in flags_of(trace, out):
        failures.append("B: timing.teardown_ms and the summary's teardown line are missing")
    site.hits.clear()
    red = make_spec(base + "/cleanup", teardown=td, outcomes={"saved": {"when": "The page says 'Never shown here'", "verdict": "pass"}})
    trace, out = go("teardown-red", red, ScriptedJev([("click", "Save")], {"saved": "Never shown here"}))
    if trace["status"] == "passed" or not any(h.startswith("/api/deleted") for h in site.hits):
        failures.append(f"B: the teardown must run after a red run too: {trace['status']} hits={site.hits}")
    bad = [{"action": "click", "selector": "#no-such-button"}, {"action": "click", "selector": "#delete"}]
    trace, out = go("teardown-fails", make_spec(base + "/cleanup", teardown=bad, browser={"action_timeout_ms": 500}),
                    ScriptedJev([("click", "Save")], SAVED))
    t = trace["result"].get("teardown") or {}
    if trace["status"] != "passed" or exit_code(trace) != 0 or t.get("ok") is not False or (t.get("failed") or {}).get("n") != 0 or t.get("ran") != 0:
        failures.append(f"B: a failing teardown step is reported and the pass stands: {trace['status']} {t}")

    # C. scripted steps --------------------------------------------------------------------------------------------------
    upload = os.path.join(tmp, "cv-sample.txt")
    with open(upload, "w", encoding="utf-8") as f:
        f.write("sample")
    setup = [
        {"action": "hover", "selector": "#nav"},
        {"action": "click", "selector": "#settings"},
        {"action": "check", "selector": "#terms"},
        {"action": "uncheck", "selector": "#news"},
        {"action": "upload", "selector": "#cv", "path": upload},
        {"action": "drag", "selector": "#chip", "to": "#drop"},
        {"action": "fill", "frame": "#inner", "selector": "#code", "value": "4711"},
        {"action": "wait_for", "frame": "#inner", "selector": "text=code:4711"},
    ]
    spec = make_spec(base + "/steps", setup=setup, **{"assert": [
        {"text_in": {"selector": "#log", "contains": "menu-clicked"}},
        {"text_in": {"selector": "#log", "contains": "file:cv-sample.txt"}},
        {"text_in": {"selector": "#log", "contains": "dropped:chip"}},
        {"text_in": {"frame": "#inner", "selector": "#echo", "equals": "code:4711"}},
    ]})
    trace, out = go("steps", spec, ScriptedJev([("click", "Save")], SAVED))
    if trace["status"] != "passed" or not all(s["ok"] for s in trace["setup"]) or len(trace["setup"]) != len(setup):
        failures.append(f"C: hover / check / uncheck / upload / drag / frame steps: {trace['status']} "
                        f"{[(s['action'], s['error']) for s in trace['setup'] if not s['ok']]} {trace['result']['assertions']}")
    boxes = {e.get("name"): e.get("checked") for e in trace["steps"][0]["elements"] if e["role"] == "checkbox"}
    if boxes != {"Accept the terms": True, "Send me news": False}:
        failures.append(f"C: check / uncheck should leave terms ticked and news cleared: {boxes}")
    spec = make_spec(base + "/steps", setup=[{"action": "upload", "selector": "#cv", "path": os.path.join(tmp, "missing.pdf")}])
    trace, out = go("steps-missing-file", spec, ScriptedJev([], SAVED))
    if exit_code(trace) != 2 or "no such file" not in (trace["setup"][0].get("error") or ""):
        failures.append(f"C: a missing upload file is a setup failure (exit 2) that names the file: {trace['setup']}")

    # D. frames ----------------------------------------------------------------------------------------------------------
    pay = make_spec(base + "/checkout", goal="Pay with the card, so that the page says it was saved.", data={"card": "4242424242421881"},
                    observation={"frames": ["#card-frame"]},
                    **{"assert": [{"text_contains": "Saved successfully: 1881"}, {"text_in": {"frame": "#card-frame", "selector": "#status", "equals": "Paid"}}]})
    jev = ScriptedJev([("type", "Card number", "card"), ("click", "Pay now")], SAVED)
    trace, out = go("frames", pay, jev)
    first = trace["steps"][0]
    in_frame = [e for e in first["elements"] if e.get("frame") == "#card-frame"]
    if trace["status"] != "passed":
        failures.append(f"D: typing and clicking inside a listed frame should pass: {trace['status']} {trace.get('error')} {trace['result']['assertions']}")
    if sorted(e["role"] for e in in_frame) != ["button", "textbox"] or not all((e.get("context") or "") == "frame: Secure card payment" for e in in_frame):
        failures.append(f"D: the frame's two controls should be in the table, named with their frame: {in_frame}")
    if any(e.get("name") == "Buy more" for e in first["elements"]):
        failures.append("D: the unlisted advert frame must contribute nothing")
    if first.get("frames") != [{"selector": "#card-frame", "elements": 2, "label": "Secure card payment", "url": base + "/card"}]:
        failures.append(f"D: step.frames should say what the frame contributed: {first.get('frames')}")
    if len({e["idx"] for e in first["elements"]}) != len(first["elements"]):
        failures.append("D: element indices must be unique across the page and its frames")
    acted = [s["executed"] for s in trace["steps"] if s.get("executed", {}).get("action") in ("TYPE_TEXT", "CLICK")]
    if [a.get("frame") for a in acted] != ["#card-frame", "#card-frame"] or not all(a["ok"] for a in acted):
        failures.append(f"D: both actions should have run inside the frame: {acted}")
    if "Card number" not in jev.seen_states[0]["visible_text"] and "Paid" not in jev.seen_states[-1]["visible_text"]:
        failures.append("D: the frame's visible text should reach Jev's state")
    unlisted = make_spec(base + "/checkout", goal=pay["goal"], data=pay["data"], budget={"max_steps": 3, "max_seconds": 30})
    trace, out = go("frames-unlisted", unlisted, ScriptedJev([("undecided",)], SAVED))
    if any(e.get("frame") for s in trace["steps"] for e in s["elements"]) or "observation.frames" not in flags_of(trace, out):
        failures.append("D: without observation.frames nothing of a frame is offered, and a stalled run's summary names the option")
    gone = make_spec(base + "/app", observation={"frames": ["#not-on-this-page"]})
    trace, out = go("frames-absent", gone, ScriptedJev([("click", "Save")], SAVED))
    if trace["status"] != "passed" or trace["steps"][0].get("frames") != [{"selector": "#not-on-this-page", "elements": 0, "skipped": "no element matches"}]:
        failures.append(f"D: a listed frame that is not on the page is skipped, not an error: {trace['status']} {trace['steps'][0].get('frames')}")

    # D2. a one-line frame (live, 0.5.0: Stripe's card element is an iframe 323 x 18 px, skipped under the old 40 x 20 floor)
    slim = make_spec(base + "/checkout-slim", goal="Type the card number, so that the page says it was saved.", data={"card": "4242424242424242"},
                     observation={"frames": ["#card-line", "#pixel"]}, **{"assert": [{"text_contains": "Saved successfully: 4242"}]})
    trace, out = go("frames-one-line", slim, ScriptedJev([("type", "Credit or debit card number", "card")], SAVED))
    first = trace["steps"][0]
    got = {f["selector"]: f.get("elements", 0) for f in first.get("frames") or []}
    if trace["status"] != "passed" or got.get("#card-line") != 1:
        failures.append(f"D2: a listed one-line frame 18 px tall is observed and typed into: {trace['status']} {first.get('frames')}")
    if got.get("#pixel") or "smaller than" not in str([f.get("skipped") for f in first.get("frames") or []]):
        failures.append(f"D2: a 1 x 1 frame is still skipped, and says why: {first.get('frames')}")

    # E. device emulation ------------------------------------------------------------------------------------------------
    phone = make_spec(base + "/device", browser={"device": "iPhone 13"}, **{"assert": [{"text_in": {"selector": "#info", "equals": "width:390 touch:true mobile:true"}}]})
    trace, out = go("device", phone, ScriptedJev([("click", "Save")], SAVED))
    if trace["status"] != "passed" or trace["browser"].get("device") != "iPhone 13" or "device: iPhone 13" not in flags_of(trace, out):
        failures.append(f"E: an iPhone 13 should give the page a 390 px touch viewport: {trace['status']} {trace['result']['assertions']} {trace.get('browser')}")
    try:
        run(make_spec(base + "/device", browser={"device": "iPhone 13 Ultra Max"}), ScriptedJev([], SAVED), os.path.join(tmp, "cap-device-unknown"), screenshots=False)
        failures.append("E: an unknown device should raise BrowserUnavailable")
    except BrowserUnavailable as e:
        if "iPhone 13" not in str(e) or os.path.exists(os.path.join(tmp, "cap-device-unknown")):
            failures.append(f"E: the error should suggest close device names and leave no run directory: {e}")

    # F. new tabs --------------------------------------------------------------------------------------------------------
    follow = make_spec(base + "/tabs", browser={"follow_new_tabs": True}, **{"assert": [{"url_matches": "**/receipt"}]})
    trace, out = go("tabs-follow", follow, ScriptedJev([("click", "Open receipt"), ("click", "Save")], SAVED))
    opener = next((s for s in trace["steps"] if s.get("new_tab")), {})
    if trace["status"] != "passed" or opener.get("new_tab") != {"followed": True, "url": base + "/receipt"} or not trace["final"]["url"].endswith("/receipt"):
        failures.append(f"F: with follow_new_tabs the run carries on in the new tab: {trace['status']} {opener.get('new_tab')} {trace['final'].get('url')}")
    stay = make_spec(base + "/tabs", budget={"max_steps": 3, "max_seconds": 30})
    trace, out = go("tabs-stay", stay, ScriptedJev([("click", "Open receipt")], SAVED))
    opener = next((s for s in trace["steps"] if s.get("new_tab")), {})
    if (opener.get("new_tab") or {}).get("followed") is not False or not trace["final"]["url"].endswith("/tabs") or "NEW-TAB(not followed)" not in flags_of(trace, out):
        failures.append(f"F: by default the run stays on its page and flags the new tab: {opener.get('new_tab')} {trace['final'].get('url')}")

    # G. loading indicators ----------------------------------------------------------------------------------------------
    # undecided for as long as the spinner runs (2.5 s): three undecided looks at 300 ms x 1, 2 wait 0.9 s and end the run
    # without the indicator rule; with it the limit is five looks (0.3 + 0.6 + 1.2 + 1.2 s) and the page finishes first
    spin = make_spec(base + "/spinner?ms=2500", goal="Wait for the report, so that the page says it was saved.")
    trace, out = go("spinner", spin, ScriptedJev([], SAVED, undecided_while="Crunching the numbers"))
    looks = [s for s in trace["steps"] if s.get("low_confidence")]
    if trace["status"] != "passed" or len(looks) < 4 or not all(s.get("loading_indicators") == 1 for s in looks):
        failures.append(f"G: a spinner that covers nothing should earn the extra undecided looks: {trace['status']} "
                        f"{[(s['n'], s.get('low_streak'), s.get('loading_indicators')) for s in trace['steps']]}")
    if any(s.get("action_deferred") or s.get("recheck_again") for s in trace["steps"]):
        failures.append("G: a loading indicator must not defer actions or extend the confirmation")
    plain = make_spec(base + "/app", budget={"max_steps": 8, "max_seconds": 30})
    trace, out = go("no-spinner", plain, ScriptedJev([("undecided",)], SAVED))
    if trace["status"] != "low_confidence" or len(trace["steps"]) != 3 or any(s.get("loading_indicators") for s in trace["steps"]):
        failures.append(f"G: a page with no indicator keeps the three-look limit: {trace['status']} {len(trace['steps'])} steps")

    # H. shadow DOM --------------------------------------------------------------------------------------------------------
    shadow = make_spec(base + "/shadow", budget={"max_steps": 3, "max_seconds": 30}, observation={"shadow_dom": False})
    trace, out = go("shadow-hint", shadow, ScriptedJev([("undecided",)], SAVED))
    if trace["steps"][-1].get("shadow_hosts") != 1 or "shadow DOM" not in flags_of(trace, out):
        failures.append(f"H: a stalled run on a page with controls in shadow DOM should say so: {trace['steps'][-1].get('shadow_hosts')}")
    scripted = make_spec(base + "/shadow", setup=[{"action": "click", "selector": "#inner-save"}])
    trace, out = go("shadow-setup", scripted, ScriptedJev([], SAVED))
    if trace["status"] != "passed":
        failures.append(f"H: a scripted step reaches a control inside an open shadow root: {trace['status']} {trace['setup']}")

    # I. JUnit -------------------------------------------------------------------------------------------------------------
    green = {"spec_id": "login", "outcome": "logged_in", "verdict": "pass", "status": "passed", "evidence": {"line": "Welcome"}, "duration_ms": 6100}
    bug = {"spec_id": "sort", "outcome": "unsorted", "verdict": "bug", "status": "outcome", "evidence": {"line": "Backpack \x0b$29.99"}, "duration_ms": 9000,
           "trace": "runs/sort/trace.json"}
    env = {"spec_id": "slow", "outcome": "undetermined", "verdict": None, "status": "error",
           "reason": {"phase": "navigation", "error": "Page.goto: Timeout", "suggested_verdict": "flaky"}}
    xml = render_junit("suite", [run_case(green, 0), run_case(bug, 1), run_case(env, 2)])
    root = ET.fromstring(xml.split("\n", 1)[1])
    cases = {c.get("name"): c for c in root.iter("testcase")}
    suite_el = root.find("testsuite")
    if (suite_el.get("tests"), suite_el.get("failures"), suite_el.get("errors")) != ("3", "1", "1"):
        failures.append(f"I: counts should be 3 tests, 1 failure, 1 error: {suite_el.attrib}")
    if cases["login"].find("failure") is not None or cases["login"].find("error") is not None or cases["login"].get("time") != "6.100":
        failures.append("I: a pass is a test case with no failure and its duration in seconds")
    f_el = cases["sort"].find("failure")
    if f_el is None or f_el.get("type") != "bug" or "Backpack $29.99" not in (f_el.get("message") or "") or "runs/sort/trace.json" not in (f_el.text or ""):
        failures.append(f"I: a bug is a <failure type=bug> with the evidence line (control characters dropped) and the trace path: {xml}")
    e_el = cases["slow"].find("error")
    if e_el is None or e_el.get("type") != "environment" or "navigation" not in (e_el.get("message") or ""):
        failures.append("I: an exit-2 run is an <error type=environment>, never a failure")
    report = {"specs": {
        "a": {"verdict": "pass", "runs": [{"run": 1, "outcome": "ok", "status": "passed", "wall_ms": 1000}], "outcome_counts": {"ok": 1}},
        "b": {"verdict": "flaky", "runs": [{"run": 1, "outcome": "ok", "status": "passed", "wall_ms": 1000},
                                           {"run": 2, "outcome": "undetermined", "status": "stuck", "wall_ms": 2000}],
              "outcome_counts": {"ok": 1, "undetermined": 1}},
        "c": {"verdict": "undetermined", "reason": "every run failed before observing a page",
              "runs": [{"run": 1, "environment_failure": True, "status": "error", "error": "could not launch", "wall_ms": 10}]},
    }}
    kinds = {c["name"]: (c["kind"], c["type"]) for c in suite_cases(report)}
    if kinds != {"a": ("pass", None), "b": ("failure", "flaky"), "c": ("error", "environment")}:
        failures.append(f"I: suite verdicts should map to pass / failure(flaky) / error(environment): {kinds}")
    # J. shadow DOM, driven by Jev -------------------------------------------------------------------------------------------
    deep = make_spec(base + "/shadow-app", goal="Set the nickname and save the profile, so that the page says it was saved.",
                     data={"nickname": "Ada"}, observation={"shadow_dom": True},
                     **{"assert": [{"text_contains": "Saved successfully: Ada"}, {"text_in": {"selector": "#out", "equals": "Saved successfully: Ada"}},
                                   {"field_value": {"label": "Nickname", "equals": "Ada"}}, {"element_present": {"role": "button", "name": "Save profile"}}]})
    jev = ScriptedJev([("type", "Nickname", "nickname"), ("click", "Save profile")], SAVED)
    trace, out = go("shadow-driven", deep, jev)
    first = trace["steps"][0]
    table = {(e["role"], e.get("name")) for e in first["elements"]}
    if trace["status"] != "passed":
        failures.append(f"J: typing and clicking inside (nested) shadow roots should pass: {trace['status']} {trace.get('error')} {trace['result']['assertions']}")
    if not {("textbox", "Nickname"), ("button", "Save profile")} <= table:
        failures.append(f"J: the field (named by its label in the same root) and the button in the nested root should be offered: {sorted(table)}")
    if first.get("covered_controls") or first.get("shadow_hosts"):
        failures.append(f"J: a control inside a shadow root is not covered by its own host, and no hint is due: {first.get('covered_controls')} {first.get('shadow_hosts')}")
    page_states = [st for st in jev.seen_states if "visible_text" in st]  # the evidence request's state has lines instead
    if "Nickname" not in page_states[0]["visible_text"] or "Saved successfully: Ada" not in page_states[-1]["visible_text"]:
        failures.append("J: the text inside shadow roots should reach Jev's state")
    if trace["result"]["evidence"]["line"] != "Saved successfully: Ada":
        failures.append(f"J: the evidence line should be quoted from inside the shadow root: {trace['result']['evidence']}")
    acted = [s["executed"] for s in trace["steps"] if s.get("executed", {}).get("action") in ("TYPE_TEXT", "CLICK")]
    if len(acted) != 2 or not all(a["ok"] for a in acted) or any(s.get("stale") for s in trace["steps"]):
        failures.append(f"J: both actions should land, with no stale decision (the fingerprint re-reads the shadow nodes): {acted}")
    shallow = make_spec(base + "/shadow-app", goal=deep["goal"], data=deep["data"], budget={"max_steps": 3, "max_seconds": 30},
                        observation={"shadow_dom": False})
    by_default = make_spec(base + "/shadow-app", goal=deep["goal"], data=deep["data"], **{"assert": deep["assert"]})  # 0.6.0: on unless a spec turns it off
    trace, out = go("shadow-default", by_default, ScriptedJev([("type", "Nickname", "nickname"), ("click", "Save profile")], SAVED))
    if trace["status"] != "passed":
        failures.append(f"J: shadow DOM is observed by default (0.6.0): {trace['status']} {trace.get('error')}")
    trace, out = go("shadow-off", shallow, ScriptedJev([("type", "Nickname", "nickname"), ("click", "Save profile"), ("undecided",)], SAVED))
    if trace["status"] == "passed" or any(e.get("name") in ("Nickname", "Save profile") for s in trace["steps"] for e in s["elements"]) \
            or "shadow DOM" not in flags_of(trace, out):
        failures.append(f"J: without observation.shadow_dom the shadow controls are not offered and the stalled run says so: {trace['status']}")

    # K. uploads, driven by Jev ------------------------------------------------------------------------------------------------
    photo = os.path.join(tmp, "photo-sample.png")
    with open(photo, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
    apply = make_spec(base + "/upload", goal="Attach the resume and the photo and submit, so that the page says it was saved.",
                      files={"resume": upload, "photo": photo},
                      **{"assert": [{"text_in": {"selector": "#log", "contains": "cv=cv-sample.txt"}}, {"text_in": {"selector": "#log", "contains": "photo=photo-sample.png"}}]})
    jev = ScriptedJev([("upload", "Resume", "resume"), ("upload", "photo", "photo"), ("click", "Submit application")], SAVED)
    trace, out = go("upload-driven", apply, jev)
    first = trace["steps"][0]
    fields = {e.get("name"): e for e in first["elements"] if e["role"] == "file"}
    if trace["status"] != "passed":
        failures.append(f"K: attaching two files and submitting should pass: {trace['status']} {trace.get('error')} {trace['result']['assertions']} {trace['result']['story']}")
    if set(fields) != {"Resume", "Choose photo"} or not fields.get("Choose photo", {}).get("hidden") or fields.get("Resume", {}).get("hidden"):
        failures.append(f"K: both file fields should be offered, the hidden one marked so and named by its label: {fields}")
    if "UPLOAD_FILE" not in first["offered_operations"] or jev.seen_states[0].get("available_files") != [
            {"key": "resume", "name": "cv-sample.txt"}, {"key": "photo", "name": "photo-sample.png"}]:
        failures.append(f"K: UPLOAD_FILE and the files (key and name, never the path) should be offered: {first['offered_operations']} {jev.seen_states[0].get('available_files')}")
    if tmp in json.dumps(jev.seen_states):
        failures.append("K: a file's path must not reach Jev's state")
    ups = [s for s in trace["steps"] if (s.get("executed") or {}).get("action") == "UPLOAD_FILE"]
    if [(u["executed"].get("file_key"), u["executed"].get("file"), u["executed"]["ok"]) for u in ups] != [
            ("resume", "cv-sample.txt", True), ("photo", "photo-sample.png", True)]:
        failures.append(f"K: the two uploads should be recorded with the file's key and name: {[u['executed'] for u in ups]}")
    after = {e.get("name"): e.get("value") for e in trace["steps"][2]["elements"] if e["role"] == "file"}
    if after != {"Resume": "(file: cv-sample.txt)", "Choose photo": "(file: photo-sample.png)"}:
        failures.append(f"K: an attached file should show as the field's content: {after}")
    story = trace["result"]["story"]
    if len(story) < 2 or not story[0].endswith("<- file resume") or not story[1].endswith("<- file photo"):
        failures.append(f"K: the story should name the file attached at each upload: {story}")
    plain = make_spec(base + "/upload", goal=apply["goal"], budget={"max_steps": 2, "max_seconds": 30})
    trace, out = go("upload-off", plain, ScriptedJev([("undecided",)], SAVED))
    first = trace["steps"][0]
    if "UPLOAD_FILE" in first["offered_operations"] or [e.get("name") for e in first["elements"] if e["role"] == "file"] != ["Resume"]:
        failures.append(f"K: without `files` no upload is offered and the hidden field stays out of the table: {first['offered_operations']}")

    # L. hover, driven by Jev ----------------------------------------------------------------------------------------------------
    menu = make_spec(base + "/hover", goal="Open Products and choose Pricing, so that the page says it was saved.", extra_operations=["HOVER"])
    jev = ScriptedJev([("hover", "Products"), ("click", "Pricing")], SAVED)
    trace, out = go("hover-driven", menu, jev)
    ops = [(s.get("executed") or {}).get("action") for s in trace["steps"]]
    if trace["status"] != "passed" or ops[:2] != ["HOVER", "CLICK"]:
        failures.append(f"L: hovering the menu and clicking the item it reveals should pass: {trace['status']} {ops} {trace.get('error')}")
    if any(e.get("name") == "Pricing" for e in trace["steps"][0]["elements"]) or not any(e.get("name") == "Pricing" for e in trace["steps"][1]["elements"]):
        failures.append("L: the submenu item should be offered only after the hover")
    if trace["steps"][0].get("page_changed") is not True:
        failures.append("L: the hover changed what Jev sees, so it is not a no-effect action")
    slow = make_spec(base + "/hover-delay", goal=menu["goal"], extra_operations=["HOVER"])
    trace, out = go("hover-delayed", slow, ScriptedJev([("hover", "Products"), ("click", "Pricing")], SAVED))
    hovered = [s for s in trace["steps"] if (s.get("executed") or {}).get("action") == "HOVER"]
    if trace["status"] != "passed" or not hovered or (hovered[0]["executed"].get("reveal") or {}).get("ended") != "changed" \
            or hovered[0].get("no_effect") or hovered[0].get("page_changed") is not True:
        failures.append(f"L: a menu that opens 300 ms after the hover is waited for, not flagged NO-EFFECT: {trace['status']} "
                        f"{[h['executed'].get('reveal') for h in hovered]}")
    still = make_spec(base + "/hover", goal=menu["goal"], budget={"max_steps": 2, "max_seconds": 30})
    trace, out = go("hover-off", still, ScriptedJev([("hover", "Products"), ("click", "Pricing"), ("undecided",)], SAVED))
    if any("HOVER" in s["offered_operations"] for s in trace["steps"]) or "hover_target" in json.dumps(trace["steps"][0].get("target") or {}):
        failures.append("L: without extra_operations HOVER is never offered")
    # M. evidence: "failures" ---------------------------------------------------------------------------------------------------
    counts = {}
    for mode in ("always", "failures"):
        jev = ScriptedJev([("click", "Save")], SAVED)
        trace, out = go(f"evidence-{mode}", make_spec(base + "/app", evidence=mode, **{"assert": [{"text_contains": "Saved successfully"}]}), jev)
        counts[mode] = (trace["status"], jev.requests, trace["result"]["evidence"].get("line"), trace["result"]["evidence"].get("skipped"))
    if counts["always"][:3] != ("passed", 3, "Saved successfully") or counts["always"][3] is not None:
        failures.append(f"M: by default a pass gets its evidence line in one more request: {counts['always']}")
    if counts["failures"][:3] != ("passed", 2, None) or not counts["failures"][3]:
        failures.append(f"M: with evidence 'failures' a pass whose assertions hold makes one request fewer and says why it has no line: {counts['failures']}")
    if "line not asked" not in flags_of(trace, out):
        failures.append("M: the summary should say the line was not asked")
    jev = ScriptedJev([("click", "Save")], SAVED)
    trace, out = go("evidence-no-assert", make_spec(base + "/app", evidence="failures"), jev)
    if trace["status"] != "passed" or trace["result"]["evidence"]["line"] != "Saved successfully":
        failures.append(f"M: a pass with no assertions has nothing else to prove it and keeps its line: {trace['status']} {trace['result']['evidence']}")
    jev = ScriptedJev([("click", "Save")], SAVED)
    wrong = make_spec(base + "/app", evidence="failures", confirm="recheck", **{"assert": [{"url_matches": "**/somewhere-else"}]})
    trace, out = go("evidence-assert-fails", wrong, jev)
    if trace["status"] != "assert_failed" or trace["result"]["evidence"]["line"] != "Saved successfully":
        failures.append(f"M: a pass whose assertions fail is a failure and gets its line: {trace['status']} {trace['result']['evidence']}")
    bug = make_spec(base + "/app", evidence="failures", outcomes={"saved": {"when": "The page says 'Never shown here'", "verdict": "pass"},
                                                                 "said_saved": {"when": "The page says 'Saved successfully'", "verdict": "bug", "requires_action": True}},
                    **{"assert": [{"text_contains": "Saved"}]})
    jev = ScriptedJev([("click", "Save")], {"said_saved": "Saved successfully"})
    trace, out = go("evidence-bug", bug, jev)
    if (trace["outcome"], trace["result"]["evidence"]["line"]) != ("said_saved", "Saved successfully"):
        failures.append(f"M: an outcome that is not a pass always gets its line: {trace['outcome']} {trace['result']['evidence']}")
    return failures


def main() -> int:
    from spec import utf8_stdio
    utf8_stdio()
    failures = run_checks()
    if failures:
        print("CAPABILITIES SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("CAPABILITIES SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
