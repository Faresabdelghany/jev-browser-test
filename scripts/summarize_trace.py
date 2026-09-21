"""Print a compact summary of a run trace.

    python scripts/summarize_trace.py runs/<id>/<ts>/trace.json [--checks] [--step N]

Read this first when judging a run; open trace.json or the step screenshots only for the steps
the summary flags. `--step N` dumps one step in full (element table, probabilities, checks).
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
                op = "DONE (confirmed)"
        elif ex.get("action") == "WAIT" and ex.get("reason"):
            op = "DONE (checking)" if ex["reason"] == "confirming DONE" else f"{op} (not run)"
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
    if out_dir:
        lines.append(f"trace: {os.path.join(out_dir, 'trace.json')}" + ("  screenshots: steps/NNN.png, steps/final.png" if any(s.get("screenshot") for s in trace.get("steps", [])) else ""))
    return "\n".join(lines)


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
    ap.add_argument("trace")
    ap.add_argument("--step", type=int, help="dump one step in full")
    args = ap.parse_args(argv[1:])
    with open(args.trace, encoding="utf-8") as f:
        trace = json.load(f)
    if args.step:
        print(dump_step(trace, args.step))
    else:
        print(summarize(trace, os.path.dirname(args.trace)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
