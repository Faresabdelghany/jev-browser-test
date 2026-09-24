"""Scaffold a spec from a URL, a goal and the data values, so the first run costs an edit, not an authoring.

    python scripts/scaffold.py --url URL --goal "..." [--data key=value ...] [--out specs/<id>.json]
        [--id ID] [--secret key ...] [--pass "when"] [--bug "when" ...] [--needs-human "when" ...]
        [--assert-url GLOB] [--assert-text TEXT ...] [--assert-in "css|text" ...]
        [--setup "fill:css=value" | "click:css" | "press:css=Key" | "select:css=value" | "wait_for:css" | "wait_for_url:glob" | "goto:url" ...]
        [--notes "..."] [--slow] [--stdout] [--force]

The result is a spec that validates as the runner loads it (`spec.py` is run on it before it is written): the goal,
the data, a `pass` outcome (the goal's "so that ..." clause, or `--pass`), one `bug` outcome per `--bug` (with
`requires_action`, since a wrong message is never on the start page), the standing `app_error` bug outcome, the
assertions and setup steps given, and only the non-default settings. Nothing is invented: no assertion is emitted
unless one was given (a trivial one would confirm a pass at first sighting), and a `${ENV}` that is not set yet is
kept as written and resolved at run time. Keys that look like credentials (password, secret, token, pin) are listed
in `secrets`. `--slow` is the preset for a slow single-page app (settle 2500 ms, quiet 200 ms, 45 s navigation,
30 steps / 360 s). Exit 0 with the written path and spec.py's summary on stderr; 2 on bad input or an existing file
(`--force` overwrites).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from datetime import date

from spec import DEFAULTS, RUN_STAMP_VAR, _merge, substitute_env, validate

SETUP_SYNTAX = {
    "fill": ("selector", "value"),
    "press": ("selector", "key"),
    "select": ("selector", "value"),
    "click": ("selector",),
    "wait_for": ("selector",),
    "wait_for_url": ("url",),
    "goto": ("url",),
}
SLOW = {"browser": {"settle_ms": 2500, "quiet_ms": 200, "navigation_timeout_ms": 45000},
        "budget": {"max_steps": 30, "max_seconds": 360}}
SLOW_WAIT_TIMEOUT_MS = 45000
SECRET_KEY_RE = re.compile(r"pass(word|wd)?|secret|token|\bpin\b|otp", re.IGNORECASE)
APP_ERROR = {"when": "An error page, a stack trace or 'something went wrong' text is shown", "verdict": "bug"}
SO_THAT_RE = re.compile(r"\bso that\b", re.IGNORECASE)


class ScaffoldError(ValueError):
    pass


def slug(text: str, words: int = 5, sep: str = "-") -> str:
    """The first `words` words of `text` as a folder-safe name (`--id` default) or an identifier (outcome names)."""
    parts = re.findall(r"[A-Za-z0-9]+", text.lower())[:words]
    return sep.join(parts) or "spec"


def outcome_name(when: str, taken: set[str]) -> str:
    base = slug(when, 4, "_")
    if not re.match(r"[A-Za-z_]", base):
        base = "o_" + base
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    return name


def pass_statement(goal: str) -> str:
    """The pass outcome's `when` when none was given: the goal's last 'so that ...' clause, capitalised and without a
    trailing full stop; else the goal itself (the comment tells the author to sharpen it)."""
    parts = SO_THAT_RE.split(goal)
    text = parts[-1].strip() if len(parts) > 1 else goal.strip()
    text = text.rstrip(". ")
    text = re.sub(r"^[,:;\s]+", "", text)
    return text[:1].upper() + text[1:] if text else goal


def parse_data(items: list[str]) -> dict:
    data = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            raise ScaffoldError(f"--data wants key=value with an identifier key, got {item!r}")
        data[key.strip()] = value
    return data


def split_selector(rest: str) -> tuple[str, str, str]:
    """`css=value` split at the first `=` outside brackets and quotes, so `input[name=username]=Admin` keeps its
    attribute selector whole. Returns (selector, "=", value), or (rest, "", "") when there is no such `=`."""
    depth, quote = 0, ""
    for i, c in enumerate(rest):
        if quote:
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "[":
            depth += 1
        elif c == "]":
            depth = max(0, depth - 1)
        elif c == "=" and depth == 0:
            return rest[:i], "=", rest[i + 1:]
    return rest, "", ""


def parse_setup(items: list[str], slow: bool) -> list[dict]:
    steps = []
    for item in items:
        action, sep, rest = item.partition(":")
        if not sep or action not in SETUP_SYNTAX:
            raise ScaffoldError(f"--setup wants one of {', '.join(k + ':...' for k in SETUP_SYNTAX)}, got {item!r}")
        fields = SETUP_SYNTAX[action]
        if len(fields) == 2:
            first, eq, second = split_selector(rest)
            if not eq or not first.strip() or not second.strip():
                raise ScaffoldError(f"--setup {action} wants {action}:{fields[0]}={fields[1]}, got {item!r}")
            values = (first.strip(), second.strip())
        else:
            if not rest.strip():
                raise ScaffoldError(f"--setup {action} wants {action}:{fields[0]}, got {item!r}")
            values = (rest.strip(),)
        step = {"action": "wait_for" if action == "wait_for_url" else action}
        step.update(zip(fields, values))
        if step["action"] == "wait_for" and slow:
            step["timeout_ms"] = SLOW_WAIT_TIMEOUT_MS
        steps.append(step)
    return steps


def parse_assert_in(items: list[str]) -> list[dict]:
    out = []
    for item in items:
        selector, sep, text = item.partition("|")
        if not sep or not selector.strip() or not text.strip():
            raise ScaffoldError(f"--assert-in wants 'css selector|text', got {item!r}")
        out.append({"text_in": {"selector": selector.strip(), "contains": text.strip()}})
    return out


def build(args: argparse.Namespace) -> dict:
    goal = args.goal.strip()
    if len(goal) < 12:
        raise ScaffoldError("--goal is what you would tell a tester in one breath, ending with the visible outcome (at least 12 characters)")
    data = parse_data(args.data)
    secrets = list(dict.fromkeys(list(args.secret) + [k for k in data if SECRET_KEY_RE.search(k)]))
    for s in secrets:
        if s not in data:
            raise ScaffoldError(f"--secret {s!r} is not a --data key")
    spec: dict = {
        "id": args.id or slug(goal),
        "comment": (f"Scaffolded by scripts/scaffold.py on {date.today().isoformat()} from a URL, a goal and {len(data)} data "
                    f"value(s). Edit before the first run: the pass outcome's `when` (one visible fact per sentence, the app's "
                    f"own words), an `assert` block with at least one exact check on the final page, `notes` for Jev about the "
                    f"page, and put the {RUN_STAMP_VAR} placeholder (a dollar sign and braces around the name) into any data value the app keeps. "
                    + ("Keys that look like credentials were listed in `secrets`; give them environment-variable placeholders "
                       "(the form spec-format.md shows under `data`) unless the app publishes them. " if secrets else "")
                    + "references/spec-format.md has every field."),
        "start_url": args.url,
        "goal": goal,
    }
    if args.notes:
        spec["notes"] = args.notes.strip()
    if data:
        spec["data"] = data
    if secrets:
        spec["secrets"] = secrets
    setup = parse_setup(args.setup, args.slow)
    if setup:
        spec["setup"] = setup
    outcomes: dict = {"goal_reached": {"when": (args.pass_when or pass_statement(goal)).strip(), "verdict": "pass"}}
    for when in args.bug:
        outcomes[outcome_name(when, set(outcomes))] = {"when": when.strip(), "verdict": "bug", "requires_action": True}
    for when in args.needs_human:
        outcomes[outcome_name(when, set(outcomes))] = {"when": when.strip(), "verdict": "needs_human"}
    outcomes["app_error"] = dict(APP_ERROR)
    spec["outcomes"] = outcomes
    assertions: list[dict] = []
    if args.assert_url:
        assertions.append({"url_matches": args.assert_url})
    assertions += [{"text_contains": t} for t in args.assert_text]
    assertions += parse_assert_in(args.assert_in)
    if assertions:
        spec["assert"] = assertions
    if args.slow:
        spec.update(copy.deepcopy(SLOW))
    return spec


def check(spec: dict) -> list[str]:
    """spec.validate over the merged spec, with every `${VAR}` stood in for (they resolve at run time)."""
    merged = _merge(DEFAULTS, spec)
    missing: list[str] = []
    resolved = substitute_env(merged, missing, {RUN_STAMP_VAR: "stamp000"})
    if missing:
        stand_ins = {name: f"value_of_{name}" for name in missing}
        resolved = substitute_env(merged, [], {RUN_STAMP_VAR: "stamp000", **stand_ins})
    return validate(resolved)


def summary(spec: dict) -> str:
    lines = [f"OK: spec '{spec['id']}' is valid",
             f"  goal: {spec['goal']}",
             "  outcomes: " + ", ".join(f"{k} -> {v['verdict']}" for k, v in spec["outcomes"].items()),
             f"  data keys: {list(spec.get('data', {}))}  secrets: {spec.get('secrets', [])}",
             f"  assert: {len(spec.get('assert', []))} assertion(s)" + ("" if spec.get("assert") else " (add one: a pass then confirms itself in code)"),
             f"  setup: {len(spec.get('setup', []))} step(s)"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="the page the browser opens (start_url)")
    ap.add_argument("--goal", required=True, help="what a tester would be told, ending with 'so that <the visible outcome>'")
    ap.add_argument("--id", help="spec id and file name (default: the goal's first words)")
    ap.add_argument("--data", action="append", default=[], metavar="KEY=VALUE", help="a value Jev may type (repeatable)")
    ap.add_argument("--secret", action="append", default=[], metavar="KEY", help="a data key to mask (credential-like keys are added by themselves)")
    ap.add_argument("--pass", dest="pass_when", metavar="WHEN", help="the pass outcome's statement (default: the goal's 'so that' clause)")
    ap.add_argument("--bug", action="append", default=[], metavar="WHEN", help="a wrong ending, as a statement about the page (repeatable)")
    ap.add_argument("--needs-human", action="append", default=[], metavar="WHEN", help="an ending only a human can take further (repeatable)")
    ap.add_argument("--assert-url", metavar="GLOB", help="url_matches on the final page (** any, * no slash)")
    ap.add_argument("--assert-text", action="append", default=[], metavar="TEXT", help="text_contains on the final page (repeatable)")
    ap.add_argument("--assert-in", action="append", default=[], metavar="CSS|TEXT", help="text_in: the text inside a CSS-selected element (repeatable)")
    ap.add_argument("--setup", action="append", default=[], metavar="STEP",
                    help="a deterministic step before Jev: fill:css=value, click:css, press:css=Key, select:css=value, wait_for:css, wait_for_url:glob, goto:url")
    ap.add_argument("--notes", help="hints Jev reads every step, about the page and the flow")
    ap.add_argument("--slow", action="store_true", help="the slow single-page-app preset: settle 2500 ms, quiet 200 ms, 45 s navigation, 30 steps / 360 s")
    ap.add_argument("--out", help="where to write (default specs/<id>.json)")
    ap.add_argument("--stdout", action="store_true", help="print the spec instead of writing a file")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args(argv[1:])
    try:
        spec = build(args)
        problems = check(spec)
        if problems:
            raise ScaffoldError("the scaffold does not validate (a bug in scaffold.py or an odd input):\n  - " + "\n  - ".join(problems))
    except ScaffoldError as e:
        print(f"scaffold: {e}", file=sys.stderr)
        return 2
    text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(text, end="")
        print(summary(spec), file=sys.stderr)
        return 0
    out = args.out or os.path.join("specs", spec["id"] + ".json")
    if os.path.exists(out) and not args.force:
        print(f"scaffold: {out} exists; pass --force to overwrite it, or --id / --out for another name", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(summary(spec), file=sys.stderr)
    print(f"  written: {out}  (edit it, then: python scripts/run_test.py {out})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
