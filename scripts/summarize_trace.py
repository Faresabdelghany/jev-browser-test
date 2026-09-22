"""Print a compact summary of a run trace, or the run's result.json.

    python scripts/summarize_trace.py runs/<id>/<ts>/trace.json [--step N] [--result]

Read result.json first when judging a run (`--result` prints it), then this summary; open trace.json
or the step screenshots only for the steps the summary flags. `--step N` dumps one step in full
(element table, probabilities, checks).
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _fmt_conf(step: dict) -> str:
    op = step.get("operation") or {}
    tg = step.get("target") or {}
    a = f"{op.get('confidence', 0):.2f}" if op else "-"
    b = f"{tg.get('confidence', 0):.2f}" if tg and not tg.get("missing") else "-"
    tv = step.get("type_value")
    c = f"/{tv.get('confidence', 0):.2f}" if tv else ""
    return f"{a}/{b}{c}"


def _fmt_checks(checks: dict, spec: dict) -> str:
    if not checks:
        return "-"
    parts = []
    for name, p in checks.items():
        mark = ""
        if name in spec.get("done_when", []):
            mark = "✓" if p >= spec["thresholds"]["check_true"] else "✗"
        elif name in spec.get("never", []):
            mark = "!!" if p >= spec["thresholds"]["never_true"] else "ok"
        parts.append(f"{name}={p:.2f}{mark}")
    return " ".join(parts)


def _flags(step: dict) -> str:
    f = []
    if step.get("low_confidence"):
        f.append("LOW-CONF")
    ex = step.get("executed") or {}
    if ex and ex.get("ok") is False:
        f.append("ACTION-FAILED")
    if ex.get("forced"):
        f.append("FORCED-CLICK")
    if ex.get("dispatched"):
        f.append("DISPATCHED-CLICK")
    if step.get("repeat_count", 0) > 1:
        f.append(f"REPEAT×{step['repeat_count']}")
    if step.get("never_violated"):
        f.append("NEVER:" + ",".join(step["never_violated"]))
    if step.get("outcome_seen"):
        f.append("OUTCOME:" + step["outcome_seen"])
    if step.get("pending_outcome"):
        f.append("PENDING:" + step["pending_outcome"])
    if step.get("outcome_unconfirmed"):
        f.append("UNCONFIRMED:" + step["outcome_unconfirmed"])
    if step.get("assertions") and not all(a.get("ok") for a in step["assertions"]):
        f.append("ASSERT-FAILED")
    if step.get("stale"):
        f.append("STALE")
    if (step.get("target") or {}).get("missing"):
        f.append("NO-TARGET-ANSWER")
    if step.get("invalid_answer"):
        f.append("INVALID-ANSWER")
    if step.get("retried"):
        f.append("RETRIED")
    if step.get("error"):
        f.append("ERROR")
    return " ".join(f)


def summarize(trace: dict, out_dir: str | None = None) -> str:
    spec = trace.get("spec", {})
    usage = trace.get("usage", {})
    lines = []
    lines.append(
        f"jev-browser-test  spec={trace.get('spec_id')}  status={trace.get('status')}  pass={trace.get('pass')}  "
        f"actions={trace.get('actions_executed')}  duration={trace.get('duration_ms', 0) / 1000:.1f}s  "
        f"jev={usage.get('model')}  requests={usage.get('jev_requests')}  "
        f"tokens={usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out"
    )
    if trace.get("outcome"):
        result = trace.get("result") or {}
        verdict = trace.get("verdict")
        head = f"  outcome: {trace['outcome']}" + (f"  verdict: {verdict}" if verdict else "")
        if result.get("reason"):
            r = result["reason"]
            typed = ", ".join(f"{k}={v}" for k, v in (("blocked_reason", r.get("blocked_reason")), ("stuck_reason", r.get("stuck_reason"))) if v)
            head += f"  ({r.get('status')}" + (f"; {typed}" if typed else "") + f"; suggested verdict: {r.get('suggested_verdict') or 'judge yourself'})"
        elif result.get("seen_at_step"):
            head += f"  seen at step {result['seen_at_step']}" + (" (confirmed)" if result.get("confirmed") else "")
        lines.append(head)
        if (result.get("evidence") or {}).get("line"):
            lines.append(f"  evidence: \"{result['evidence']['line']}\"")
        if result.get("note"):
            lines.append(f"  note: {result['note']}")
    if trace.get("status_meaning"):
        lines.append(f"  meaning: {trace['status_meaning']}")
    if trace.get("error"):
        lines.append(f"  error: {trace['error']}")
    if trace.get("passed_without_actions"):
        lines.append("  WARNING: passed on the start page before any action; the done_when checks may be too weak")
    lines.append(f"  goal: {spec.get('goal')}")
    if trace.get("setup"):
        ok = sum(1 for s in trace["setup"] if s.get("ok"))
        lines.append(f"  setup: {ok}/{len(trace['setup'])} scripted steps ok")
    final = trace.get("final") or {}
    lines.append(f"  start: {spec.get('start_url')}")
    lines.append(f"  end:   {final.get('url')}  \"{final.get('title')}\"")
    lines.append("")
    lines.append(f"{'#':>3}  {'operation':<20} {'target / value':<58} {'conf op/tgt/val':<16} checks  flags")
    for s in trace.get("steps", []):
        op = (s.get("operation") or {}).get("choice", "?")
        ex = s.get("executed") or {}
        if ex.get("action") in ("AUTO_DONE", "STOP", "DONE", "BLOCKED"):
            op = ex["action"] if ex["action"] != "STOP" else f"{op} (stopped)"
            if ex.get("confirmed"):
                op = f"{ex['action']} (confirmed)"
        elif ex.get("action") == "WAIT" and ex.get("reason"):
            if s.get("stale"):
                op = f"{op} (stale)"
            elif ex["reason"] == "confirming DONE":
                op = "DONE (checking)"
            elif ex["reason"].startswith("confirming outcome"):
                op = "outcome (checking)"
            else:
                op = f"{op} (not run)"
        target = ""
        tg = s.get("target")
        if tg and not tg.get("missing"):
            target = tg.get("label", tg.get("choice", ""))
        if s.get("type_value"):
            target += f" <- {s['type_value'].get('choice')}"
        if len(target) > 58:
            target = target[:55] + "..."
        lines.append(
            f"{s['n']:>3}  {op:<20} {target:<58} {_fmt_conf(s):<16} {_fmt_checks(s.get('checks', {}), spec)}  {_flags(s)}".rstrip()
        )
    lines.append("")
    lines.append("final checks: " + _fmt_checks(final.get("checks", {}), spec))
    assertions = (trace.get("result") or {}).get("assertions") or []
    if assertions:
        lines.append("assertions: " + "  ".join(
            f"{'✓' if a.get('ok') else '✗'} {next(k for k in a if k not in ('ok', 'actual'))}" for a in assertions))
    if out_dir:
        lines.append(f"result: {os.path.join(out_dir, 'result.json')}  trace: {os.path.join(out_dir, 'trace.json')}" + _screenshot_hint(trace))
    return "\n".join(lines)


def _screenshot_hint(trace: dict) -> str:
    steps = trace.get("steps", [])
    with_shot = [s["n"] for s in steps if s.get("screenshot")]
    failed = [s["n"] for s in steps if s.get("screenshot_after_failure")]
    final = (trace.get("final") or {}).get("screenshot")
    if not with_shot and not final:
        return ""
    if steps and len(with_shot) == len(steps):
        which = "every step"
    else:
        which = "steps " + ", ".join(str(n) for n in with_shot) if with_shot else "no step"
    hint = f"  screenshots: {which}"
    if failed:
        hint += f"; after failed action: {', '.join(f'{n:03d}-failed.png' for n in failed)}"
    if final:
        hint += " + final.png"
    return hint


def dump_step(trace: dict, n: int) -> str:
    for s in trace.get("steps", []):
        if s["n"] == n:
            s = dict(s)
            elements = s.pop("elements", [])
            body = json.dumps(s, indent=2, ensure_ascii=False)
            table = "\n".join(
                f"[{e['idx']}] {e['role']} \"{e.get('name', '')}\"" + (f" value=\"{e['value']}\"" if e.get("value") else "")
                for e in elements
            )
            return f"{body}\n\nelements offered at step {n}:\n{table}"
    return f"no step {n} in trace"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", help="a run's trace.json (or its result.json, or the run directory)")
    ap.add_argument("--step", type=int, help="dump one step in full")
    ap.add_argument("--result", action="store_true", help="print the run's result.json instead of the step table")
    args = ap.parse_args(argv[1:])
    path = args.trace
    if os.path.isdir(path):
        path = os.path.join(path, "trace.json")
    run_dir = os.path.dirname(path)
    if args.result or os.path.basename(path) == "result.json":
        with open(os.path.join(run_dir, "result.json"), encoding="utf-8") as f:
            print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        return 0
    with open(path, encoding="utf-8") as f:
        trace = json.load(f)
    if args.step:
        print(dump_step(trace, args.step))
    else:
        print(summarize(trace, run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
