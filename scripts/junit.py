"""JUnit XML for a CI dashboard: one `<testcase>` per spec, built from what the runner already wrote.

    python scripts/run_test.py specs/login.json --junit runs/junit.xml
    python scripts/run_suite.py specs/*.json --repeat 3 --junit runs/junit.xml

Standard library only. The mapping keeps the runner's three exit codes apart, because a dashboard that paints an
unreachable host red as a product failure trains people to ignore it:

  * green (a pass, or the result a spec's `expect` declared)   -> a test case with no child
  * red with a verdict (`bug`, `flaky`, `test_issue`, `needs_human`, `undetermined`) -> `<failure type="...">`
  * never a verdict (a spec or environment problem, exit 2)    -> `<error type="environment">`

The failure text carries what a ticket needs: the outcome, the page's own evidence line, the typed reason with its
suggested verdict, and the paths of `result.json` and `trace.json`. Characters XML 1.0 cannot hold are dropped.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

# XML 1.0 allows tab, LF, CR and everything from U+0020 except the surrogates and U+FFFE / U+FFFF
_XML_ILLEGAL = re.compile("[^\u0009\u000A\u000D -퟿-�\U00010000-\U0010FFFF]")


def xml_text(s) -> str:
    return _XML_ILLEGAL.sub("", "" if s is None else str(s))


def _seconds(ms) -> str:
    return f"{(ms or 0) / 1000:.3f}"


def run_case(result: dict, exit_code: int, duration_ms: int | None = None) -> dict:
    """One run's `result.json` as a test case: {name, classname, time_ms, kind, type, message, text}.
    `kind` is "pass", "failure" or "error"."""
    spec_id = result.get("spec_id") or "spec"
    reason = result.get("reason") or {}
    lines = [f"outcome: {result.get('outcome')}", f"status: {result.get('status')}"]
    evidence = (result.get("evidence") or {}).get("line")
    if evidence:
        lines.append(f"evidence: {evidence}")
    for key in ("blocked_reason", "stuck_reason", "suggested_verdict", "phase", "error"):
        if reason.get(key):
            lines.append(f"{key}: {reason[key]}")
    for a in reason.get("failed_assertions") or []:
        lines.append(f"assertion failed: {a}")
    expected = result.get("expected")
    if expected and not expected.get("matched"):
        lines.append(f"expected result not matched: {expected.get('mismatches') or expected}")
    if result.get("trace"):
        lines.append(f"trace: {result['trace']}")
    case = {"name": spec_id, "classname": f"jev.{spec_id}", "time_ms": duration_ms if duration_ms is not None else result.get("duration_ms"),
            "kind": "pass", "type": None, "message": None, "text": "\n".join(lines)}
    if exit_code == 0:
        return case
    if exit_code == 2 or reason.get("phase"):
        case.update(kind="error", type="environment",
                    message=f"not a verdict: {reason.get('phase') or 'spec or environment problem'}: {reason.get('error') or ''}".strip(": "))
        return case
    verdict = result.get("verdict") or reason.get("suggested_verdict") or "undetermined"
    what = f"outcome '{result.get('outcome')}'" if result.get("verdict") else f"undetermined ({result.get('status')})"
    case.update(kind="failure", type=verdict, message=f"{verdict}: {what}" + (f": {evidence}" if evidence else ""))
    return case


def suite_cases(report: dict) -> list[dict]:
    """A suite's `results.json` as test cases, one per spec: its suite verdict decides the colour (`pass` and
    `expected` are green, `flaky` is a failure of type flaky with the outcome distribution), the body lists every run."""
    cases = []
    for spec_id, sp in report.get("specs", {}).items():
        runs = sp.get("runs") or []
        lines = []
        for r in runs:
            what = "environment failure" if r.get("environment_failure") else f"{r.get('outcome')} ({r.get('status')})"
            line = f"run {r.get('run')}: {what}, {(r.get('wall_ms') or 0) / 1000:.1f} s"
            if r.get("evidence_line"):
                line += f", evidence: {r['evidence_line']}"
            if r.get("error"):
                line += f", error: {str(r['error']).strip().splitlines()[-1][:200]}"
            if r.get("result"):
                line += f", result: {r['result']}"
            lines.append(line)
        verdict = sp.get("verdict")
        case = {"name": spec_id, "classname": f"jev.{spec_id}", "time_ms": sum((r.get("wall_ms") or 0) for r in runs),
                "kind": "pass", "type": None, "message": None, "text": "\n".join(lines)}
        observed = [r for r in runs if not r.get("environment_failure")]
        if verdict in ("pass", "expected"):
            pass
        elif runs and not observed:
            case.update(kind="error", type="environment", message=sp.get("reason") or "every run failed before observing a page")
        else:
            counts = ", ".join(f"{k} x{v}" for k, v in (sp.get("outcome_counts") or {}).items())
            case.update(kind="failure", type=verdict or "undetermined",
                        message=f"{verdict}: {counts}" if counts else str(verdict))
        cases.append(case)
    return cases


def render_junit(suite_name: str, cases: list[dict]) -> str:
    failures = sum(1 for c in cases if c["kind"] == "failure")
    errors = sum(1 for c in cases if c["kind"] == "error")
    total_ms = sum(c.get("time_ms") or 0 for c in cases)
    attrs = {"name": suite_name, "tests": str(len(cases)), "failures": str(failures), "errors": str(errors), "skipped": "0",
             "time": _seconds(total_ms)}
    root = ET.Element("testsuites", attrs)
    suite = ET.SubElement(root, "testsuite", attrs)
    for c in cases:
        el = ET.SubElement(suite, "testcase", {"name": xml_text(c["name"]), "classname": xml_text(c["classname"]),
                                               "time": _seconds(c.get("time_ms"))})
        if c["kind"] in ("failure", "error"):
            child = ET.SubElement(el, c["kind"], {"type": xml_text(c["type"]), "message": xml_text(c["message"])})
            child.text = xml_text(c["text"])
        elif c.get("text"):
            ET.SubElement(el, "system-out").text = xml_text(c["text"])
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def write_junit(path: str, suite_name: str, cases: list[dict]) -> str:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_junit(suite_name, cases))
    return path
