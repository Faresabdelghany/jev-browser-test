"""Load and validate a test spec.

A spec is the contract Claude writes before a run. See references/spec-format.md.
Run `python scripts/spec.py path/to/spec.json` to validate a spec without a browser.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import random
import re
import sys
import time

RESERVED_QUESTIONS = {
    "operation",
    "click_target",
    "type_target",
    "type_value",
    "select_target",
    "hover_target",
    "upload_target",
    "upload_file",
    "outcome",
    "blocked_reason",
    "stuck_reason",
    "evidence_line",
    "evidence_present",
}


def is_reserved_question(name: str) -> bool:
    """A check or outcome name the runner uses as a question key: the fixed set above plus the per-sentence
    evidence keys `evidence_line_1`, `evidence_line_2`, … of a compound outcome statement."""
    return name in RESERVED_QUESTIONS or re.fullmatch(r"evidence_line_\d+", name) is not None


OUTCOME_NONE = "none_yet"  # the outcome Choice's "nothing listed is visible yet" option; not a valid outcome name
# `after` on an outcome: {"click": "Search"} counts the outcome only once an executed CLICK targeted a control whose
# label contains "Search" (case-insensitive); "type" -> TYPE_TEXT, "select" -> SELECT; several keys all have to hold
AFTER_OPERATIONS = {"click": "CLICK", "type": "TYPE_TEXT", "select": "SELECT"}
UNDETERMINED = "undetermined"  # result.outcome when the run ended in no declared outcome
VERDICTS = ("pass", "bug", "test_issue", "needs_human")
# every status a run can end in (run_test.TERMINAL_STATUSES has the meanings); `expect.status` is validated against it
STATUSES = ("passed", "outcome", "assert_failed", "done_unverified", "blocked", "never_violated", "stuck", "low_confidence",
            "budget_exhausted", "unstable_page", "error")
EXPECT_FIELDS = ("outcome", "status", "verdict", "blocked_reason", "stuck_reason", "suggested_verdict")
ASSERTIONS = {
    "url_matches": str,       # Playwright's URL glob over the final URL: ** any chars, * any chars but /, {a,b} either
    "text_contains": str,     # substring of the final page's visible text (body.innerText)
    "text_in": dict,          # {"selector": css, "contains" | "equals": ...}: text inside the matched element(s) only
    "text_order": list,       # strings that must appear in the page text in this order (a sorted list, a menu)
    "field_value": dict,      # {"label": ..., "equals": ...}: a text field / select found by its accessible name
    "element_present": dict,  # {"role": ..., "name"?: ...} in the final element table
    "element_absent": dict,   # the same shape, must not be there
    # What the browser itself recorded during the run (run_test's diagnostics), not what the final page shows:
    "no_page_errors": bool,      # true: no uncaught JavaScript exception was thrown on the page
    "no_failed_requests": bool,  # true: no request failed outright and no response had a 5xx status
}
DIAGNOSTIC_ASSERTIONS = ("no_page_errors", "no_failed_requests")
# The scripted steps of `setup` and `teardown` (plain Playwright, no Jev). Every step that takes a `selector` may
# also take `frame`: the CSS selector of the <iframe> the element lives in (a list for nested frames).
SETUP_ACTIONS = {"goto", "click", "fill", "press", "wait", "wait_for", "select", "hover", "check", "uncheck", "upload", "drag"}
SETUP_FIELDS = {
    "goto": ["url"],
    "click": ["selector"],
    "fill": ["selector", "value"],
    "press": ["selector", "key"],
    "wait": ["ms"],
    "select": ["selector", "value"],
    "wait_for": [],
    "hover": ["selector"],     # a menu that opens on hover: the pointer stays there for the next step
    "check": ["selector"],     # a checkbox or radio, set (idempotent, unlike click)
    "uncheck": ["selector"],
    "upload": ["selector", "path"],  # an <input type=file>; `path` is a file path or a list of them, relative to the working directory
    "drag": ["selector", "to"],      # drag `selector` onto the element `to` selects
}
EXTRA_OPERATIONS = ("HOVER",)  # operations a spec turns on with `extra_operations` (policy.py offers them only then)
SECRET_MIN_LEN = 6  # a shorter secret is masked wherever it occurs and rewrites unrelated page text: a warning, not a problem
ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")
DOTENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RUN_STAMP_VAR = "RUN_STAMP"  # `${RUN_STAMP}`: made up once per run (or taken from the environment when set there)
RUN_STAMP_TOKEN = "${" + RUN_STAMP_VAR + "}"
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def new_run_stamp(now: float | None = None, rand=None) -> str:
    """A value unique to this run for data the application keeps (a username, a last name, a title): the
    current epoch second in base 36 (six characters, unique across runs and days) followed by two random base-36
    characters (unique across the workers a suite starts in the same second). Eight lowercase letters and digits,
    so it fits a username, a last name or an id field. The environment's RUN_STAMP wins over a fresh one
    (see load_spec): export it to rerun a spec against, or clean up after, the data an earlier run created."""
    n = int(time.time() if now is None else now)
    digits = ""
    while n > 0:
        digits = _BASE36[n % 36] + digits
        n //= 36
    r = random.SystemRandom() if rand is None else rand
    return digits.rjust(6, "0")[-6:] + "".join(r.choice(_BASE36) for _ in range(2))

# `${DATE}`: the day of the run, and days counted from it, written the way the application wants its dates:
# `${DATE}`, `${DATE+30d}`, `${DATE-7d}`, `${DATE+30d+wed}`, `${DATE+30d+workday:dd/mm/yyyy}`. After DATE come terms,
# applied left to right, and an optional `:format`. A spec that types a literal date goes red the day that date has
# passed (live: a leave assigned for 2026-14-10 was listed as Taken, not Scheduled, once it had; the next literal
# would have done the same on 17 December). `+workday` reads the spec's `calendar`: the days of the work week and
# the application's holidays, because "30 days from now" is a Saturday two days in seven and a holiday now and then
# (live, the same form: 'Failed to Submit: No Working Days Selected' for a Saturday and for Remembrance Day).
DATE_RE = re.compile(r"\$\{DATE((?:[+-][^{}:+-]*)*)(?::([^{}]*))?\}")
RUN_DATE_VAR = "RUN_DATE"  # the environment's RUN_DATE=yyyy-mm-dd is the day `${DATE}` counts from (default: today)
_DATE_LEFTOVER_RE = re.compile(r"\$\{DATE(?![A-Z0-9_])[^}\s\"']*\}?")  # what is still there after substitution: not `${DATE_FROM}`
_DATE_TERM_RE = re.compile(r"([+-])(?:(\d{1,5})d|(mon|tue|wed|thu|fri|sat|sun|workday))")
_HOLIDAY_RE = re.compile(r"(?:(\d{4})-)?(\d{2})-(\d{2})")  # "12-25" (every year) or "2026-12-28" (that year only)
WORKDAY_SEARCH_DAYS = 366  # how far `workday` looks for a working day before it gives up (a calendar with none)
_DATE_TOKEN_RE = re.compile(r"yyyy|yy|mmmm|mmm|mm|m|dddd|ddd|dd|d")
DATE_DEFAULT_FORMAT = "yyyy-mm-dd"
_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# English names written out here: strftime's follow the machine's locale, and a spec means the same on every machine
_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def format_date(day: datetime.date, fmt: str = DATE_DEFAULT_FORMAT) -> str:
    """`day` written with `fmt`: yyyy / yy the year, mm / m the month's number (with and without a leading zero),
    mmmm / mmm its English name (December / Dec), dd / d the day of the month, dddd / ddd the English weekday
    (Wednesday / Wed). Every other character is kept as written, so `yyyy-dd-mm`, `dd/mm/yyyy`, `d mmmm yyyy`
    and `dddd d mmmm yyyy` are all formats."""
    parts = {"yyyy": f"{day.year:04d}", "yy": f"{day.year % 100:02d}", "mmmm": _MONTH_NAMES[day.month - 1],
             "mmm": _MONTH_NAMES[day.month - 1][:3], "mm": f"{day.month:02d}", "m": str(day.month),
             "dddd": _DAY_NAMES[day.weekday()], "ddd": _DAY_NAMES[day.weekday()][:3], "dd": f"{day.day:02d}", "d": str(day.day)}
    return _DATE_TOKEN_RE.sub(lambda m: parts[m.group(0)], fmt)


def calendar_problems(calendar) -> list[str]:
    """Problems of a spec's `calendar` (empty list means valid): `workweek`, the days people work, as a non-empty list
    of mon ... sun, and `holidays`, the days the application treats as non-working, each "mm-dd" (every year) or
    "yyyy-mm-dd" (that year only)."""
    if not isinstance(calendar, dict):
        return ["'calendar' must be an object: {\"workweek\": [\"mon\", ..., \"fri\"], \"holidays\": [\"12-25\", \"2026-12-28\"]}"]
    errors = [f"calendar: unknown key '{k}' (workweek, holidays)" for k in calendar if k not in ("workweek", "holidays")]
    week = calendar.get("workweek", list(_DAY_KEYS[:5]))
    if not isinstance(week, list) or not week or any(d not in _DAY_KEYS for d in week):
        errors.append(f"calendar.workweek must be a non-empty list of {list(_DAY_KEYS)} (the days people work)")
    holidays = calendar.get("holidays", [])
    if not isinstance(holidays, list):
        return errors + ["calendar.holidays must be a list of \"mm-dd\" (every year) or \"yyyy-mm-dd\" (that year only) strings"]
    for h in holidays:
        m = _HOLIDAY_RE.fullmatch(h) if isinstance(h, str) else None
        try:
            if not m:
                raise ValueError
            datetime.date(int(m.group(1) or 2024), int(m.group(2)), int(m.group(3)))  # 2024: a leap year, so "02-29" is a day
        except ValueError:
            errors.append(f"calendar.holidays: {h!r} is not a day (write \"12-25\" for every year, \"2026-12-28\" for one)")
    return errors


def is_workday(day: datetime.date, calendar: dict | None = None) -> bool:
    """Is `day` a working day of the spec's `calendar`: one of its `workweek` days (Monday to Friday when not given)
    and not one of its `holidays`?"""
    cal = calendar or {}
    if _DAY_KEYS[day.weekday()] not in cal.get("workweek", _DAY_KEYS[:5]):
        return False
    return f"{day.month:02d}-{day.day:02d}" not in cal.get("holidays", ()) and day.isoformat() not in cal.get("holidays", ())


def shift_date(day: datetime.date, terms: str, calendar: dict | None = None) -> datetime.date:
    """Apply a `${DATE...}` placeholder's terms to `day`, left to right. `+30d` / `-7d`: that many days later /
    earlier. `+wed` (mon ... sun): on to the next Wednesday, staying on a day that already is one; `-wed`: back to
    the last one. `+workday`: on to the next working day of `calendar` (is_workday), staying on a day that already is
    one; `-workday`: back to the last one. Raises ValueError naming the first term it cannot read, a date outside the
    calendar, or a `calendar` with no working day."""
    pos = 0
    for m in _DATE_TERM_RE.finditer(terms):
        if m.start() != pos:
            break
        pos = m.end()
        sign = 1 if m.group(1) == "+" else -1
        try:
            if m.group(2) is not None:
                day = day + datetime.timedelta(days=sign * int(m.group(2)))
            elif m.group(3) == "workday":
                for _ in range(WORKDAY_SEARCH_DAYS):
                    if is_workday(day, calendar):
                        break
                    day = day + datetime.timedelta(days=sign)
                else:
                    raise ValueError(f"'{m.group(0)}' finds no working day in {WORKDAY_SEARCH_DAYS} days: check the spec's calendar")
            else:
                day = day + datetime.timedelta(days=sign * ((sign * (_DAY_KEYS.index(m.group(3)) - day.weekday())) % 7))
        except OverflowError:
            raise ValueError(f"'{m.group(0)}' leaves the calendar") from None
    if pos != len(terms):
        raise ValueError(f"cannot read '{terms[pos:]}' (terms are +Nd / -Nd, +mon ... +sun, +workday, and the same with -)")
    return day


def run_date(env=None) -> datetime.date:
    """The day `${DATE}` counts from: the environment's RUN_DATE (yyyy-mm-dd) when set, else today on this machine's
    clock. Raises ValueError for a RUN_DATE that is not a date."""
    pinned = ((os.environ if env is None else env).get(RUN_DATE_VAR) or "").strip()
    if not pinned:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(pinned)
    except ValueError:
        raise ValueError(f"{RUN_DATE_VAR}={pinned!r} is not a date (yyyy-mm-dd)") from None


def substitute_dates(value, today: datetime.date, problems: list[str], found: dict | None = None, calendar: dict | None = None):
    """Replace every `${DATE...}` in strings, recursively, with the date it names counted from `today` (`calendar`: the
    spec's, for `workday`). A placeholder that cannot be read is left as written and named in `problems`; `found`
    collects placeholder -> date. `${DATE_X}` and every other `${NAME}` are not dates: substitute_env reads those
    from the environment."""
    if isinstance(value, str):

        def repl(m):
            try:
                if m.group(2) is not None and not _DATE_TOKEN_RE.search(m.group(2)):
                    raise ValueError(f"the format '{m.group(2)}' names no part of a date (yyyy, mm, dd, mmm, ddd, ...)")
                text = format_date(shift_date(today, m.group(1), calendar), DATE_DEFAULT_FORMAT if m.group(2) is None else m.group(2))
            except ValueError as e:
                problems.append(f"{m.group(0)}: {e}")
                return m.group(0)
            if found is not None:
                found[m.group(0)] = text
            return text

        out = DATE_RE.sub(repl, value)
        for left in _DATE_LEFTOVER_RE.findall(out):  # `${DATE 30d}`, `${DATE+30d`: never a date, and not an environment variable
            if not any(p.startswith(left + ":") for p in problems):
                problems.append(f"{left}: not a date placeholder (write ${{DATE}}, ${{DATE+30d}}, ${{DATE+30d+wed:dd/mm/yyyy}})")
        return out
    if isinstance(value, list):
        return [substitute_dates(v, today, problems, found, calendar) for v in value]
    if isinstance(value, dict):
        return {k: substitute_dates(v, today, problems, found, calendar) for k, v in value.items()}
    return value


DEFAULTS = {
    "notes": "",
    # What `${DATE...+workday}` calls a working day: the days of the work week, and the days the application under test
    # treats as holidays ("mm-dd" every year, "yyyy-mm-dd" one year). Read by the date placeholders only.
    "calendar": {"workweek": ["mon", "tue", "wed", "thu", "fri"], "holidays": []},
    "data": {},
    "secrets": [],
    # Files Jev may attach, by name: {"cv": "fixtures/cv.pdf"} (paths relative to the directory the run starts in,
    # ${ENV} allowed). Declaring any offers the operation UPLOAD_FILE wherever the page has a file field, hidden ones
    # included; Jev picks the field and the name, the runner sets the file. Empty: file fields are not upload targets.
    "files": {},
    # Operations beyond the standing set, offered only when listed: "HOVER" (move the pointer over an element to open
    # a menu that only shows on hover). Off by default because every operation offered is a choice on every step.
    "extra_operations": [],
    "setup": [],
    # Scripted steps after the verdict, whatever it was (delete the record the flow created, log out): the same
    # actions as `setup`. Best effort: a failing step is recorded (trace.teardown, result.teardown) and never changes
    # the outcome, the verdict or the exit code.
    "teardown": [],
    "checks": {},
    "done_when": [],
    "never": [],
    # The results contract: the endings Claude accepts back, each with a pre-declared verdict, and exact
    # expectations checked in code on the final page. See references/spec-format.md. When `outcomes` is
    # empty the runner synthesizes them from done_when / never (see effective_outcomes below).
    "outcomes": {},
    "assert": [],
    "auto_done": True,
    "fail_fast": True,
    # How a pass sighting is confirmed. "assert": when the spec has an `assert` block and every assertion already holds
    # on the page the pass was seen on, that is the confirmation (in code, at once; the evidence line then costs one
    # request); otherwise, and always with "recheck", the runner pauses settle_ms, observes again and asks Jev once
    # more (the evidence questions ride in that request). Measured on the demo login: "assert" saves ~0.5 s a pass.
    "confirm": "assert",
    # When the evidence line is asked. "always": for every declared outcome (the page's own words in result.evidence.line).
    # "failures": not for a pass whose assertions all hold. The assertions are then the proof, each with the value found,
    # and the request that would have fetched the line is not made: one Jev request fewer on every such pass (one of
    # five on the demo login), which is what a regression suite pays for most. A pass with no assertions, and every
    # outcome that is not a pass, still gets its line.
    "evidence": "always",
    # Attach the standing rules (scripts/rules.py) to every question. Measured on the demo site they lowered
    # decision confidence in every wording tried (docs/superpowers/measurements/2026-09-22-track1-ab-*.json),
    # so they are opt-in for apps where Jev repeats no-op actions or needs the untrusted-page-text guard.
    "rules": False,
    # Replay (scripts/replay.py): remember the path of a passing run and walk it again without asking Jev. Off unless
    # the spec says `"replay": true` (or an object) or the run is started with --replay. `verify`: how the ending of a
    # fully replayed run is decided. "jev": one request asks which declared outcome the page shows, then the
    # assertions, as in any run. "assert": a spec with assertions is decided by them alone when they all hold on the
    # page the recorded run ended on (no request; without assertions it is "jev"). `dir`: where paths are kept
    # (default .jev/paths, which ignores itself for git). A path holds no typed value, only the keys of `data`.
    # `"replay": "never"` (never: true) keeps a spec out of replay even when the run is started with --replay.
    "replay": {"enabled": False, "verify": "jev", "dir": None},
    "budget": {"max_steps": 25, "max_seconds": 240},
    "thresholds": {
        "check_true": 0.8,
        "never_true": 0.8,
        "outcome_true": 0.8,  # an outcome is seen when the outcome Choice gives it at least this probability
        "min_confidence": 0.5,
        "max_low_confidence_steps": 3,
        "max_repeat": 3,
        "max_stale": 3,  # consecutive decisions invalidated by the page changing -> unstable_page
        # A CLICK / TYPE_TEXT / SELECT decided below this while controls sit under a blank layer (covered_controls > 0
        # and the layer has no controls of its own: a form still loading, a request in flight) is deferred: a wait
        # ending when the page changes, settle_ms x 1, 2, 4, 4, 4 on one page (run_test.deferral_limit), then Jev
        # decides again. A layer with controls of its own (a dialog, an open list) defers nothing. Live, the first name
        # went into the sidebar's menu filter at 0.54-0.90 in every PIM run while the form's fields were covered (the
        # right fields read 0.84-0.99), and a Leave flow clicked the Leave List tab at 0.71-0.74 while the spinner
        # before the 'Balance not sufficient' dialog covered the form; was 0.8, and the deferral fired once per page.
        # 0 turns the deferral off.
        "covered_action_confidence": 0.9,
    },
    "browser": {
        "headless": True,
        "viewport": [1280, 800],
        "settle_ms": 400,   # cap on the event-based settle after every action
        "quiet_ms": 100,    # the DOM must stay unchanged this long (and 2 animation frames) before observing
        "action_timeout_ms": 8000,
        "navigation_timeout_ms": 30000,  # the start URL and setup `goto`s: a slow shared host is not a flow outcome
        "storage_state": None,
        "channel": None,
        "cdp_url": None,    # attach to a running browser (Chrome started with --remote-debugging-port) instead of launching
        # A Playwright device name ("iPhone 13", "Pixel 7", "iPad Mini"): its viewport, user agent, pixel ratio and
        # touch replace `viewport`. Ignored when attached to a running browser (that browser is what it is).
        "device": None,
        # A click that opens a new tab (target=_blank, window.open): true carries the run on in that tab, as a person
        # would; false (the default) stays on the page it started on and flags the step NEW-TAB.
        "follow_new_tabs": False,
    },
    # 200 elements: the Choice cap is 255 and the table-row "stuck" seen in real runs was truncation at 60.
    # 2000 chars of viewport-first text (lever F5; was 4000): what is on screen comes first, so the toast the checks
    # look for is not crowded out by the header; a long article's four steps each saved ~450 tokens at no change.
    # screenshots "key": only terminal and flagged steps (plus final.png); true = every step; false = none.
    # frames: CSS selectors of <iframe>s whose controls Jev may use as well (a payment form, an embedded widget): their
    # elements join the table after the page's own, marked with the frame. Empty = the main frame only, as before.
    # shadow_dom: also observe inside open shadow roots (web components): their controls join the table, their text the
    # state, and assertions and evidence lines look there too. On by default since 0.6.0: on the 22 example specs it
    # changed nothing (no example page has a shadow root: identical observations, A/B 2026-11-17), and on pages built
    # from web components it is the difference between seeing the page and not (the Polymer shop: a stall without it,
    # a pass with it; MDN: 0/5 without, 5/5 with). False: the document's own tree only, the 0.5 behaviour.
    "observation": {"max_elements": 200, "max_text_chars": 2000, "screenshots": "key", "frames": [], "shadow_dom": True},  # lever F5: was 4000
}


def _merge(defaults: dict, given: dict) -> dict:
    out = copy.deepcopy(defaults)
    for k, v in given.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def substitute_env(value, missing: list[str], extra: dict | None = None):
    """Replace ${VAR} with os.environ[VAR] in strings, recursively. `extra` holds values that are not environment
    variables (the run stamp); a name found in neither is appended to `missing` and left as written."""
    if isinstance(value, str):

        def repl(m):
            name = m.group(1)
            if extra and name in extra:
                return extra[name]
            if name not in os.environ:
                missing.append(name)
                return m.group(0)
            return os.environ[name]

        return ENV_RE.sub(repl, value)
    if isinstance(value, list):
        return [substitute_env(v, missing, extra) for v in value]
    if isinstance(value, dict):
        return {k: substitute_env(v, missing, extra) for k, v in value.items()}
    return value


HEADED_ENV = "JEV_HEADED"  # a standing preference in .env or the environment: 1/true/yes/on/headed, 0/false/no/off/headless
_HEADED_WORDS = {"1", "true", "yes", "on", "headed"}
_HEADLESS_WORDS = {"0", "false", "no", "off", "headless"}


def resolve_headless(spec_headless: bool, headed: bool = False, headless: bool = False, env=None) -> bool:
    """The browser mode for a launch. A CLI flag (`--headed` / `--headless`) wins; then `JEV_HEADED` in the
    environment (loaded from .env by then); then the spec's `browser.headless`. An empty or unreadable
    JEV_HEADED is ignored. Attached mode (`browser.cdp_url`) never looks at this: that browser is already open."""
    if headed:
        return False
    if headless:
        return True
    word = ((os.environ if env is None else env).get(HEADED_ENV) or "").strip().lower()
    if word in _HEADED_WORDS:
        return False
    if word in _HEADLESS_WORDS:
        return True
    return bool(spec_headless)


def load_dotenv(path: str = ".env") -> list[str]:
    """Load KEY=VALUE lines from `path` into os.environ; variables already set win.

    Keeps the key out of the shell history and out of specs: a `.env` in the directory the
    runner is started from is read by both run_test.py and spec.py, so validation and the run
    see the same environment. Blank lines and `#` comments are skipped, a leading `export ` is
    allowed, and matching quotes around a value are removed. Returns the names that were set.
    """
    loaded: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return loaded
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not DOTENV_NAME_RE.match(name) or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value
        loaded.append(name)
    return loaded


def validate_step(list_name: str, i: int, step) -> list[str]:
    """Problems of one scripted `setup` / `teardown` step (empty list means valid)."""
    errors: list[str] = []
    act = step.get("action") if isinstance(step, dict) else None
    if act not in SETUP_ACTIONS:
        return [f"{list_name}[{i}]: action must be one of {sorted(SETUP_ACTIONS)}"]
    for field in SETUP_FIELDS[act]:
        if field not in step:
            errors.append(f"{list_name}[{i}] ({act}): missing '{field}'")
    if act == "wait_for":
        if not (step.get("selector") or step.get("url")):
            errors.append(f"{list_name}[{i}] (wait_for): needs 'selector' and/or 'url'")
        if step.get("state", "visible") not in ("attached", "detached", "visible", "hidden"):
            errors.append(f"{list_name}[{i}] (wait_for): 'state' must be attached|detached|visible|hidden")
    if act == "upload" and "path" in step:
        paths = step["path"] if isinstance(step["path"], list) else [step["path"]]
        if not paths or any(not isinstance(p, str) or not p.strip() for p in paths):
            errors.append(f"{list_name}[{i}] (upload): 'path' must be a file path or a non-empty list of file paths")
    frame = step.get("frame")
    if frame is not None:
        frames = frame if isinstance(frame, list) else [frame]
        if not frames or any(not isinstance(f, str) or not f.strip() for f in frames):
            errors.append(f"{list_name}[{i}] ({act}): 'frame' must be the CSS selector of an <iframe> (or a list, outermost first)")
        elif not step.get("selector"):
            errors.append(f"{list_name}[{i}] ({act}): 'frame' needs a 'selector' to look for inside that frame")
    return errors


def validate(spec: dict) -> list[str]:
    """Return a list of human-readable problems (empty list means valid)."""
    errors: list[str] = []
    for key in ("id", "start_url", "goal"):
        if not spec.get(key) or not isinstance(spec[key], str):
            errors.append(f"'{key}' is required and must be a non-empty string")
    if "calendar" in spec:
        errors.extend(calendar_problems(spec["calendar"]))
    if "id" in spec and isinstance(spec["id"], str) and not re.fullmatch(r"[A-Za-z0-9._-]+", spec["id"]):
        errors.append("'id' may only contain letters, digits, '.', '_' and '-' (it becomes a folder name)")

    checks = spec.get("checks", {})
    if not isinstance(checks, dict):
        errors.append("'checks' must be an object mapping check_name -> statement")
        checks = {}
    for name, statement in checks.items():
        if is_reserved_question(name):
            errors.append(f"check '{name}' collides with a reserved question name {sorted(RESERVED_QUESTIONS)} (or evidence_line_<n>)")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            errors.append(f"check name '{name}' must be a simple identifier (letters, digits, underscore)")
        if not isinstance(statement, str) or len(statement.strip()) < 8:
            errors.append(f"check '{name}' needs a statement about what is visible on the page")
        elif statement.strip().endswith("?"):
            errors.append(f"check '{name}' should be a statement ('The cart shows 1 item'), not a question")

    for list_name in ("done_when", "never"):
        for name in spec.get(list_name, []):
            if name not in checks:
                errors.append(f"'{list_name}' references unknown check '{name}'")

    outcomes = spec.get("outcomes", {})
    if not isinstance(outcomes, dict):
        errors.append("'outcomes' must be an object mapping outcome_name -> {when, verdict, requires?, note?}")
        outcomes = {}
    for name, o in outcomes.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or name == OUTCOME_NONE or is_reserved_question(name):
            errors.append(f"outcome name '{name}' must be a simple identifier other than '{OUTCOME_NONE}' and the reserved "
                          f"question names {sorted(RESERVED_QUESTIONS)}")
        if not isinstance(o, dict):
            errors.append(f"outcome '{name}' must be an object with 'verdict' and 'when' and/or 'requires'")
            continue
        if o.get("verdict") not in VERDICTS:
            errors.append(f"outcome '{name}': 'verdict' must be one of {list(VERDICTS)}")
        when = o.get("when")
        if when is not None:
            if not isinstance(when, str) or len(when.strip()) < 8:
                errors.append(f"outcome '{name}': 'when' needs a statement about what is visible on the page")
            elif when.strip().endswith("?"):
                errors.append(f"outcome '{name}': 'when' should be a statement, not a question")
        requires = o.get("requires", [])
        if not isinstance(requires, list) or any(not isinstance(r, str) or r not in checks for r in requires):
            errors.append(f"outcome '{name}': 'requires' must list known check names")
        if when is None and not requires:
            errors.append(f"outcome '{name}' needs a 'when' statement and/or 'requires' checks")
        if "note" in o and not isinstance(o["note"], str):
            errors.append(f"outcome '{name}': 'note' must be a string")
        if "requires_action" in o and not isinstance(o["requires_action"], bool):
            errors.append(f"outcome '{name}': 'requires_action' must be true or false")
        after = o.get("after")
        if after is not None and not (isinstance(after, dict) and after and set(after) <= set(AFTER_OPERATIONS)
                                      and all(isinstance(v, str) and v.strip() for v in after.values())):
            errors.append(f"outcome '{name}': 'after' must be an object with some of {sorted(AFTER_OPERATIONS)} naming the "
                          f"control an executed action must have targeted, e.g. {{\"click\": \"Search\"}}")
    has_pass_outcome = any(isinstance(o, dict) and o.get("verdict") == "pass" for o in outcomes.values())
    if outcomes and not has_pass_outcome:
        errors.append("'outcomes' must declare an outcome with verdict \"pass\" (done_when / never are shorthand for "
                      "outcomes only when none are declared); otherwise nothing defines success")
    if not outcomes and not spec.get("done_when"):
        errors.append("'done_when' must list at least one check, or 'outcomes' must declare an outcome with verdict "
                      "\"pass\"; otherwise nothing defines success")

    assertions = spec.get("assert", [])
    if not isinstance(assertions, list):
        errors.append("'assert' must be a list of single-key objects")
        assertions = []
    for i, a in enumerate(assertions):
        if not isinstance(a, dict) or len(a) != 1:
            errors.append(f"assert[{i}] must be an object with exactly one key, one of {sorted(ASSERTIONS)}")
            continue
        (kind, arg), = a.items()
        if kind not in ASSERTIONS:
            errors.append(f"assert[{i}]: unknown assertion '{kind}' (one of {sorted(ASSERTIONS)})")
        elif kind in DIAGNOSTIC_ASSERTIONS:
            if arg is not True:
                errors.append(f"assert[{i}] ({kind}): write {{\"{kind}\": true}}; leave the assertion out to allow them")
        elif not isinstance(arg, ASSERTIONS[kind]) or (isinstance(arg, str) and not arg.strip()):
            errors.append(f"assert[{i}] ({kind}): expected a {ASSERTIONS[kind].__name__}")
        elif kind == "field_value" and not (isinstance(arg.get("label"), str) and isinstance(arg.get("equals"), str)):
            errors.append(f"assert[{i}] (field_value): needs 'label' and 'equals' strings")
        elif kind == "text_in" and not (isinstance(arg.get("selector"), str) and arg["selector"].strip()
                                        and ("contains" in arg) != ("equals" in arg)
                                        and isinstance(arg.get("contains", arg.get("equals")), str)
                                        and arg.get("contains", arg.get("equals")).strip()):
            errors.append(f"assert[{i}] (text_in): needs a 'selector' string and exactly one of 'contains' / 'equals' (a non-empty string)")
        elif kind == "text_order" and not (len(arg) >= 2 and all(isinstance(t, str) and t.strip() for t in arg)):
            errors.append(f"assert[{i}] (text_order): needs a list of at least two non-empty strings, in the order they must appear")
        elif kind in ("element_present", "element_absent") and not (
            isinstance(arg.get("role"), str) and arg["role"] and isinstance(arg.get("name", ""), str)
        ):
            errors.append(f"assert[{i}] ({kind}): needs a 'role' string and optionally a 'name' string")

    data = spec.get("data", {})
    if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()):
        errors.append("'data' must be an object mapping value_name -> string")
    for s in spec.get("secrets", []):
        if s not in data:
            errors.append(f"'secrets' names '{s}' which is not a key in 'data'")
    files = spec.get("files", {})
    if not isinstance(files, dict) or any(not isinstance(v, str) or not v.strip() for v in files.values()):
        errors.append("'files' must be an object mapping file_name -> path of a file to attach")
    elif any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) for k in files):
        errors.append("'files' keys must be simple identifiers (letters, digits, underscore): Jev picks a file by its key")
    extra = spec.get("extra_operations", [])
    if not isinstance(extra, list) or any(op not in EXTRA_OPERATIONS for op in extra):
        errors.append(f"'extra_operations' must be a list with some of {list(EXTRA_OPERATIONS)}")

    for list_name in ("setup", "teardown"):
        steps = spec.get(list_name, [])
        if not isinstance(steps, list):
            errors.append(f"'{list_name}' must be a list of steps")
            continue
        for i, step in enumerate(steps):
            errors.extend(validate_step(list_name, i, step))

    b = spec.get("budget", {})
    ms = b.get("max_steps", 1)
    if not (isinstance(ms, int) and not isinstance(ms, bool) and 1 <= ms <= 200):
        errors.append("'budget.max_steps' must be an integer between 1 and 200")
    secs = b.get("max_seconds", 1)
    if not (isinstance(secs, (int, float)) and not isinstance(secs, bool) and secs > 0):
        errors.append("'budget.max_seconds' must be a number of seconds greater than 0")
    br = spec.get("browser", {})
    vp = br.get("viewport", [1, 1])
    if not (isinstance(vp, list) and len(vp) == 2 and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in vp)):
        errors.append("'browser.viewport' must be [width, height] in pixels")
    at = br.get("action_timeout_ms", 1)
    if not (isinstance(at, int) and not isinstance(at, bool) and at >= 1):
        errors.append("'browser.action_timeout_ms' must be an integer number of milliseconds >= 1")
    nt = br.get("navigation_timeout_ms", 1)
    if not (isinstance(nt, int) and not isinstance(nt, bool) and nt >= 1):
        errors.append("'browser.navigation_timeout_ms' must be an integer number of milliseconds >= 1")
    settle_ms, quiet_ms = br.get("settle_ms", 0), br.get("quiet_ms", 0)
    if not (isinstance(settle_ms, int) and not isinstance(settle_ms, bool) and 0 <= settle_ms <= 10000):
        errors.append("'browser.settle_ms' must be an integer between 0 and 10000 (the cap on the post-action settle)")
    elif not (isinstance(quiet_ms, int) and not isinstance(quiet_ms, bool) and 0 <= quiet_ms <= settle_ms):
        errors.append("'browser.quiet_ms' must be an integer between 0 and browser.settle_ms")
    device = br.get("device")
    if device is not None and not (isinstance(device, str) and device.strip()):
        errors.append("'browser.device' must be a Playwright device name such as \"iPhone 13\" or \"Pixel 7\"")
    if not isinstance(br.get("follow_new_tabs", False), bool):
        errors.append("'browser.follow_new_tabs' must be true or false")
    cdp = br.get("cdp_url")
    if cdp is not None and not (isinstance(cdp, str) and cdp.startswith(("http://", "https://", "ws://", "wss://"))):
        errors.append("'browser.cdp_url' must be an http(s):// or ws(s):// URL of a browser's remote-debugging endpoint")
    t = spec.get("thresholds", {})
    for k in ("check_true", "never_true", "outcome_true", "min_confidence", "covered_action_confidence"):
        v = t.get(k, 0.5)
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= v <= 1.0):
            errors.append(f"'thresholds.{k}' must be a number between 0 and 1")
    for k in ("max_low_confidence_steps", "max_repeat", "max_stale"):
        v = t.get(k, 1)
        if not (isinstance(v, int) and not isinstance(v, bool) and v >= 1):
            errors.append(f"'thresholds.{k}' must be an integer >= 1")
    o = spec.get("observation", {})
    me = o.get("max_elements", 1)
    if not (isinstance(me, int) and not isinstance(me, bool) and 1 <= me <= 250):
        errors.append("'observation.max_elements' must be an integer between 1 and 250 (a Choice takes at most 255 options)")
    mt = o.get("max_text_chars", 100)
    if not (isinstance(mt, int) and not isinstance(mt, bool) and mt >= 100):
        errors.append("'observation.max_text_chars' must be an integer >= 100")
    fr = o.get("frames", [])
    if not (isinstance(fr, list) and all(isinstance(f, str) and f.strip() for f in fr) and len(fr) <= 5):
        errors.append("'observation.frames' must be a list of at most 5 CSS selectors, one per <iframe> whose controls Jev may use")
    if not isinstance(o.get("shadow_dom", False), bool):
        errors.append("'observation.shadow_dom' must be true or false")
    ss = o.get("screenshots", "key")
    if not (ss is True or ss is False or ss == "key"):
        errors.append("'observation.screenshots' must be true, false or \"key\"")
    for k in ("auto_done", "fail_fast", "rules"):
        if not isinstance(spec.get(k, False), bool):
            errors.append(f"'{k}' must be true or false")
    if spec.get("evidence", "always") not in ("always", "failures"):
        errors.append("'evidence' must be \"always\" (every outcome gets its evidence line) or \"failures\" (a pass whose assertions hold is not asked for one)")
    rp = spec.get("replay", {})
    if not isinstance(rp, dict) or not isinstance(rp.get("enabled", False), bool) or not isinstance(rp.get("never", False), bool):
        errors.append("'replay' must be true, false, \"never\" or an object such as {\"enabled\": true, \"verify\": \"assert\"}")
    else:
        if rp.get("verify", "jev") not in ("jev", "assert"):
            errors.append("'replay.verify' must be \"jev\" (Jev is asked which outcome the final page shows) or \"assert\" "
                          "(a spec with assertions is decided by them alone)")
        if rp.get("dir") is not None and not (isinstance(rp["dir"], str) and rp["dir"].strip()):
            errors.append("'replay.dir' must be a directory path (default .jev/paths)")
    if spec.get("confirm", "assert") not in ("assert", "recheck"):
        errors.append("'confirm' must be \"assert\" (a pass whose assertions all hold is confirmed at once) or \"recheck\" (settle, observe again, ask Jev)")
    expect = spec.get("expect")
    if expect is not None:
        if not isinstance(expect, dict) or not expect:
            errors.append(f"'expect' must be a non-empty object with some of {list(EXPECT_FIELDS)} (the result this spec is expected to end in)")
        else:
            for k, v in expect.items():
                if k not in EXPECT_FIELDS:
                    errors.append(f"'expect.{k}' is not a result field; use {list(EXPECT_FIELDS)}")
                elif k == "verdict" and v is not None and v not in VERDICTS:
                    errors.append(f"'expect.verdict' must be one of {list(VERDICTS)} or null")
                elif k != "verdict" and not isinstance(v, str):
                    errors.append(f"'expect.{k}' must be a string")
            if isinstance(expect.get("status"), str) and expect["status"] not in STATUSES:
                errors.append(f"'expect.status' must be one of {list(STATUSES)}")
            declared = set(outcomes) | {UNDETERMINED} if outcomes else None
            if declared is not None and isinstance(expect.get("outcome"), str) and expect["outcome"] not in declared:
                errors.append(f"'expect.outcome' must be a declared outcome or '{UNDETERMINED}', got '{expect['outcome']}'")
    return errors


def match_expect(result: dict, expect: dict) -> dict:
    """Pure: does a run's result.json match the spec's `expect`? An expected-red spec (a documented breakage, a
    demo account that is broken by design) is green when the result is the one declared, so it can sit in a suite
    gate and go red only when the behaviour changes. Compares the fields named in `expect` (`outcome`, `status`,
    `verdict`, `blocked_reason`, `stuck_reason`, `suggested_verdict`) against the result; returns {expect, actual,
    matched, mismatches} with the actual values of the compared fields."""
    reason = result.get("reason") or {}
    actual_all = {"outcome": result.get("outcome"), "status": result.get("status"), "verdict": result.get("verdict"),
                  "blocked_reason": reason.get("blocked_reason"), "stuck_reason": reason.get("stuck_reason"),
                  "suggested_verdict": reason.get("suggested_verdict")}
    actual = {k: actual_all.get(k) for k in expect}
    mismatches = {k: actual_all.get(k) for k, v in expect.items() if actual_all.get(k) != v}
    return {"expect": dict(expect), "actual": actual, "matched": not mismatches, "mismatches": mismatches}


def spec_warnings(spec: dict) -> list[str]:
    """Advisory notes about a spec that validates. The CLIs print them to stderr; they are never a problem and
    never change an exit code. Today: a `secrets` entry whose value (after `${ENV}` substitution) is shorter
    than SECRET_MIN_LEN characters. `observe.mask_secrets` replaces every occurrence of a secret in what Jev
    sees and in the trace, so a value like `1`, `2024` or `admin` also rewrites unrelated page text (a year in
    a footer, a menu entry) as `<secret>` and can change what Jev decides on. An empty value masks nothing."""
    notes: list[str] = []
    data = spec.get("data") or {}
    for key in spec.get("secrets") or []:
        value = data.get(key)
        if not isinstance(value, str):
            continue  # validate() reports it
        if value == "":
            notes.append(f"secret '{key}' is empty: nothing is masked (is its environment variable set to a value?)")
        elif len(value) < SECRET_MIN_LEN:
            notes.append(f"secret '{key}' resolves to a {len(value)}-character value: every occurrence of a secret is masked in "
                         f"the state Jev sees and in the trace, so a value this short also rewrites unrelated page text "
                         f"(a year, a menu entry) as <secret> and can change what Jev decides on; use a longer test "
                         f"credential, or drop '{key}' from 'secrets' if it is not confidential")
    return notes


def effective_outcomes(spec: dict) -> dict:
    """The outcomes the runner works with: the declared ones, or those synthesized from done_when / never.

    When the spec declares no `outcomes`, `goal_reached` (verdict pass, requires every done_when check at
    check_true) and `never_<check>` (verdict bug, requires that check at never_true) are synthesized, so an
    old-style spec keeps its pass / fail semantics (design §5.1). When outcomes ARE declared they are the whole
    contract: done_when / never are not turned into competing outcomes, because a lone `never` Noul judging
    the same message a declared outcome describes would race the outcome Choice at its own threshold and
    could end a negative test as `bug`. Every outcome comes back with `requires` (a list) and
    `requires_threshold` filled in; synthesized ones carry `synthesized: true`. Declaration order is the
    order of preference when several are seen on the same page."""
    th = spec["thresholds"]
    out: dict = {}
    for name, o in (spec.get("outcomes") or {}).items():
        out[name] = {**o, "requires": list(o.get("requires") or []), "requires_threshold": th["check_true"]}
    if out:
        return out
    if spec.get("done_when"):
        out["goal_reached"] = {"verdict": "pass", "requires": list(spec["done_when"]),
                               "requires_threshold": th["check_true"], "synthesized": True}
    for n in spec.get("never") or []:
        out[f"never_{n}"] = {"verdict": "bug", "requires": [n], "requires_threshold": th["never_true"], "synthesized": True}
    return out


def utf8_stdio() -> None:
    """On Windows, print in UTF-8 whatever the console's code page is. The summaries use ✓, ✗, × and …; a Windows
    console, and a pipe there, default to a legacy code page that cannot encode them, and the print would raise.
    Every script's main() calls this first. Elsewhere it does nothing."""
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def load_spec(path: str, run_stamp: str | None = None, today: datetime.date | None = None) -> dict:
    """Load, apply defaults, substitute ${DATE...} and ${ENV} and validate. Raises ValueError on problems.

    `${RUN_STAMP}` anywhere in the spec (data, goal, outcomes, assertions, setup values) becomes one value for this
    run: `run_stamp` when given, else the environment's RUN_STAMP, else a fresh `new_run_stamp()`. The value used is
    recorded as `spec["run_stamp"]` (None when the spec never mentions it), and from there in the trace and the
    result, so the data a run created can be found in the application afterwards.

    `${DATE...}` anywhere in the spec becomes a date counted from the day of the run (substitute_dates): `today` when
    given, else the environment's RUN_DATE, else this machine's date. `spec["run_date"]` is that day (yyyy-mm-dd) and
    `spec["dates"]` what each placeholder became; both None when the spec has no date placeholder. `+workday` reads
    the spec's `calendar` (its work week and the application's holidays)."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # the spec as written, before any ${...} becomes this run's value: what a saved path was recorded for (replay.py)
    source_sha = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if isinstance(raw, dict) and isinstance(raw.get("replay"), bool):
        raw = {**raw, "replay": {"enabled": raw["replay"]}}  # "replay": true is the short form
    elif isinstance(raw, dict) and raw.get("replay") == "never":
        raw = {**raw, "replay": {"enabled": False, "never": True}}  # not even when the command line says --replay
    spec = _merge(DEFAULTS, raw)
    spec["source"] = {"sha256": source_sha}
    used = RUN_STAMP_TOKEN in json.dumps(raw)
    stamp = run_stamp or os.environ.get(RUN_STAMP_VAR) or new_run_stamp()
    date_problems: list[str] = []
    dates: dict = {}
    if "${DATE" in json.dumps(raw) and not calendar_problems(spec["calendar"]):  # a bad calendar is validate()'s to report
        try:
            day = today or run_date()
            spec = substitute_dates(spec, day, date_problems, dates, spec["calendar"])
        except ValueError as e:  # a RUN_DATE that is not a date
            day = None
            date_problems.append(str(e))
    missing: list[str] = []
    spec = substitute_env(spec, missing, {RUN_STAMP_VAR: stamp})
    spec["run_stamp"] = stamp if used else None
    spec["run_date"] = day.isoformat() if dates else None
    spec["dates"] = dates or None
    errors = validate(spec) + [f"date placeholder {p}" for p in date_problems]
    if missing:
        errors.append("missing environment variables: " + ", ".join(sorted(set(missing))))
    if errors:
        raise ValueError("Spec problems:\n  - " + "\n  - ".join(errors))
    return spec


def main(argv: list[str]) -> int:
    utf8_stdio()
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print("usage: python scripts/spec.py path/to/spec.json\n\nValidates a spec without opening a browser: exit 0 and a summary when it is "
              "valid, exit 1 with the list of problems otherwise. The format is documented in references/spec-format.md.")
        return 0
    if len(argv) != 2:
        print("usage: python scripts/spec.py path/to/spec.json", file=sys.stderr)
        return 2
    load_dotenv()
    try:
        spec = load_spec(argv[1])
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(str(e))
        return 1
    for note in spec_warnings(spec):
        print(f"warning: {note}", file=sys.stderr)
    print(f"OK: spec '{spec['id']}' is valid")
    print(f"  goal: {spec['goal']}")
    print(f"  checks: {', '.join(spec['checks'])}")
    print(f"  done_when: {spec['done_when']}  never: {spec['never']}")
    eff = effective_outcomes(spec)
    print("  outcomes: " + ", ".join(f"{k} -> {v.get('verdict')}{' (synthesized)' if v.get('synthesized') else ''}"
                                    for k, v in eff.items()))
    if spec["outcomes"] and (spec["done_when"] or spec["never"]):
        print("  note: done_when / never are ignored by the runner when outcomes are declared")
    if spec["assert"]:
        print(f"  assert: {len(spec['assert'])} assertion(s) on the final page")
    print(f"  data keys: {list(spec['data'])}  secrets: {spec['secrets']}")
    if spec["files"]:
        print(f"  files: {list(spec['files'])}" + "".join(f"\n    warning: {k}: no such file from here: {v}" for k, v in spec["files"].items() if not os.path.isfile(v)))
    if spec["extra_operations"] or not spec["observation"]["shadow_dom"]:
        print(f"  extra operations: {spec['extra_operations']}  shadow_dom: {spec['observation']['shadow_dom']}")
    if spec.get("run_stamp"):
        print(f"  run stamp: {spec['run_stamp']} (this validation's example; every run makes its own ${{RUN_STAMP}}, export RUN_STAMP to pin one)")
    if spec.get("dates"):
        print(f"  dates, counted from {spec['run_date']} (the day of the run; export {RUN_DATE_VAR}=yyyy-mm-dd to pin another): "
              + ", ".join(f"{k} -> {v}" for k, v in spec["dates"].items()))
    print(f"  budget: {spec['budget']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
