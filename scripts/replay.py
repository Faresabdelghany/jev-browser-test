"""Replay: remember the path of a passing run and walk it again without asking Jev.

A run with `replay` on (spec `"replay": true`, or `--replay`) that ends `passed` writes its path to
`.jev/paths/<spec id>.json`: for every executed action the operation, how to find its target again (role, name,
text, context and stable attributes, never the table index), the *key* of the value typed (never the value) and a
fingerprint of the page it was decided on. The next run with replay on executes those steps with no Jev request, one
by one, each only when

  * the page matches the step's fingerprint (`match_page`): the same URL shape, the same title and the same set of
    named fields and buttons on screen, and
  * the target is found unambiguously in the fresh observation (`find_target`): exactly one element with the recorded
    role and name that can take the operation, told apart from others of the same name by its text, context, link
    target or stable attributes.

The page is given the time it took when the path was recorded (and at least two settles) to get there. On any
mismatch the run hands over to Jev from that step and carries on as an ordinary run; if it then ends `passed`, the
path is written again from what this run did.

A replayed run never reports a pass on the replay alone. After the last saved step the ending is decided as in any
run: by default Jev is asked which declared outcome the page shows (one request, without the operation and target
questions) and the spec's assertions are evaluated; with `replay.verify: "assert"` a spec that has assertions is
decided by them alone when they all hold on the page the recorded run ended on. Everything else about the run (the
executor, the settle, the history Jev would see, repeat detection, the trace) is the code an ordinary run uses: a
saved step only replaces the request that would have chosen it.

A path is dropped, and recorded afresh by the next passing run, when the spec file changed (any edit), when the
options that shape the observation differ (device, viewport, shadow DOM, frames, extra operations) or when
`PATH_FORMAT` changed. Strings in a path are templated: a data value, the run stamp and a date placeholder's value
are written as `{{data:<key>}}`, `{{run_stamp}}` and `{{date:<n>}}` and filled in again from the run that replays,
so a path holds no typed value and still matches a page that shows this run's own.

Pure except for load_path / save_path; run_test.py owns the browser.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

from observe import element_label
from policy import element_operations

PATH_FORMAT = 1  # bump when the meaning of a saved path changes: every saved path is then recorded afresh
DEFAULT_DIR = os.path.join(".jev", "paths")
VERIFY_MODES = ("jev", "assert")
TARGET_OPERATIONS = ("CLICK", "TYPE_TEXT", "SELECT", "HOVER", "UPLOAD_FILE")
REPLAYABLE = (*TARGET_OPERATIONS, "PRESS_ENTER", "SCROLL_DOWN", "SCROLL_UP")
# The controls whose presence makes a page "the same page": fields and buttons. Links (a menu, an article's body),
# options (an autocomplete's suggestions) and rows are content and change with the data; a field or a button that is
# new or gone is a change to the form, and that is Jev's to look at.
PRINT_ROLES = {"textbox", "searchbox", "combobox", "select", "checkbox", "radio", "switch", "button", "submit", "reset", "file", "range"}
STABLE_ATTRS = ("data-testid", "data-test", "data-test-id", "data-qa", "data-cy", "id", "name")
GENERATED_RE = re.compile(r"\d{3,}|[:.]")  # an id such as ":r5:", "ember1234", "input.17" is made up by a framework at render time
WAIT_FLOOR_SETTLES = 2  # a saved step waits for its page at least this many settle_ms ...
WAIT_FACTOR = 2  # ... and this many times what the recorded run waited, never beyond navigation_timeout_ms
POLL_MS = 250  # while waiting for a saved step's page: look again this often (sooner when the page changes)
RESUME_TRIES = 3  # after a handover: how many of Jev's actions may differ from the saved step before the path is given up

# Read where the path is recorded and where two candidates must be told apart: the attributes that identify a control
# across renders. One call for the indices asked about; the page's own tree and, with `deep`, its open shadow roots.
ATTRS_JS = r"""(args) => {
  const out = {};
  const roots = [document];
  if (args.deep) { const scan = root => { for (const el of root.querySelectorAll('*')) if (el.shadowRoot) { roots.push(el.shadowRoot); scan(el.shadowRoot); } }; scan(document); }
  for (const idx of args.idx) {
    for (const root of roots) {
      const el = root.querySelector('[data-jev-idx="' + idx + '"]');
      if (!el) continue;
      const rec = {};
      for (const a of args.names) { const v = el.getAttribute(a); if (v) rec[a] = String(v).slice(0, 80); }
      out[String(idx)] = rec;
      break;
    }
  }
  return out;
}"""


class Tokens:
    """This run's changing values and the tokens a saved path writes in their place: every data value (`{{data:key}}`),
    the run stamp (`{{run_stamp}}`) and what each date placeholder became (`{{date:n}}`). `template` writes the
    tokens, `fill` reads them back with the values of the run that replays. A value the observer cut (a name stops at
    80 characters) is written as `{{data:key:N}}`: its first N characters."""

    def __init__(self, spec: dict):
        pairs: dict[str, str] = {}
        for key, value in (spec.get("data") or {}).items():
            if isinstance(value, str) and value:
                pairs.setdefault(value, "{{data:" + key + "}}")
        if spec.get("run_stamp"):
            pairs.setdefault(spec["run_stamp"], "{{run_stamp}}")
        for i, value in enumerate((spec.get("dates") or {}).values()):
            if isinstance(value, str) and value:
                pairs.setdefault(value, "{{date:" + str(i) + "}}")
        self._by_value = dict(sorted(pairs.items(), key=lambda kv: -len(kv[0])))  # the longest value first
        self._by_token = {tok: value for value, tok in self._by_value.items()}
        self._values_re = re.compile("|".join(re.escape(v) for v in self._by_value)) if self._by_value else None
        heads = sorted((tok[:-2] for tok in self._by_token), key=len, reverse=True)
        self._tokens_re = re.compile("(" + "|".join(re.escape(h) for h in heads) + r")(?::(\d+))?\}\}") if heads else None

    def template(self, text):
        if not isinstance(text, str) or not text or self._values_re is None:
            return text
        out = self._values_re.sub(lambda m: self._by_value[m.group(0)], text)
        for value, tok in self._by_value.items():  # the head of a value the observer cut off at the end of the string
            for k in range(min(len(value) - 1, len(out)), 3, -1):
                if out.endswith(value[:k]):
                    return out[:-k] + tok[:-2] + ":" + str(k) + "}}"
        return out

    def fill(self, text):
        if not isinstance(text, str) or not text or self._tokens_re is None:
            return text

        def value(m) -> str:
            full = self._by_token[m.group(1) + "}}"]
            return full[:int(m.group(2))] if m.group(2) else full
        return self._tokens_re.sub(value, text)


_TOKEN_OR_DIGITS = re.compile(r"(\{\{[^{}]*\}\})|\d+")
_WORD = re.compile(r"[^\W\d_]{2,}")  # two letters in a row: a name that says something ("Save", not "×", "+" or "3")
_ID_SEGMENT = re.compile(r"(?:\d+|[0-9a-f]{8,}|[0-9a-f]{8}-[0-9a-f-]{27}|[A-Za-z0-9_-]{24,})", re.I)


def no_digits(text: str) -> str:
    """Every run of digits as '#', tokens left alone: a counter in a title or on a button ("Cart (2)") is not what
    makes a page another page."""
    return _TOKEN_OR_DIGITS.sub(lambda m: m.group(1) or "#", text or "")


def url_shape(url: str) -> str:
    """A URL without what changes from run to run: origin and path with id-like segments (numbers, hashes, UUIDs,
    long opaque tokens) as '*', the names of the query parameters without their values, and the fragment treated like
    a path (a single-page app's route)."""
    try:
        u = urlsplit(url or "")
    except ValueError:
        return url or ""

    def shape(path: str) -> str:
        return "/".join("*" if _ID_SEGMENT.fullmatch(seg) else seg for seg in path.split("/"))

    keys = sorted({k for k, _ in parse_qsl(u.query, keep_blank_values=True)})
    out = f"{u.scheme}://{u.netloc}{shape(u.path)}"
    if keys:
        out += "?" + ",".join(keys)
    if u.fragment:
        out += "#" + shape(u.fragment.split("?", 1)[0])
    return out


def page_print(obs: dict, tokens: Tokens) -> dict:
    """The fingerprint a saved step carries of the page it was decided on: the URL's shape, the title and the set of
    named fields and buttons offered (role and name). Controls of a record are left out, there being as many as there
    are records: those inside a table row (`row`, set by the observer) and those the observer gave a row or list
    context. Live: a list page of a shared demo showed another visitor's row with Approve and Reject buttons in one
    run and not in the next, and the step after it was handed to Jev for a page that had not changed. And only a
    control whose name is a word counts: an unnamed button, one named by a symbol ("×" on a filter chip that comes and
    goes with the filter) or by a guess from its icon's class appears and disappears with the page's decoration.
    Live: a chip's "×" rendered a moment later in one run than in the recording, and the step waited three seconds
    for a page that was already there, or was handed to Jev."""
    controls = sorted({f'{e["role"]} "{no_digits(tokens.template(e.get("name") or ""))}"' for e in obs.get("elements") or []
                       if e.get("role") in PRINT_ROLES and not e.get("context") and not e.get("row") and not e.get("icon_named")
                       and _WORD.search(e.get("name") or "")})
    return {"url": url_shape(tokens.template(obs.get("url") or "")), "title": no_digits(tokens.template(obs.get("title") or "")),
            "controls": controls}


def match_page(saved: dict, now: dict) -> str | None:
    """Why the page is not the one a saved step was recorded on (both are page_print results), or None when it is."""
    if saved.get("url") != now.get("url"):
        return f"the page is {now.get('url')}, the path was recorded on {saved.get('url')}"
    if saved.get("title") != now.get("title"):
        return f"the page's title is \"{now.get('title')}\", recorded: \"{saved.get('title')}\""
    was, has = set(saved.get("controls") or []), set(now.get("controls") or [])
    if was != has:
        gone, new = sorted(was - has), sorted(has - was)
        parts = ([f"gone: {', '.join(gone[:3])}" + (f" and {len(gone) - 3} more" if len(gone) > 3 else "")] if gone else []) \
            + ([f"new: {', '.join(new[:3])}" + (f" and {len(new) - 3} more" if len(new) > 3 else "")] if new else [])
        return "the page's fields and buttons differ from the recording (" + "; ".join(parts) + ")"
    return None


def match_final(saved: dict | None, now: dict) -> str | None:
    """Why the page is not the one the recorded run ended on (`saved`: a path's `final`), or None. A run that ended on
    a page still under its loading layer (`busy`: the assertions already held there) recorded only that page's shell,
    so its fields and buttons say nothing about the page once loaded: the URL and the title are compared."""
    page = (saved or {}).get("page")
    if not page:
        return None
    if saved.get("busy"):
        return match_page({**page, "controls": []}, {**now, "controls": []})
    return match_page(page, now)


def stable_attrs(attrs: dict | None) -> dict:
    """The attributes worth identifying a control by: test ids always, an id or a name unless a framework generated it."""
    out = {}
    for k in STABLE_ATTRS:
        v = (attrs or {}).get(k)
        if isinstance(v, str) and v and not (k in ("id", "name") and GENERATED_RE.search(v)):
            out[k] = v
    return out


def describe_target(el: dict, attrs: dict | None, tokens: Tokens, option: str | None = None) -> dict:
    """How to find `el` (an observed element) again: what a person would say about it, and what a test would."""
    d = {"role": el["role"], "name": tokens.template(el.get("name") or "")}
    for key in ("text", "context", "href", "frame"):
        if el.get(key):
            d[key] = tokens.template(el[key])
    if el.get("type"):
        d["type"] = el["type"]
    stable = {k: tokens.template(v) for k, v in stable_attrs(attrs).items()}
    if stable:
        d["attrs"] = stable
    if option is not None:
        d["option"] = tokens.template(option)
    return d


def candidates(saved: dict, elements: list[dict], operation: str, spec: dict, tokens: Tokens, read_attrs=None) -> tuple[list[dict], list[str], str | None]:
    """The observed elements a saved target may be, narrowed by everything recorded about it: (pool, what told them
    apart, None), or ([], [], why none). Role and name must match and the element must be able to take the operation;
    among several, the frame, the type, the link target, the text and the context each narrow the pool when some
    candidate has the recorded value, then the stable attributes (read from the page only then, or for a control
    without a name)."""
    role, name = saved.get("role"), tokens.fill(saved.get("name") or "")
    label = f'{role} "{name}"'
    named = [e for e in elements if e.get("role") == role and (e.get("name") or "") == name]
    pool = [e for e in named if operation in element_operations(spec, e)]
    if not pool:
        if named:
            return [], [], f"{label} is on the page but cannot take {operation} now" + (" (disabled)" if all(e.get("disabled") for e in named) else "")
        return [], [], f"{label} is not on the page"
    told_by: list[str] = []
    for key in ("frame", "type", "href", "text", "context"):
        if len(pool) == 1 and name:
            break
        want = tokens.fill(saved.get(key) or "")
        narrowed = [e for e in pool if (e.get(key) or "") == want]
        if narrowed:
            if want and key in ("href", "text", "context"):
                told_by.append(key)
            pool = narrowed
    want_attrs = {k: tokens.fill(v) for k, v in (saved.get("attrs") or {}).items()}
    if want_attrs and read_attrs is not None and (len(pool) > 1 or not name):
        pool_attrs = read_attrs([e["idx"] for e in pool if not e.get("frame")]) or {}
        narrowed = [e for e in pool if stable_attrs(pool_attrs.get(str(e["idx"]))) == want_attrs]
        if narrowed:
            told_by.append("attrs")
            pool = narrowed
    return sorted(pool, key=lambda e: e["idx"]), told_by, None


def find_target(saved: dict, elements: list[dict], operation: str, spec: dict, tokens: Tokens,
                read_attrs=None) -> tuple[dict | None, int | None, str | None]:
    """The one observed element a saved target describes, as (element, option, None) with `option` the index of the
    recorded option for SELECT (else None), or (None, None, why not). `read_attrs(indices)` returns {index: attributes}
    for elements of this observation (run_test reads them from the page).

    Controls that nothing tells apart (two "Delete" buttons with the same text, context and attributes, which Jev
    could only choose between by their order either) are replayed by position among themselves, `nth` of `of`, and
    only while there are still exactly `of` of them: the first of two is not the first of three."""
    role, name = saved.get("role"), tokens.fill(saved.get("name") or "")
    label = f'{role} "{name}"'
    pool, told_by, why = candidates(saved, elements, operation, spec, tokens, read_attrs)
    if why:
        return None, None, why
    if len(pool) > 1 and isinstance(saved.get("nth"), int) and saved.get("of") == len(pool):
        pool, told_by = [pool[saved["nth"]]], [*told_by, "nth"]
    if len(pool) != 1:
        was = f" (the recording had {saved['of']})" if saved.get("of") else ""
        return None, None, f"{len(pool)} controls read {label} and nothing recorded tells them apart{was}"
    if not name and not told_by:
        return None, None, f"the recorded target has no name ({label}) and no text, context or stable attribute identifies it on this page"
    el = pool[0]
    if operation == "SELECT":
        want = tokens.fill(saved.get("option") or "")
        options = [o for o in el.get("options") or [] if not o.get("disabled") and o.get("text") == want]
        if len(options) != 1:
            return None, None, f'{label} has {"no" if not options else len(options)} option reading "{want}"'
        return el, options[0]["i"], None
    return el, None, None


def spec_key(spec: dict) -> str:
    """What "the spec" is for a saved path: the file as written (`spec["source"]["sha256"]`, set by spec.load_spec,
    which hashes it before any ${...} is substituted), else the spec itself without what a run adds to it."""
    source = (spec.get("source") or {}).get("sha256")
    if source:
        return source
    body = {k: v for k, v in spec.items() if k not in ("run_stamp", "run_date", "dates", "source", "replay")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def run_options(spec: dict) -> dict:
    """The settings that decide what an observation contains: a path recorded under others describes other tables."""
    b, o = spec.get("browser") or {}, spec.get("observation") or {}
    return {"device": b.get("device"), "viewport": b.get("viewport"), "shadow_dom": bool(o.get("shadow_dom")),
            "frames": list(o.get("frames") or []), "max_elements": o.get("max_elements"),
            "extra_operations": sorted(spec.get("extra_operations") or []), "files": sorted(spec.get("files") or {})}


def path_file(spec: dict, directory: str | None = None) -> str:
    return os.path.join(directory or (spec.get("replay") or {}).get("dir") or DEFAULT_DIR, f"{spec['id']}.json")


def load_path(file: str, spec: dict) -> tuple[dict | None, str | None]:
    """(path, None) when `file` holds a path this run may replay, else (None, why not)."""
    if not os.path.isfile(file):
        return None, "no saved path yet"
    try:
        with open(file, encoding="utf-8") as f:
            path = json.load(f)
    except (OSError, ValueError) as e:
        return None, f"the saved path could not be read ({type(e).__name__})"
    if not isinstance(path, dict) or not isinstance(path.get("steps"), list):
        return None, "the saved path is not a path"
    if path.get("format") != PATH_FORMAT:
        return None, f"the saved path has format {path.get('format')}, this runner writes {PATH_FORMAT}"
    if path.get("spec_sha256") != spec_key(spec):
        return None, "the spec changed since the path was recorded"
    if path.get("options") != run_options(spec):
        was, now = path.get("options") or {}, run_options(spec)
        return None, "the run's options differ from the recording's (" + ", ".join(k for k in now if was.get(k) != now[k]) + ")"
    if path.get("verdict") != "pass" or not path.get("outcome"):
        return None, "the saved path is not a passing run's"
    return path, None


def private_dir(directory: str) -> None:
    """Create `directory` with a .gitignore that ignores everything in it (and in `.jev` when it is a folder of that):
    what the runner keeps between runs (saved paths, sessions, caches) is local state and must not reach a repository."""
    os.makedirs(directory, exist_ok=True)
    parent = os.path.dirname(os.path.abspath(directory))
    for d in ([directory, parent] if os.path.basename(parent) == ".jev" else [directory]):
        ignore = os.path.join(d, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="utf-8") as f:
                f.write("# written by jev-browser-test: local state (saved paths, sessions, caches), never committed\n*\n")


def save_path(file: str, path: dict) -> None:
    private_dir(os.path.dirname(file) or ".")
    tmp = f"{file}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(path, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file)  # two runs of one spec finishing together leave one whole file, not two halves


class Replay:
    """One run's replay state: the saved path and where the run is in it, what this run did (the path it would save),
    and the account result.json gives of it. run_test.run drives it."""

    def __init__(self, spec: dict, file: str | None = None, use: bool = True):
        cfg = spec.get("replay") or {}
        self.spec = spec
        self.file = file or path_file(spec)
        self.verify = cfg.get("verify") or "jev"
        self.tokens = Tokens(spec)
        self.path, self.not_used = load_path(self.file, spec) if use else (None, "the saved path was not read (record only)")
        self.cursor: int | None = 0 if self.path else None  # the next saved step; None once Jev has the run
        self.recorded: list[dict] = []  # this run's executed actions as path steps
        self.replayed = 0
        self.handed_back: dict | None = None
        self.waited_ms = 0
        self.verified_by: str | None = None
        self.verify_asked = False
        self.final: dict | None = None  # this run's ending as a path's `final`
        self.saved: bool | None = None
        self.save_note: str | None = None
        # After a handover: the saved step Jev was asked to decide in the path's place. When Jev's own action is that
        # step (the same operation on the control the path describes), the path was right and only its picture of the
        # page was not, and the replay goes on from the next saved step (try_resume).
        self.resume_at: int | None = None
        self.resume_misses = 0
        self.resumed: list[dict] = []

    # -- walking the saved path ----------------------------------------------------------------------------------------
    @property
    def active(self) -> bool:
        return self.cursor is not None and self.cursor < len(self.path["steps"])

    @property
    def at_end(self) -> bool:
        """Every saved step was replayed and the ending has not been asked about yet."""
        return self.cursor is not None and self.cursor >= len(self.path["steps"]) and not self.verify_asked

    def next_step(self) -> dict:
        return self.path["steps"][self.cursor]

    def wait_budget(self, recorded_ms: int | None) -> int:
        """How long a saved step (or the saved ending) may wait for its page: see WAIT_FLOOR_SETTLES / WAIT_FACTOR."""
        b = self.spec["browser"]
        return int(min(max(WAIT_FLOOR_SETTLES * b["settle_ms"], WAIT_FACTOR * (recorded_ms or 0) + b["settle_ms"]), b["navigation_timeout_ms"]))

    def decide(self, saved: dict, obs: dict, read_attrs=None) -> tuple[dict | None, str | None]:
        """The decision a saved step makes on this observation, as (decision, None), or (None, why it does not apply).
        decision: {"operation", "element" (the observed element, or None), "target" (the step's target record, as
        resolve_target builds one), "value_key"}."""
        operation = saved.get("operation")
        if operation not in REPLAYABLE:
            return None, f"the path has an operation this runner does not replay ({operation})"
        why = match_page(saved.get("page") or {}, page_print(obs, self.tokens))
        if why:
            return None, why
        if operation == "PRESS_ENTER" and not (self.recorded and self.recorded[-1].get("operation") == "TYPE_TEXT"):
            return None, "PRESS_ENTER is replayed only right after the typing it followed"
        if operation == "SCROLL_DOWN" and not obs.get("can_scroll_down") or operation == "SCROLL_UP" and not obs.get("can_scroll_up"):
            return None, f"the page cannot {operation.replace('_', ' ').lower()} any further"
        if operation not in TARGET_OPERATIONS:
            return {"operation": operation, "element": None, "target": None, "value_key": None}, None
        key = saved.get("value_key")
        if operation == "TYPE_TEXT" and key not in (self.spec.get("data") or {}):
            return None, f"the path types data value '{key}', which the spec no longer has"
        if operation == "UPLOAD_FILE" and key not in (self.spec.get("files") or {}):
            return None, f"the path attaches file '{key}', which the spec no longer has"
        el, option, why = find_target(saved.get("target") or {}, obs.get("elements") or [], operation, self.spec, self.tokens, read_attrs)
        if el is None:
            return None, why
        target = {"choice": str(el["idx"]), "element": el["idx"], "label": f'[{el["idx"]}] {element_label(el)}', "replayed": True}
        if operation == "SELECT":
            text = next((o["text"] for o in el.get("options") or [] if o["i"] == option), "")
            target.update({"choice": f'{el["idx"]}:{option}', "option": option, "label": f'{target["label"]} -> "{text}"'})
        return {"operation": operation, "element": el, "target": target, "value_key": key}, None

    def hand_back(self, n: int, reason: str) -> None:
        """Jev decides from step n on. Kept once: the first reason is why the replay ended."""
        if self.handed_back is None and self.path is not None:
            at = self.cursor if self.cursor is not None and self.cursor < len(self.path["steps"]) else None
            self.handed_back = {"at_step": n, "path_step": None if at is None else at + 1, "reason": reason}
        if self.path is not None and self.cursor is not None and self.cursor < len(self.path["steps"]):
            self.resume_at, self.resume_misses = self.cursor, 0
        self.cursor = None

    def try_resume(self, n: int, operation: str, obs: dict, el: dict | None, option: int | None, value_key: str | None,
                   read_attrs=None) -> bool:
        """Jev has just executed an action after a handover. If it is the saved step the path stopped at (the same
        operation, the same value key, and the control the path describes is the one Jev chose), the replay resumes
        at the next saved step: the page differed from the recording in something that did not change what to do (a
        widget that loaded earlier this time, a banner). Otherwise Jev may take up to RESUME_TRIES other actions (the
        banner it had to dismiss first) before the path is given up for this run."""
        if self.resume_at is None or self.path is None:
            return False
        saved = self.path["steps"][self.resume_at]
        same = saved.get("operation") == operation and (saved.get("value_key") or None) == (value_key or None)
        if same and operation in TARGET_OPERATIONS:
            found, opt, _ = find_target(saved.get("target") or {}, obs.get("elements") or [], operation, self.spec, self.tokens, read_attrs)
            same = found is not None and el is not None and found["idx"] == el["idx"] and (operation != "SELECT" or opt == option)
        if same:
            self.cursor, self.resume_at = self.resume_at + 1, None
            self.resumed.append({"at_step": n, "path_step": self.cursor})
            return True
        self.resume_misses += 1
        if self.resume_misses >= RESUME_TRIES:
            self.resume_at = None
        return False

    # -- recording what this run does ----------------------------------------------------------------------------------
    def record(self, operation: str, obs: dict, el: dict | None, attrs: dict | None, value_key: str | None,
               option_text: str | None, wait_ms: int, busy: bool = False, replayed_from: dict | None = None, read_attrs=None) -> None:
        """An executed action of this run as a path step. A replayed step is kept as it was saved (this run waited for
        nothing in Jev's place, so its own wait says nothing) and advances the cursor. `busy`: the action was decided
        on a page still under a blank layer, so a replay need not wait for the layer to lift."""
        step: dict = {"operation": operation, "page": page_print(obs, self.tokens), "wait_ms": int(wait_ms)}
        if busy:
            step["busy"] = True
        if el is not None and replayed_from is None:
            step["target"] = describe_target(el, attrs, self.tokens, option_text)
            # more than one control answers this description: which of them it was, counted among themselves
            pool, _, _ = candidates(step["target"], obs.get("elements") or [], operation, self.spec, self.tokens, read_attrs)
            if len(pool) > 1 and any(e["idx"] == el["idx"] for e in pool):
                step["target"].update({"nth": [e["idx"] for e in pool].index(el["idx"]), "of": len(pool)})
        if value_key:
            step["value_key"] = value_key
        if replayed_from is not None:
            step = {**replayed_from}
            self.replayed += 1
            self.cursor += 1
        self.recorded.append(step)

    def set_final(self, obs: dict, wait_ms: int, busy: bool = False) -> None:
        self.final = {"page": page_print(obs, self.tokens), "wait_ms": int(wait_ms)}
        if busy:
            self.final["busy"] = True  # the run ended on a page with no controls (a bare confirmation): a replay does not wait for some

    # -- the account -----------------------------------------------------------------------------------------------------
    @property
    def fully_replayed(self) -> bool:
        return self.path is not None and self.handed_back is None and self.replayed == len(self.path["steps"])

    def finish(self, trace: dict, save: bool = True) -> dict:
        """After the run: write the path when the run passed and this is not the saved path walked to its end, and
        return the account for result.json (`result.replay`)."""
        passed = trace.get("status") == "passed"
        if not save:
            self.saved, self.save_note = False, "saving is off"
        elif not passed:
            self.saved, self.save_note = False, "only a passing run's path is saved"
        elif self.fully_replayed and self.path.get("outcome") == trace.get("outcome"):
            self.saved, self.save_note = False, "the saved path was replayed to its end and stands"
        elif any(s.get("operation") not in REPLAYABLE for s in self.recorded):
            self.saved, self.save_note = False, "the run used an operation that is not replayed"
        else:
            usage = trace.get("usage") or {}
            path = {
                "format": PATH_FORMAT,
                "spec_id": self.spec["id"],
                "spec_sha256": spec_key(self.spec),
                "options": run_options(self.spec),
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "recorded_run": {"duration_ms": trace.get("duration_ms"), "jev_requests": usage.get("jev_requests"),
                                 "input_tokens": usage.get("input_tokens")},
                "outcome": trace.get("outcome"),
                "verdict": "pass",
                "steps": self.recorded,
                "final": self.final or (self.path or {}).get("final"),
            }
            try:
                save_path(self.file, path)
                self.saved = True
            except OSError as e:  # a read-only checkout: the run's result stands, the next run asks Jev again
                self.saved, self.save_note = False, f"the path could not be written ({type(e).__name__}: {str(e)[:120]})"
        steps = trace.get("steps") or []
        acted = [s for s in steps if (s.get("executed") or {}).get("action") in REPLAYABLE and not (s.get("executed") or {}).get("reason")]
        out: dict = {
            "path": self.file.replace(os.sep, "/"),
            "used": self.path is not None,
            "steps_in_path": len(self.path["steps"]) if self.path else None,
            "steps_replayed": self.replayed,
            "steps_by_jev": sum(1 for s in acted if not s.get("replayed")),  # executed actions Jev chose in this run
            "handed_back": self.handed_back,  # {at_step, path_step, reason} when Jev took over before the path's end
            "resumed": self.resumed,  # after a handover: [{at_step, path_step}] where Jev's action was the saved step and the path went on
            "waited_ms": self.waited_ms,  # spent waiting for saved steps' pages
            "verified_by": self.verified_by,  # how the ending was decided after a full replay: "jev" | "assertions"
            "saved": bool(self.saved),
        }
        if self.path is None:
            out["not_used"] = self.not_used
        if self.save_note:
            out["save_note"] = self.save_note
        if self.path is not None and not passed and self.replayed:
            out["note"] = ("this run walked saved steps before it ended without a pass: run it once more with --no-replay "
                           "before reading the ending as the application's")
        return out
