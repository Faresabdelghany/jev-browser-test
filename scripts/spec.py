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
}
SETUP_ACTIONS = {"goto", "click", "fill", "press", "wait", "wait_for", "select"}
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
    # 4000 chars of viewport-first text: the toast the checks look for must not be crowded out by the header.
    # screenshots "key": only terminal and flagged steps (plus final.png); true = every step; false = none.
    "observation": {"max_elements": 200, "max_text_chars": 4000, "screenshots": "key"},
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
        if name in RESERVED_QUESTIONS:
            errors.append(f"check '{name}' collides with a reserved question name {sorted(RESERVED_QUESTIONS)}")
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
    if not spec.get("done_when"):
        errors.append("'done_when' must list at least one check; otherwise nothing defines success")

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
    if not (1 <= int(b.get("max_steps", 1)) <= 200):
        errors.append("'budget.max_steps' must be between 1 and 200")
    br = spec.get("browser", {})
    settle_ms, quiet_ms = br.get("settle_ms", 0), br.get("quiet_ms", 0)
    if not (isinstance(settle_ms, int) and not isinstance(settle_ms, bool) and 0 <= settle_ms <= 10000):
        errors.append("'browser.settle_ms' must be an integer between 0 and 10000 (the cap on the post-action settle)")
    elif not (isinstance(quiet_ms, int) and not isinstance(quiet_ms, bool) and 0 <= quiet_ms <= settle_ms):
        errors.append("'browser.quiet_ms' must be an integer between 0 and browser.settle_ms")
    cdp = br.get("cdp_url")
    if cdp is not None and not (isinstance(cdp, str) and cdp.startswith(("http://", "https://", "ws://", "wss://"))):
        errors.append("'browser.cdp_url' must be an http(s):// or ws(s):// URL of a browser's remote-debugging endpoint")
    t = spec.get("thresholds", {})
    for k in ("check_true", "never_true", "min_confidence"):
        v = t.get(k, 0.5)
        if not (0.0 <= float(v) <= 1.0):
            errors.append(f"'thresholds.{k}' must be between 0 and 1")
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
    print(f"OK: spec '{spec['id']}' is valid")
    print(f"  goal: {spec['goal']}")
    print(f"  checks: {', '.join(spec['checks'])}")
    print(f"  done_when: {spec['done_when']}  never: {spec['never']}")
    print(f"  data keys: {list(spec['data'])}  secrets: {spec['secrets']}")
    print(f"  budget: {spec['budget']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
