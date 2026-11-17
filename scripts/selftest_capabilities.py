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

and for the spec language:

  N. `${DATE...}`: a spec file with a date placeholder is loaded for a given day, the date it names is what Jev is
     offered and types, the assertion written with the same placeholder reads it back, and the trace says what each
     placeholder became; RUN_DATE in the environment moves the day

and for what a run takes over from an earlier one (`session`, `browser.http_cache`, both off until asked):

  R. sessions and the HTTP cache: the first run with a `login` block logs in and saves the session, the next starts
     logged in and skips the login; a session the application no longer accepts is thrown away and the run logs in
     again; another account is another session; `"session": "never"` logs in every time. With the HTTP cache a
     script is fetched once over two runs while cookies and stored state start empty in each, and a saved session
     works on the cache profile too

and for the settle (`browser.settle: "network"`, off until the spec or --settle network asks):

  Q. network-aware settle: after a click that fetches its answer the settle waits for the response, so the next look
     already shows it; a connection opened before the action and an analytics call are not waited for; a request that
     outlasts the cap ends the settle at the cap and says what was left; the default settle is what it was

and for one request per form (`batch_fields`, off until the spec or --batch-fields asks):

  P. form batch: the request that types a form's first field assigns the others their values, and they are typed with
     no further request; a field that appears, a message and a list of suggestions each end the batch and hand the
     next decision back to Jev; without the option the per-field questions are never asked

and for the saved path (`replay`, off until the spec or --replay asks):

  O. replay: a passing run saves its path without the value it typed; the same pages replay every step with one
     request (the ending) or, with `verify: "assert"`, none; a control that appears late is waited for; a renamed
     control and a moved one hand the run to Jev from that step, it still passes and the path is written again; a page
     that now fails ends in the bug outcome under both ways of deciding the ending, never a pass; an edited spec
     drops the path
"""
from __future__ import annotations

import datetime
import http.server
import json
import os
import sys
import tempfile
import threading
import time
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

    def __init__(self, moves: list[tuple], outcome_rules: dict[str, str] | None = None, undecided_while: str | None = None,
                 undecided_ms: int = 0, blocked_reason: str | None = None, fills: dict[str, str] | None = None):
        self.moves = [list(m) for m in moves]
        self.played: set[int] = set()
        self.outcome_rules = outcome_rules or {}
        self.undecided_while = undecided_while  # text on the page while which every decision is an undecided WAIT
        self.undecided_ms = undecided_ms  # how long an undecided answer takes: the page may move meanwhile
        self.blocked_reason = blocked_reason  # the answer to blocked_reason when a run stalls (default: the first one offered, `nothing`)
        self.fills = fills or {}  # a form batch's per-field questions: {substring of the field's question: data key}; others are left empty
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
        self.seen_questions = [*getattr(self, "seen_questions", []), questions]
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
        for key, q in questions.items():
            if key.startswith("fill_"):
                pick = next((v for needle, v in self.fills.items() if needle.lower() in str(q["instructions"]).lower()), "leave_empty")
                answers[key] = self._choice(pick, q["criteria"], 0.95)
        for reason in ("stuck_reason", "blocked_reason"):
            if reason in questions:
                pick = self.blocked_reason if reason == "blocked_reason" and self.blocked_reason else next(iter(questions[reason]["criteria"]))
                answers[reason] = self._choice(pick, questions[reason]["criteria"])
        if "operation" not in questions:
            return {"answers": answers, "usage": usage, "model": "scripted-jev", "latency_ms": 1}
        ops = questions["operation"]["criteria"]
        clicks = questions.get("click_target", {}).get("criteria", {})
        types = questions.get("type_target", {}).get("criteria", {})
        hovers = questions.get("hover_target", {}).get("criteria", {})
        uploads = questions.get("upload_target", {}).get("criteria", {})
        if self.undecided_while and self.undecided_while in text:
            answers["operation"] = self._choice("WAIT", ops, conf=0.3)
            if self.undecided_ms:
                import time
                time.sleep(self.undecided_ms / 1000)
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
                if self.fills and (types[self._find(types, move[1])] or {}).get("current_value"):
                    continue  # the field is filled already (a form batch typed it): this move is done
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
<script>if (new URLSearchParams(location.search).get('plain')) document.getElementById('spin').className = '';</script>
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

# Captions drawn from another tree, the two shapes met live (0.6.0). The Polymer shop: a link around a custom element
# that renders the product's title and price in its own shadow root (<a><shop-card></a>), and a link around an icon
# button that names itself. MDN: a component whose shadow root holds <button><slot></slot></button>, the caption being
# the host's own text. And the control whose content is all in its own tree (a link around an image), which is named
# as it always was. The second button's caption is an element shown through the slot: the button is not covered by it.
SHADOW_NAMES_PAGE = """<!doctype html><html><head><title>Shadow names</title></head><body>
<h1>Outerwear</h1>
<a href="#cart"><icon-button aria-label="Shopping cart: 0 items" role="button" tabindex="0"></icon-button></a>
<a href="#home"><img alt="Shop logo" width="24" height="24" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="></a>
<div id="grid">
  <a href="#tech-shell"><shop-card title="Tech Shell Full-Zip" price="$50.20"></shop-card></a>
  <a href="#crew-neck"><shop-card title="Crew Neck - Grey" price="$22.15"></shop-card></a>
