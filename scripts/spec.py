"""Load and validate a test spec.

A spec is the contract Claude writes before a run. See references/spec-format.md.
Run `python scripts/spec.py path/to/spec.json` to validate a spec without a browser.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys

RESERVED_QUESTIONS = {
    "operation",
    "click_target",
    "type_target",
    "type_value",
    "select_target",
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
UNDETERMINED = "undetermined"  # result.outcome when the run ended in no declared outcome
VERDICTS = ("pass", "bug", "test_issue", "needs_human")
ASSERTIONS = {
    "url_matches": str,       # Playwright's URL glob over the final URL: ** any chars, * any chars but /, {a,b} either
    "text_contains": str,     # substring of the final page's visible text (body.innerText)
    "field_value": dict,      # {"label": ..., "equals": ...}: a text field / select found by its label
    "element_present": dict,  # {"role": ..., "name"?: ...} in the final element table
    "element_absent": dict,   # the same shape, must not be there
}
SETUP_ACTIONS = {"goto", "click", "fill", "press", "wait", "wait_for", "select"}
SECRET_MIN_LEN = 6  # a shorter secret is masked wherever it occurs and rewrites unrelated page text: a warning, not a problem
ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")
DOTENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULTS = {
    "notes": "",
    "data": {},
    "secrets": [],
    "setup": [],
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
    # Attach the standing rules (scripts/rules.py) to every question. Measured on the demo site they lowered
    # decision confidence in every wording tried (docs/superpowers/measurements/2026-09-22-track1-ab-*.json),
    # so they are opt-in for apps where Jev repeats no-op actions or needs the untrusted-page-text guard.
    "rules": False,
    "budget": {"max_steps": 25, "max_seconds": 240},
    "thresholds": {
        "check_true": 0.8,
        "never_true": 0.8,
        "outcome_true": 0.8,  # an outcome is seen when the outcome Choice gives it at least this probability
        "min_confidence": 0.5,
        "max_low_confidence_steps": 3,
        "max_repeat": 3,
        "max_stale": 3,  # consecutive decisions invalidated by the page changing -> unstable_page
    },
    "browser": {
        "headless": True,
        "viewport": [1280, 800],
        "settle_ms": 400,   # cap on the event-based settle after every action
        "quiet_ms": 100,    # the DOM must stay unchanged this long (and 2 animation frames) before observing
        "action_timeout_ms": 8000,
        "storage_state": None,
        "channel": None,
        "cdp_url": None,    # attach to a running browser (Chrome started with --remote-debugging-port) instead of launching
    },
    # 200 elements: the Choice cap is 255 and the table-row "stuck" seen in real runs was truncation at 60.
    # 2000 chars of viewport-first text (lever F5; was 4000): what is on screen comes first, so the toast the checks
    # look for is not crowded out by the header; a long article's four steps each saved ~450 tokens at no change.
    # screenshots "key": only terminal and flagged steps (plus final.png); true = every step; false = none.
    "observation": {"max_elements": 200, "max_text_chars": 2000, "screenshots": "key"},  # lever F5: was 4000
}


def _merge(defaults: dict, given: dict) -> dict:
    out = copy.deepcopy(defaults)
    for k, v in given.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def substitute_env(value, missing: list[str]):
    """Replace ${VAR} with os.environ[VAR] in strings, recursively."""
    if isinstance(value, str):

        def repl(m):
            name = m.group(1)
            if name not in os.environ:
                missing.append(name)
                return m.group(0)
            return os.environ[name]

        return ENV_RE.sub(repl, value)
    if isinstance(value, list):
        return [substitute_env(v, missing) for v in value]
    if isinstance(value, dict):
        return {k: substitute_env(v, missing) for k, v in value.items()}
    return value


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


def validate(spec: dict) -> list[str]:
    """Return a list of human-readable problems (empty list means valid)."""
    errors: list[str] = []
    for key in ("id", "start_url", "goal"):
        if not spec.get(key) or not isinstance(spec[key], str):
            errors.append(f"'{key}' is required and must be a non-empty string")
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
        elif not isinstance(arg, ASSERTIONS[kind]) or (isinstance(arg, str) and not arg.strip()):
            errors.append(f"assert[{i}] ({kind}): expected a {ASSERTIONS[kind].__name__}")
        elif kind == "field_value" and not (isinstance(arg.get("label"), str) and isinstance(arg.get("equals"), str)):
            errors.append(f"assert[{i}] (field_value): needs 'label' and 'equals' strings")
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

    for i, step in enumerate(spec.get("setup", [])):
        act = step.get("action") if isinstance(step, dict) else None
        if act not in SETUP_ACTIONS:
            errors.append(f"setup[{i}]: action must be one of {sorted(SETUP_ACTIONS)}")
            continue
        need = {
            "goto": ["url"],
            "click": ["selector"],
            "fill": ["selector", "value"],
            "press": ["selector", "key"],
            "wait": ["ms"],
            "select": ["selector", "value"],
            "wait_for": [],
        }[act]
        for field in need:
            if field not in step:
                errors.append(f"setup[{i}] ({act}): missing '{field}'")
        if act == "wait_for":
            if not (step.get("selector") or step.get("url")):
                errors.append(f"setup[{i}] (wait_for): needs 'selector' and/or 'url'")
            if step.get("state", "visible") not in ("attached", "detached", "visible", "hidden"):
                errors.append(f"setup[{i}] (wait_for): 'state' must be attached|detached|visible|hidden")

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
    settle_ms, quiet_ms = br.get("settle_ms", 0), br.get("quiet_ms", 0)
    if not (isinstance(settle_ms, int) and not isinstance(settle_ms, bool) and 0 <= settle_ms <= 10000):
        errors.append("'browser.settle_ms' must be an integer between 0 and 10000 (the cap on the post-action settle)")
    elif not (isinstance(quiet_ms, int) and not isinstance(quiet_ms, bool) and 0 <= quiet_ms <= settle_ms):
        errors.append("'browser.quiet_ms' must be an integer between 0 and browser.settle_ms")
    cdp = br.get("cdp_url")
    if cdp is not None and not (isinstance(cdp, str) and cdp.startswith(("http://", "https://", "ws://", "wss://"))):
        errors.append("'browser.cdp_url' must be an http(s):// or ws(s):// URL of a browser's remote-debugging endpoint")
    t = spec.get("thresholds", {})
    for k in ("check_true", "never_true", "outcome_true", "min_confidence"):
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
    ss = o.get("screenshots", "key")
    if not (ss is True or ss is False or ss == "key"):
        errors.append("'observation.screenshots' must be true, false or \"key\"")
    for k in ("auto_done", "fail_fast", "rules"):
        if not isinstance(spec.get(k, False), bool):
            errors.append(f"'{k}' must be true or false")
    return errors


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


def load_spec(path: str) -> dict:
    """Load, apply defaults, substitute ${ENV} and validate. Raises ValueError on problems."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    spec = _merge(DEFAULTS, raw)
    missing: list[str] = []
    spec = substitute_env(spec, missing)
    errors = validate(spec)
    if missing:
        errors.append("missing environment variables: " + ", ".join(sorted(set(missing))))
    if errors:
        raise ValueError("Spec problems:\n  - " + "\n  - ".join(errors))
    return spec


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/spec.py path/to/spec.json")
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
    print(f"  budget: {spec['budget']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