</div>
<slot-button id="copy">Copy</slot-button> <slot-button id="reset"><b>Reset</b> all</slot-button>
<p id="msg"></p>
<script>
  customElements.define('icon-button', class extends HTMLElement {
    connectedCallback() { this.attachShadow({mode: 'open'}).innerHTML = '<style>:host{display:inline-block;width:24px;height:24px;background:#ccd}</style><span></span>'; }
  });
  customElements.define('shop-image', class extends HTMLElement {
    connectedCallback() { this.attachShadow({mode: 'open'}).innerHTML = '<style>:host{display:block;width:120px;height:80px;background:#dde}</style>'; }
  });
  customElements.define('shop-card', class extends HTMLElement {
    connectedCallback() {
      this.attachShadow({mode: 'open'}).innerHTML = '<style>:host{display:block;width:200px;margin:8px}</style><shop-image></shop-image>' +
        '<div class="title">' + this.getAttribute('title') + '</div><span class="price">' + this.getAttribute('price') + '</span>' +
        '<span style="display:none">internal sku 4711</span>';
    }
  });
  customElements.define('slot-button', class extends HTMLElement {
    connectedCallback() {
      const root = this.attachShadow({mode: 'open'});
      root.innerHTML = '<button class="button" type="button" aria-labelledby="label"><span id="label"><slot></slot></span></button>';
      root.querySelector('button').addEventListener('click', () => { document.getElementById('msg').textContent = this.id === 'copy' ? 'Saved successfully' : 'Reset done'; });
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

# the-internet's /upload: the form's own field, and a drag-and-drop library's hidden input appended to the body.
DROPZONE_PAGE = """<!doctype html><html><head><title>Upload</title></head><body>
<form id="f" onsubmit="event.preventDefault(); document.getElementById('msg').textContent = document.getElementById('file-upload').files.length ? 'Saved successfully' : 'Internal Server Error'">
<input id="file-upload" type="file" name="file"> <input type="submit" value="Upload"></form>
<div id="drop" style="width:300px;height:120px;border:2px dashed #888">drop files here</div><p id="msg"></p>
<script>const i = document.createElement('input'); i.type = 'file'; i.className = 'dz-hidden-input';
i.style.cssText = 'visibility:hidden;position:absolute;top:0;left:0;height:0;width:0'; document.body.appendChild(i);</script>
</body></html>"""
DROPZONE_ONLY_PAGE = DROPZONE_PAGE.replace('<input id="file-upload" type="file" name="file"> ', '')

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

REPLAY_FORM_PAGE = """<!doctype html><html><head><title>Profile</title></head><body>
<h1>Profile</h1>
<label>Name <input id="name"></label>
<button id="go" type="button" onclick="location.href='/replay-confirm?name=' + encodeURIComponent(document.getElementById('name').value)">Continue</button>
</body></html>"""

# The second page of the replay scenario, as the application's "current version" (the handler's `variant`) serves it:
# v1 the page the path is recorded on; slow the same with Save arriving 400 ms late; renamed Save reads "Save changes";
# moved Save sits behind "More options"; bug Save answers with an error.
REPLAY_CONFIRM = {
    "v1": '<button id="save" type="button">Save</button>',
    "slow": '<span id="late"></span><script>setTimeout(() => { document.getElementById("late").outerHTML = \'<button id="save" type="button">Save</button>\'; wire(); }, 400);</script>',
    "renamed": '<button id="save" type="button">Save changes</button>',
    "moved": '<button id="more" type="button" onclick="document.getElementById(\'save\').hidden = false; this.remove()">More options</button> '
             '<button id="save" type="button" hidden>Save</button>',
    "bug": '<button id="save" type="button">Save</button>',
    "extra": '<button id="save" type="button">Save</button>',
}


def replay_confirm_page(variant: str) -> str:
    message = "'Error: could not save'" if variant == "bug" else "'Saved successfully for ' + who"
    undo = "" if variant == "bug" else "const u = document.createElement('button'); u.type = 'button'; u.textContent = 'Undo ' + who; document.body.appendChild(u);"
    return f"""<!doctype html><html><head><title>Confirm</title></head><body>
<h1>Confirm</h1>
<p>Confirm the profile of <b id="who"></b></p>
<p id="msg"></p>
<script>
const who = new URLSearchParams(location.search).get('name') || '';
document.getElementById('who').textContent = who;
function wire() {{ const b = document.getElementById('save'); if (b) b.onclick = () => {{ document.getElementById('msg').textContent = {message}; b.remove(); {undo} }}; }}
</script>
{REPLAY_CONFIRM[variant]}
<script>wire();</script>
</body></html>"""


# A sign-up form of three fields. ?react= makes the page answer the typing of the last name: `field` reveals a fourth
# field, `message` a line of text, `list` a list of suggestions.
# A site with a login: /do-login sets the session cookie and sends the browser to /home, which sends anyone without a
# valid cookie back to the form. The handler counts the logins and can forget every session (`sessions`).
LOGIN_APP_PAGE = """<!doctype html><html><head><title>Sign in</title></head><body>
<h1>Sign in</h1>
<script>if (location.search.includes('denied')) { const a = document.createElement('div'); a.setAttribute('role', 'alert');
  a.textContent = 'Error: you can only open that page when you are signed in'; document.body.appendChild(a); console.error('denied'); }</script>
<label>User <input id="user"></label> <label>Password <input id="pass" type="password"></label>
<button id="go" type="button" onclick="location.href='/do-login?user=' + encodeURIComponent(document.getElementById('user').value)">Sign in</button>
</body></html>"""

HOME_PAGE = """<!doctype html><html><head><title>Home</title></head><body>
<h1>Welcome __USER__</h1>
<button id="do" type="button" onclick="document.getElementById('msg').textContent = 'Saved successfully'">Do it</button>
<p id="msg"></p>
</body></html>"""

# The page says whether this browser has been here before (localStorage) and loads a script the server lets it cache.
CACHE_APP_PAGE = """<!doctype html><html><head><title>Cache</title></head><body>
<h1>Visit</h1><p id="msg"></p>
<script>document.getElementById('msg').textContent = localStorage.getItem('seen') ? 'Seen before' : 'Saved successfully (first visit)'; localStorage.setItem('seen', '1'); document.cookie = 'visited=1; max-age=3600';</script>
<script src="/static/big.js"></script>
</body></html>"""

# Save fetches its answer from a slow endpoint (?ms=, default 400) and only then writes the message. ?poll=1 opens a
# request at load that never answers within a run; ?track=1 also sends a slow analytics call on the click.
NET_PAGE = """<!doctype html><html><head><title>Slow save</title></head><body>
<h1>Profile</h1>
<button id="save" type="button">Save</button>
<p id="msg"></p>
<script>
const q = new URLSearchParams(location.search);
if (q.get('poll')) fetch('/api/slow?ms=20000').catch(() => {});
document.getElementById('save').onclick = () => {
  if (q.get('track')) fetch('/collect?event=save&ms=3000').catch(() => {});
  fetch('/api/slow?ms=' + (q.get('ms') || 400)).then(() => { document.getElementById('msg').textContent = 'Saved successfully'; });
};
</script>
</body></html>"""

BATCH_FORM_PAGE = """<!doctype html><html><head><title>Sign up</title></head><body>
<h1>Sign up</h1>
<label>First name <input id="first"></label>
<label>Last name <input id="last"></label>
<span id="extra"></span>
<label>Email <input id="email"></label>
<button id="save" type="button">Save</button>
<p id="msg"></p>
<script>
const $ = id => document.getElementById(id);
const react = new URLSearchParams(location.search).get('react');
$('last').addEventListener('input', () => {
  if ($('extra').firstChild) return;
  if (react === 'field') $('extra').innerHTML = '<label>Middle name <input id="middle"></label>';
  if (react === 'message') $('extra').innerHTML = '<em>Looks good</em>';
  if (react === 'list') $('extra').innerHTML = '<ul role="listbox"><li role="option">Lovelace</li><li role="option">Lovell</li></ul>';
});
$('save').onclick = () => { $('msg').textContent = ($('first').value && $('last').value && $('email').value)
  ? 'Saved successfully' : 'Error: every field is required'; };
</script>
</body></html>"""

ROUTES = {"/login-app": LOGIN_APP_PAGE, "/cache-app": CACHE_APP_PAGE, "/net": NET_PAGE, "/batch-form": BATCH_FORM_PAGE, "/replay-form": REPLAY_FORM_PAGE, "/dropzone": DROPZONE_PAGE, "/dropzone-only": DROPZONE_ONLY_PAGE, "/hover-delay": HOVER_DELAY_PAGE, "/shadow-app": SHADOW_APP_PAGE, "/upload": UPLOAD_PAGE, "/hover": HOVER_PAGE, "/app": APP_PAGE, "/cleanup": CLEANUP_PAGE, "/steps": STEPS_PAGE, "/checkout": CHECKOUT_PAGE, "/card": CARD_PAGE, "/checkout-slim": SLIM_CHECKOUT_PAGE, "/card-line": CARD_LINE_PAGE,
          "/device": DEVICE_PAGE, "/tabs": TABS_PAGE, "/receipt": RECEIPT_PAGE, "/spinner": SPINNER_PAGE, "/shadow": SHADOW_PAGE,
          "/shadow-names": SHADOW_NAMES_PAGE}


class _Site(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []  # the paths requested, for the teardown scenario
    sessions: set = set()  # the users the application counts as logged in (the sessions scenario empties it to expire them)
    logins = 0
    variant = "v1"  # which version of /replay-confirm the application serves now (the replay scenario changes it between runs)

    def log_message(self, *args) -> None:  # noqa: D401 - quiet
        pass

    def do_GET(self) -> None:  # noqa: N802 - the handler's name is the protocol's
        path = self.path.split("?", 1)[0]
        type(self).hits.append(self.path)
        site = type(self)
        cookie_user = next((c.split("=", 1)[1] for c in (self.headers.get("Cookie") or "").split("; ") if c.startswith("sid=")), None)
        extra: dict = {}
        if path == "/do-login":
            user = self.path.split("user=", 1)[-1] if "user=" in self.path else "nobody"
            site.logins += 1
            site.sessions = site.sessions | {user}
            self.send_response(302)
            self.send_header("Set-Cookie", f"sid={user}; Path=/")
            self.send_header("Location", "/home")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/home" and cookie_user not in site.sessions:
            self.send_response(302)
            self.send_header("Location", "/login-app?denied=1")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/api/save":
            status, body, ctype = (500, '{"error": "boom"}', "application/json") if "fail=1" in self.path else (200, '{"ok": true}', "application/json")
        elif path == "/api/deleted":
            status, body, ctype = 200, "{}", "application/json"
        elif path in ("/api/slow", "/collect"):
            ms = next((int(part[3:]) for part in self.path.split("?", 1)[-1].split("&") if part.startswith("ms=") and part[3:].isdigit()), 0)
            time.sleep(ms / 1000)  # each request has its own thread (ThreadingHTTPServer)
            status, body, ctype = 200, "{}", "application/json"
        elif path == "/favicon.ico":
            status, body, ctype = 204, "", "image/x-icon"
        elif path == "/home":
            status, body, ctype = 200, HOME_PAGE.replace("__USER__", cookie_user or ""), "text/html; charset=utf-8"
        elif path == "/static/big.js":
            status, body, ctype = 200, "window.big = 1; /*" + "x" * 50000 + "*/", "application/javascript"
            extra["Cache-Control"] = "public, max-age=3600"
        elif path == "/replay-form" and site.variant == "extra":
            # the same form with one more button on it: another page to the fingerprint, the same thing to do
            status, body, ctype = 200, REPLAY_FORM_PAGE.replace("</body>", '<button type="button">Clear form</button></body>'), "text/html; charset=utf-8"
        elif path == "/replay-confirm":
            status, body, ctype = 200, replay_confirm_page(type(self).variant), "text/html; charset=utf-8"
        elif path in ROUTES:
            status, body, ctype = 200, ROUTES[path], "text/html; charset=utf-8"
        else:
            status, body, ctype = 404, "not found", "text/plain"
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for name, value in extra.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)


def start_site() -> tuple[str, type]:
    handler = type("CapabilitiesSite", (_Site,), {"hits": [], "sessions": set(), "logins": 0})
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

    # G2. the page moves while Jev decides the last undecided look (live: dynamic-controls' loader ended between the
    # observation and the indicator check): no indicator here, so three looks; each answer takes 2 s and the text
    # changes at 6.2 s, inside the third answer (looks at ~0.2, ~2.6, ~5.2 s). Without the check the run ends
    # low_confidence on a page that has finished; with it the count starts again and the next look sees the result.
    moving = make_spec(base + "/spinner?ms=6200&plain=1", goal=spin["goal"], budget={"max_steps": 8, "max_seconds": 60})
    trace, out = go("moved-while-deciding", moving, ScriptedJev([], SAVED, undecided_while="Crunching the numbers", undecided_ms=2000))
    if trace["status"] != "passed" or not any(s.get("moved_while_deciding") for s in trace["steps"]):
        failures.append(f"G2: a page that moved while the last undecided look was decided restarts the count: {trace['status']} "
                        f"{[(s['n'], s.get('low_streak'), s.get('moved_while_deciding')) for s in trace['steps']]}")

    # H. shadow DOM --------------------------------------------------------------------------------------------------------
    shadow = make_spec(base + "/shadow", budget={"max_steps": 3, "max_seconds": 30}, observation={"shadow_dom": False})
    trace, out = go("shadow-hint", shadow, ScriptedJev([("undecided",)], SAVED))
    if trace["steps"][-1].get("shadow_hosts") != 1 or "shadow DOM" not in flags_of(trace, out):
        failures.append(f"H: a stalled run on a page with controls in shadow DOM should say so: {trace['steps'][-1].get('shadow_hosts')}")
    # the same stall when Jev says the control is not on the page (live: the Polymer shop with shadow DOM off): the result
    # carries the hint and suggests test_issue, not bug; with the page observed in full the same answer keeps bug
    trace, out = go("shadow-hint-reason", shadow, ScriptedJev([("undecided",)], SAVED, blocked_reason="control_not_on_page"))
    reason = trace["result"]["reason"]
    if (reason.get("suggested_verdict"), reason.get("suggestion_from")) != ("test_issue", "hints") or "shadow DOM" not in " ".join(reason.get("hints") or []) \
            or "from the hint below" not in flags_of(trace, out):
        failures.append(f"H: control_not_on_page on a page with unobserved shadow DOM should suggest test_issue and carry the hint: {reason}")
    seen_all = make_spec(base + "/shadow", budget={"max_steps": 3, "max_seconds": 30})
    trace, out = go("shadow-no-hint", seen_all, ScriptedJev([("undecided",)], SAVED, blocked_reason="control_not_on_page"))
    reason = trace["result"]["reason"]
    if reason.get("suggested_verdict") != "bug" or reason.get("hints"):
        failures.append(f"H: control_not_on_page on a page observed in full keeps the suggestion bug: {reason}")
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

    # J2. captions drawn from another tree (live, 0.6.0: the Polymer shop's product links and MDN's Copy / Reset buttons
    # read `link ""` and `button ""`, and each product card was in the table three times)
    named = make_spec(base + "/shadow-names", goal="Copy the list, so that the page says it was saved.",
                      **{"assert": [{"element_present": {"role": "button", "name": "Copy"}},
                                    {"element_present": {"role": "link", "name": "Tech Shell Full-Zip $50.20"}}]})
    trace, out = go("shadow-names", named, ScriptedJev([("click", "Copy")], SAVED))
    table = [(e["role"], e.get("name")) for e in trace["steps"][0]["elements"]]
    want = [("link", "Shopping cart: 0 items"), ("link", "Tech Shell Full-Zip $50.20"), ("link", "Crew Neck - Grey $22.15"), ("button", "Copy"),
            ("button", "Reset all")]
    if trace["status"] != "passed" or not all(a["ok"] for a in trace["result"]["assertions"]):
        failures.append(f"J2: a button named through a slot is clicked and asserted by that name: {trace['status']} {trace['result']['assertions']}")
    if any(w not in table for w in want):
        failures.append(f"J2: a caption in a nested shadow root, through a slot or on a self-named child names the control: missing "
                        f"{[w for w in want if w not in table]} in {table}")
    if ("link", "") not in table or any("logo" in (n or "").lower() or "sku" in (n or "") for _, n in table):
        failures.append(f"J2: a link whose content is all in its own tree is named as before, and text that is not displayed names nothing: {table}")
    if len(table) != 7 or any(r == "clickable" for r, _ in table) or trace["steps"][0].get("covered_controls"):
        failures.append(f"J2: the title and the image inside a card's shadow root are inside the link around the card, not entries of their own, and a button is not covered by the caption slotted into it: {table} covered={trace['steps'][0].get('covered_controls')}")
    plain = make_spec(base + "/shadow-names", goal=named["goal"], budget={"max_steps": 3, "max_seconds": 30}, observation={"shadow_dom": False})
    trace, out = go("shadow-names-off", plain, ScriptedJev([("click", "Copy"), ("undecided",)], SAVED))
    off = [(e["role"], e.get("name")) for e in trace["steps"][0]["elements"]]
    if any(n for r, n in off if r == "link") or ("button", "Copy") in off:
        failures.append(f"J2: with shadow DOM off nothing is read across a shadow boundary: {off}")

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
    dz = make_spec(base + "/dropzone", goal="Attach the resume and click Upload, so that the page says it was saved.", files={"resume": upload})
    trace, out = go("upload-dropzone", dz, ScriptedJev([("upload", "file", "resume"), ("click", "Upload")], SAVED))
    files_seen = [e for e in trace["steps"][0]["elements"] if e["role"] == "file"]
    if trace["status"] != "passed" or len(files_seen) != 1 or files_seen[0].get("hidden"):
        failures.append(f"K: beside the form's own file field a library's orphan input is not offered: {trace['status']} {files_seen}")
    only = make_spec(base + "/dropzone-only", goal=dz["goal"], files={"resume": upload}, budget={"max_steps": 2, "max_seconds": 30})
    trace, out = go("upload-dropzone-only", only, ScriptedJev([("undecided",)], SAVED))
    files_seen = [e for e in trace["steps"][0]["elements"] if e["role"] == "file"]
    if len(files_seen) != 1 or files_seen[0].get("context") != "not in a form or a label":
        failures.append(f"K: when the orphan is the page's only file input it is offered, and says what it is: {files_seen}")
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

    # N. ${DATE...} -----------------------------------------------------------------------------------------------------------
    # The spec is a file, loaded the way run_test.py loads it. Tuesday 17 November 2026 + 30 days is a Thursday; on to
    # Wednesday is 23 December, and the page wants yyyy-dd-mm (live: the OrangeHRM demo's date fields).
    from spec import load_spec
    dated_path = os.path.join(tmp, "dated.json")
    with open(dated_path, "w", encoding="utf-8") as f:
        json.dump({"id": "dated", "start_url": base + "/app",
                   "goal": "Type the given date into Name and save, so that the page says it was saved.",
                   "notes": "The given date is ${DATE+30d+wed:dddd d mmmm yyyy}.",
                   "data": {"day": "${DATE+30d+wed:yyyy-dd-mm}"},
                   "outcomes": {"saved": {"when": "The page says 'Saved successfully'", "verdict": "pass"}},
                   "assert": [{"field_value": {"label": "Name", "equals": "${DATE+30d+wed:yyyy-dd-mm}"}}],
                   "budget": {"max_steps": 8, "max_seconds": 60}, "browser": {"settle_ms": 300, "quiet_ms": 50, "action_timeout_ms": 3000}}, f)
    dated = load_spec(dated_path, today=datetime.date(2026, 11, 17))
    jev = ScriptedJev([("type", "Name", "day"), ("click", "Save")], SAVED)
    trace, out = go("dates", dated, jev)
    offered = [v.get("value") for st in jev.seen_states for v in st.get("available_data_values") or [] if v.get("key") == "day"]
    held = [a for a in trace["result"]["assertions"] if "field_value" in a]
    if trace["status"] != "passed" or set(offered) != {"2026-23-12"} or not held or not held[0]["ok"] or held[0]["field_value"]["equals"] != "2026-23-12":
        failures.append(f"N: the date a placeholder names is offered, typed and asserted: {trace['status']} offered={set(offered)} {held}")
    if trace["spec"].get("run_date") != "2026-11-17" or (trace["spec"].get("dates") or {}).get("${DATE+30d+wed:yyyy-dd-mm}") != "2026-23-12" \
            or "Wednesday 23 December 2026" not in trace["spec"]["notes"]:
        failures.append(f"N: the trace's spec says the day it counted from and what each placeholder became: {trace['spec'].get('run_date')} {trace['spec'].get('dates')}")
    old_run_date = os.environ.get("RUN_DATE")
    os.environ["RUN_DATE"] = "2026-12-17"  # the day after the literal date this replaced (2026-16-12) would have gone red
    try:
        later = load_spec(dated_path)
    finally:
        if old_run_date is None:
            del os.environ["RUN_DATE"]
        else:
            os.environ["RUN_DATE"] = old_run_date
    if (later["run_date"], later["data"]["day"]) != ("2026-12-17", "2027-20-01"):
        failures.append(f"N: RUN_DATE in the environment is the day the dates count from: {later['run_date']} {later['data']['day']}")
    # R. sessions and the HTTP cache -------------------------------------------------------------------------------------------
    sess_dir, cache_dir = os.path.join(tmp, "sessions"), os.path.join(tmp, "http-cache")

    def login_spec(user: str = "ada", **over) -> dict:
        return make_spec(base + "/login-app", **{
            "id": "session", "goal": "Click Do it, so that the page says it was saved.",
            "login": [{"action": "fill", "selector": "#user", "value": user}, {"action": "fill", "selector": "#pass", "value": "pw-of-" + user},
                      {"action": "click", "selector": "#go"}, {"action": "wait_for", "url": "**/home"}, {"action": "wait_for", "selector": "#do"}],
            "assert": [{"text_contains": "Saved successfully"}, {"text_contains": f"Welcome {user}"}],
            "session": {"reuse": True, "dir": sess_dir}, **over})

    def session_run(name: str, spec: dict) -> tuple[dict, str, dict]:
        trace, out = go(name, spec, ScriptedJev([("click", "Do it")], SAVED))
        return trace, out, trace["result"].get("session") or {}

    trace, out, sess = session_run("session-first", login_spec())
    files = [f for f in os.listdir(sess_dir) if f.endswith(".json")] if os.path.isdir(sess_dir) else []
    if (trace["status"], site.logins, sess.get("reused"), sess.get("saved"), len(trace["login"]), len(files)) != ("passed", 1, False, True, 5, 1):
        failures.append(f"R: the first run logs in and saves the session: {trace['status']} logins={site.logins} {sess} {files}")
    saved_session = open(os.path.join(sess_dir, files[0]), encoding="utf-8").read() if files else ""
    if "pw-of-ada" in saved_session or "pw-of-ada" in json.dumps(trace) or '"sid"' not in saved_session:
        failures.append("R: the session file holds the browser's cookies, never what was typed; the trace has neither")
    if not all(os.path.isfile(os.path.join(sess_dir, f)) for f in (".gitignore", ".salt")):
        failures.append("R: the sessions directory ignores itself for git and keeps the key its file names are made with")
    trace, out, sess = session_run("session-reused", login_spec())
    if (trace["status"], site.logins, sess.get("reused"), trace["login"]) != ("passed", 1, True, []):
        failures.append(f"R: the second run starts logged in and skips the login: {trace['status']} logins={site.logins} {sess} {trace['login']}")
    if "login: skipped" not in flags_of(trace, out) or trace["timing"].get("login_ms", 99) > 50:
        failures.append(f"R: the summary says the login was skipped and it cost nothing: {trace['timing']}")
    site.sessions = set()  # the application forgets every session
    trace, out, sess = session_run("session-expired", login_spec())
    if (trace["status"], site.logins, sess.get("reused"), sess.get("expired"), sess.get("saved"), len(trace["login"])) != ("passed", 2, False, True, True, 5):
        failures.append(f"R: a session the application no longer accepts is dropped and the run logs in again: {trace['status']} logins={site.logins} {sess}")
    if any(st.get("announcements") for st in trace["steps"]) or "diagnostics" in trace or "signed in" in json.dumps(trace["result"]):
        failures.append(f"R: what the application said to the expired session (its alert, its console error) is not part of the run: "
                        f"{[st.get('announcements') for st in trace['steps']]} {trace.get('diagnostics')}")
    trace, out, sess = session_run("session-other-account", login_spec("bob"))
    if (trace["status"], site.logins, sess.get("reused"), sess.get("not_reused")) != ("passed", 3, False, "no saved session yet"):
        failures.append(f"R: another account is another session: {trace['status']} logins={site.logins} {sess}")
    trace, out, sess = session_run("session-never", login_spec(session={"reuse": False, "never": True, "dir": sess_dir}))
    if (trace["status"], site.logins, "session" in trace["result"]) != ("passed", 4, False):
        failures.append(f"R: a spec that opts out logs in every time and reports no session: {trace['status']} logins={site.logins}")
    # a setup that begins with a goto: the reused session opens that page at once, and it is not loaded twice
    before = len(site.hits)
    trace, out, sess = session_run("session-goto", login_spec(setup=[{"action": "goto", "url": base + "/home?tab=2"},
                                                                    {"action": "wait_for", "selector": "#do"}]))
    homes = [h for h in site.hits[before:] if h.startswith("/home")]
    if (trace["status"], site.logins, sess.get("reused"), homes, [(st["action"], st.get("by")) for st in trace["setup"]]) != \
            ("passed", 4, True, ["/home?tab=2"], [("goto", "session"), ("wait_for", None)]):
        failures.append(f"R: with a setup that starts with a goto the session is checked on that page, loaded once: {trace['status']} {sess} {homes} {trace['setup']}")
    # the HTTP cache: the script once, the stored state never
    for i in (1, 2):
        spec = make_spec(base + "/cache-app", **{"id": "http-cache", "goal": "Open the page, so that it says saved.",
                                                 "assert": [{"text_contains": "first visit"}], "browser": {"http_cache": True, "http_cache_dir": cache_dir}})
        trace, out = go(f"http-cache-{i}", spec, ScriptedJev([], SAVED))
        if trace["status"] != "passed" or trace["browser"].get("http_cache") != "slot-0":
            failures.append(f"R: run {i} on the cache profile starts with no stored state (a first visit again): {trace['status']} {trace['browser']}")
    if sum(1 for h in site.hits if h.startswith("/static/big.js")) != 1:
        failures.append(f"R: the cacheable script is fetched once over two runs: {[h for h in site.hits if 'big.js' in h]}")
    if os.path.exists(os.path.join(cache_dir, "slot-0.lock")) or not os.path.isfile(os.path.join(cache_dir, ".gitignore")):
        failures.append("R: the cache slot is released after the run and the directory ignores itself for git")
    # a saved session on the cache profile: cookies put back by hand
    trace, out, sess = session_run("session-on-cache", login_spec(browser={"http_cache": True, "http_cache_dir": cache_dir}))
    if (trace["status"], site.logins, sess.get("reused")) != ("passed", 4, True):
        failures.append(f"R: a saved session is reused on the cache profile too: {trace['status']} logins={site.logins} {sess}")

    # Q. network-aware settle ----------------------------------------------------------------------------------------------------
    def net_spec(query: str = "", **browser) -> dict:
        return make_spec(base + "/net" + query, **{"id": "net-settle", "assert": [{"text_contains": "Saved successfully"}],
                                                   "browser": {"settle_ms": 2000, "quiet_ms": 50, **browser}})

    def click_step(trace: dict) -> dict:
        return next(st for st in trace["steps"] if (st.get("executed") or {}).get("action") == "CLICK")

    trace, out = go("net-dom", net_spec(), ScriptedJev([("click", "Save"), ("wait",), ("wait",)], SAVED))
    st = click_step(trace)["settle"]
    if trace["status"] != "passed" or "network" in st or st["ms"] > 300 or trace["steps"][1].get("outcome", {}).get("choice") == "saved":
        failures.append(f"Q: the default settle does not wait for the response (the look after the click is too early): {st}")
    trace, out = go("net-network", net_spec(settle="network"), ScriptedJev([("click", "Save")], SAVED))
    st = click_step(trace)["settle"]
    if (trace["status"], st.get("ended"), (st.get("network") or {}).get("requests"), len(trace["steps"])) != ("passed", "network", 1, 2):
        failures.append(f"Q: with settle network the look after the click already shows the answer: {trace['status']} {st} steps={len(trace['steps'])}")
    if not 300 <= st["ms"] <= 1200 or "left" in st["network"]:
        failures.append(f"Q: the settle lasted as long as the request, not as long as the cap: {st}")
    trace, out = go("net-ignored", net_spec("?poll=1&track=1", settle="network"), ScriptedJev([("click", "Save")], SAVED))
    st = click_step(trace)["settle"]
    if (trace["status"], (st.get("network") or {}).get("requests"), len(trace["steps"])) != ("passed", 1, 2) or st["ms"] > 1200:
        failures.append(f"Q: a connection opened before the action and an analytics call are not waited for: {trace['status']} {st}")
    trace, out = go("net-cap", net_spec("?ms=3000", settle="network", settle_ms=600), ScriptedJev([("click", "Save"), ("wait",), ("wait",), ("wait",)], SAVED))
    st = click_step(trace)["settle"]
    if (st.get("ended"), (st.get("network") or {}).get("left")) != ("cap", 1) or not 550 <= st["ms"] <= 1000:
        failures.append(f"Q: a request that outlasts the cap ends the settle at the cap and is reported: {st}")

    # P. one request per form ------------------------------------------------------------------------------------------------------
    form_moves = [("type", "First name", "first"), ("type", "Last name", "last"), ("type", "Email", "email"), ("click", "Save")]
    form_fills = {"First name": "first", "Last name": "last", "Email": "email"}

    def form_spec(query: str = "", **over) -> dict:
        return make_spec(base + "/batch-form" + query, **{
            "id": "form-batch", "goal": "Fill in the first name, the last name and the email and save, so that the page says it was saved.",
            "data": {"first": "Ada", "last": "Lovelace", "email": "ada@example.org"}, "assert": [{"text_contains": "Saved successfully"}],
            "batch_fields": True, **over})

    def typed(trace: dict) -> list[str]:
        return [("batched " if st.get("batched") else "asked ") + st["type_value"]["choice"] for st in trace["steps"]
                if (st.get("executed") or {}).get("action") == "TYPE_TEXT"]

    plain = ScriptedJev(form_moves, SAVED)
    trace, out = go("batch-off", form_spec(batch_fields=False), plain)
    if trace["status"] != "passed" or any(k.startswith("fill_") for q in plain.seen_questions for k in q) or "batch" in trace["result"]:
        failures.append("P: without batch_fields no per-field question is asked and the result has no batch account")
    jev = ScriptedJev(form_moves, SAVED, fills=form_fills)
    trace, out = go("batch-on", form_spec(), jev)
    account = trace["result"].get("batch") or {}
    if (trace["status"], typed(trace), account.get("fields_typed"), account.get("stopped")) != \
            ("passed", ["asked first", "batched last", "batched email"], 2, []):
        failures.append(f"P: one request types the first field and assigns the other two: {trace['status']} {typed(trace)} {account}")
    if jev.requests != plain.requests - 2:
        failures.append(f"P: two requests fewer than field by field: {jev.requests} against {plain.requests}")
    first = next(st for st in trace["steps"] if st.get("batch_planned"))
    if [p["value_key"] for p in first["batch_planned"]] != ["last", "email"] or set(first.get("fill") or {}) != {"0", "1", "2"}:
        failures.append(f"P: the step that typed the first field records the plan and every per-field answer: {first.get('batch_planned')} {first.get('fill')}")
    if "BATCHED" not in flags_of(trace, out):
        failures.append("P: batched steps are flagged in the summary")
    for react, needle in (("field", 'new: textbox "Middle name"'), ("message", "the page's text changed"), ("list", "a list of suggestions opened")):
        jev = ScriptedJev(form_moves, SAVED, fills=form_fills)
        trace, out = go(f"batch-{react}", form_spec(f"?react={react}"), jev)
        account = trace["result"].get("batch") or {}
        stopped = (account.get("stopped") or [{}])[0]
        if (trace["status"], typed(trace), account.get("fields_typed")) != ("passed", ["asked first", "batched last", "asked email"], 1):
            failures.append(f"P ({react}): the batch ends when the page reacts and Jev decides the rest: {trace['status']} {typed(trace)} {account}")
        if needle not in (stopped.get("reason") or "") or stopped.get("fields_left") != 1 or "BATCH-ENDED" not in flags_of(trace, out):
            failures.append(f"P ({react}): the reason says how the page reacted: {stopped}")
    # an assignment Jev is not sure of is not typed: thresholds.batch_confidence
    jev = ScriptedJev(form_moves, SAVED, fills=form_fills)
    trace, out = go("batch-unsure", form_spec(thresholds={"batch_confidence": 0.99}), jev)
    if (trace["status"], typed(trace)) != ("passed", ["asked first", "asked last", "asked email"]):
        failures.append(f"P: below batch_confidence every field is asked for: {trace['status']} {typed(trace)}")

    # O. replay -----------------------------------------------------------------------------------------------------------------
    paths = os.path.join(tmp, "paths")
    replay_rules = {"saved": "Saved successfully", "save_error": "could not save"}
    full_moves = [("type", "Name", "name"), ("click", "Continue"), ("click", "Save")]

    def replay_spec(stamp: str, verify: str = "jev", **over) -> dict:
        # `source` stands for the spec file: the same file run with another ${RUN_STAMP} is the same spec
        return make_spec(base + "/replay-form", **{
            "id": "replay", "goal": "Enter the name, continue and save, so that the page says the profile was saved.",
            "data": {"name": f"Ada {stamp}"}, "run_stamp": stamp, "source": {"sha256": "the spec file as written"},
            "outcomes": {"saved": {"when": "The page says 'Saved successfully'", "verdict": "pass"},
                         "save_error": {"when": "The page says 'Error: could not save'", "verdict": "bug"}},
            "assert": [{"text_contains": "Saved successfully"}], "replay": {"enabled": True, "verify": verify, "dir": paths}, **over})

    def replayed(trace: dict) -> list[bool]:
        return [bool(st.get("replayed")) for st in trace["steps"] if (st.get("executed") or {}).get("action") in ("CLICK", "TYPE_TEXT")]

    path_file = os.path.join(paths, "replay.json")
    site.variant = "v1"
    jev = ScriptedJev(full_moves, replay_rules)
    trace, out = go("replay-record", replay_spec("r1aa"), jev)
    rp = trace["result"].get("replay") or {}
    if trace["status"] != "passed" or not rp.get("saved") or rp.get("used") or rp.get("steps_by_jev") != 3 or not os.path.isfile(path_file):
        failures.append(f"O: a passing run with replay on saves its path: {trace['status']} {rp}")
    recorded_requests = jev.requests
    saved_text = open(path_file, encoding="utf-8").read() if os.path.isfile(path_file) else ""
    saved_path = json.loads(saved_text) if saved_text else {"steps": [], "final": {}}
    if "Ada" in saved_text or "r1aa" in saved_text or '"value_key": "name"' not in saved_text:
        failures.append("O: the saved path holds the key of the value typed, never the value or the run stamp")
    if [st["operation"] for st in saved_path["steps"]] != ["TYPE_TEXT", "CLICK", "CLICK"] or \
            'button "Undo {{data:name}}"' not in ((saved_path.get("final") or {}).get("page") or {}).get("controls", []):
        failures.append(f"O: three steps and the final page with this run's value as a token: {saved_text[:400]}")
    if not all(os.path.isfile(os.path.join(paths, ".gitignore")) for _ in (0,)):
        failures.append("O: the directory of saved paths ignores itself for git")

    # the same pages, another run stamp: every step from the path, one request for the ending
    jev = ScriptedJev([], replay_rules)
    trace, out = go("replay-full", replay_spec("r2bb"), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], replayed(trace), rp.get("steps_replayed"), rp.get("handed_back"), rp.get("verified_by"), jev.requests) != \
            ("passed", [True, True, True], 3, None, "jev", 1):
        failures.append(f"O: unchanged pages replay every step and ask Jev once, about the ending: {trace['status']} {replayed(trace)} {rp} requests={jev.requests}")
    if recorded_requests <= 1 or "operation" in (jev.seen_questions[-1] if getattr(jev, "seen_questions", None) else {}):
        failures.append(f"O: the recording run asked {recorded_requests} requests; the deciding look asks no operation")
    if trace["result"].get("confirmed_by") != "assertions" or not (trace["result"]["evidence"].get("line") or "").startswith("Saved successfully for Ada r2bb"):
        failures.append(f"O: the ending is decided as in any run, and the evidence line rode in the one request: {trace['result'].get('confirmed_by')} {trace['result']['evidence']}")
    if rp.get("saved") or "replayed to its end" not in (rp.get("save_note") or ""):
        failures.append(f"O: a path walked to its end stands: {rp}")
    text = flags_of(trace, out)
    if "3 of 3 saved steps replayed without Jev" not in text or "saved path" not in text or "REPLAY-VERIFY" not in text:
        failures.append("O: the summary says how many steps were replayed and marks them")

    # verify "assert": the assertions alone decide, no request at all
    jev = ScriptedJev([], replay_rules)
    trace, out = go("replay-assert", replay_spec("r3cc", verify="assert"), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], jev.requests, rp.get("verified_by"), trace["result"].get("confirmed_by")) != ("passed", 0, "assertions", "assertions"):
        failures.append(f"O: with verify assert a replayed pass costs no request: {trace['status']} requests={jev.requests} {rp}")
    if "Jev was not asked" not in (trace["result"]["evidence"].get("skipped") or ""):
        failures.append(f"O: the result says why it has no evidence line: {trace['result']['evidence']}")

    # a control that arrives late is waited for, as long as the recorded run took and a little more
    site.variant = "slow"
    jev = ScriptedJev([], replay_rules)
    trace, out = go("replay-slow", replay_spec("r4dd"), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], rp.get("steps_replayed"), rp.get("handed_back")) != ("passed", 3, None) or rp.get("waited_ms", 0) < 200:
        failures.append(f"O: Save arriving 400 ms late is waited for, not handed to Jev: {trace['status']} {rp}")

    # renamed: the saved step no longer applies, Jev takes the run from there, it passes and the path is written again
    site.variant = "renamed"
    jev = ScriptedJev([("click", "Save changes")], replay_rules)
    trace, out = go("replay-renamed", replay_spec("r5ee"), jev)
    rp = trace["result"].get("replay") or {}
    hb = rp.get("handed_back") or {}
    if (trace["status"], replayed(trace), hb.get("at_step"), hb.get("path_step"), rp.get("saved")) != ("passed", [True, True, False], 3, 3, True):
        failures.append(f"O: a renamed control hands over to Jev at that step and the run still passes: {trace['status']} {replayed(trace)} {rp}")
    if 'gone: button "Save"' not in (hb.get("reason") or "") or 'new: button "Save changes"' not in (hb.get("reason") or ""):
        failures.append(f"O: the reason names what changed on the page: {hb}")
    if "REPLAY-ENDED" not in flags_of(trace, out) or '"name": "Save changes"' not in open(path_file, encoding="utf-8").read():
        failures.append("O: the step is flagged and the new path has the new name")
    jev = ScriptedJev([], replay_rules)
    trace, out = go("replay-renamed-again", replay_spec("r6ff"), jev)
    if (trace["status"], replayed(trace), jev.requests) != ("passed", [True, True, True], 1):
        failures.append(f"O: the rewritten path replays in full on the next run: {trace['status']} {replayed(trace)} requests={jev.requests}")

    # moved: Save is now behind another control
    site.variant = "moved"
    jev = ScriptedJev([("click", "More options"), ("click", "Save")], replay_rules)
    trace, out = go("replay-moved", replay_spec("r7gg"), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], replayed(trace), (rp.get("handed_back") or {}).get("at_step"), rp.get("saved")) != ("passed", [True, True, False, False], 3, True):
        failures.append(f"O: a moved control hands over to Jev and the run still passes: {trace['status']} {replayed(trace)} {rp}")

    # a page that differs from the recording in something that does not change what to do (one more button on the form):
    # Jev is asked, chooses what the saved step says, and the path goes on; twice here, then the third step is replayed
    site.variant = "v1"
    go("replay-rerecord-plain", replay_spec("r7hh"), ScriptedJev(full_moves, replay_rules))
    site.variant = "extra"
    jev = ScriptedJev([("type", "Name", "name"), ("click", "Continue")], replay_rules)
    trace, out = go("replay-resumed", replay_spec("r7ii"), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], replayed(trace), (rp.get("handed_back") or {}).get("at_step"), [r["path_step"] for r in rp.get("resumed") or []], jev.requests) != \
            ("passed", [False, False, True], 1, [1, 2], 3):
        failures.append(f"O: when Jev's own decision is the saved step the path resumes: {trace['status']} {replayed(trace)} {rp} requests={jev.requests}")
    if "REPLAY-RESUMED" not in flags_of(trace, out) or "the path resumed" not in flags_of(trace, out) or not rp.get("saved"):
        failures.append(f"O: the summary says the path resumed, and the path is written again with the page as it is now: {rp}")
    site.variant = "v1"  # (the plain pages again, and their path, for the scenarios below)
    go("replay-rerecord-plain-2", replay_spec("r7jj"), ScriptedJev(full_moves, replay_rules))

    # a page that now fails: the saved steps all apply, the ending is the bug, under both ways of deciding it
    site.variant = "v1"
    go("replay-rerecord", replay_spec("r8hh"), ScriptedJev(full_moves, replay_rules))  # the path of the healthy page again
    before_bug = open(path_file, encoding="utf-8").read()
    site.variant = "bug"
    for verify in ("jev", "assert"):
        jev = ScriptedJev([], replay_rules)
        trace, out = go(f"replay-bug-{verify}", replay_spec("r9ii", verify=verify), jev)
        rp = trace["result"].get("replay") or {}
        if (trace["status"], trace["result"]["outcome"], trace["result"]["verdict"], trace["pass"]) != ("outcome", "save_error", "bug", False):
            failures.append(f"O: a page that now fails ends in the bug outcome, never a pass (verify {verify}): {trace['status']} {trace['result']['outcome']}")
        if rp.get("steps_replayed") != 3 or rp.get("saved") or "--no-replay" not in (rp.get("note") or "") or exit_code(trace) != 1:
            failures.append(f"O: the red run keeps the old path and says to run once more without it (verify {verify}): {rp}")
        if "final_mismatch" not in " ".join(k for st in trace["steps"] for k in st):
            failures.append(f"O: the deciding look records that the final page is not the recorded one (verify {verify})")
    if open(path_file, encoding="utf-8").read() != before_bug:
        failures.append("O: a run that did not pass leaves the saved path as it was")

    # an edited spec, and replay off
    site.variant = "v1"
    jev = ScriptedJev(full_moves, replay_rules)
    trace, out = go("replay-edited", replay_spec("r0jj", source={"sha256": "the spec file after an edit"}), jev)
    rp = trace["result"].get("replay") or {}
    if (trace["status"], rp.get("used"), rp.get("not_used"), replayed(trace)) != ("passed", False, "the spec changed since the path was recorded", [False] * 3):
        failures.append(f"O: an edited spec drops the path and records a new one: {trace['status']} {rp}")
    trace, out = go("replay-off", replay_spec("r1kk", replay={"enabled": False}), ScriptedJev(full_moves, replay_rules))
    if "replay" in trace["result"] or any(replayed(trace)):
        failures.append("O: without replay nothing is read, nothing is written, and the result has no replay account")
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
