"""Render one run as a single static report.html a human can open from a PR.

    python scripts/report.py runs/<id>/<ts> [more run dirs ...] [--out report.html]

The page holds the result (outcome, verdict, evidence line, assertions, story), then one row per step with
the operation and target answers and their top probabilities, the type_value, every check, the outcome
Choice, flags, what was executed and how the page settled, with the step's screenshot inline (base64) when
the policy captured one, the failed-action picture, and final.png. Each step's element table is a
collapsed <details>. No external resources: the file is self-contained.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import sys

from spec import UNDETERMINED
from summarize_trace import _flags

CSS = """
body{font:14px/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:24px;color:#222;background:#fff}
h1{font-size:20px;margin:0 0 4px} h2{font-size:16px;margin:24px 0 8px}
.head{display:flex;flex-wrap:wrap;gap:8px 24px;margin:8px 0 16px}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-weight:600;color:#fff;background:#666}
.pass{background:#2e7d32} .bug{background:#c62828} .test_issue{background:#ef6c00} .needs_human{background:#6a1b9a}
.undetermined{background:#546e7a} .flaky{background:#8d6e63}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:6px 8px;vertical-align:top;text-align:left}
th{background:#f4f4f4} tr.flagged td{background:#fff8e1} tr.terminal td{background:#e8f5e9}
td.num{text-align:right;white-space:nowrap} .probs{color:#666;font-size:12px}
.ok{color:#2e7d32} .bad{color:#c62828} .flag{display:inline-block;padding:0 6px;border-radius:8px;background:#eee;font-size:12px;margin:1px}
img.shot{max-width:640px;max-height:400px;border:1px solid #ccc;display:block;margin-top:4px}
details summary{cursor:pointer;color:#555} pre{background:#f7f7f7;padding:8px;overflow:auto;font-size:12px}
.story li{margin:2px 0} .evidence{font-style:italic}
"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _img(images: dict[str, bytes], rel: str | None, alt: str) -> str:
    if not rel or rel not in images:
        return ""
    data = base64.b64encode(images[rel]).decode()
    return f'<img class="shot" alt="{_e(alt)}" src="data:image/png;base64,{data}">'


def _probs(answer: dict | None) -> str:
    if not answer:
        return ""
    probs = answer.get("top_probabilities") or answer.get("probabilities") or {}
    inner = ", ".join(f"{_e(k)} {v:.2f}" for k, v in sorted(probs.items(), key=lambda kv: -kv[1])[:5])
    return f'<div class="probs">conf {answer.get("confidence", 0):.2f} · {inner}</div>'


def _checks(checks: dict, spec: dict) -> str:
    if not checks:
        return "-"
    th = spec.get("thresholds") or {}
    parts = []
    for name, p in checks.items():
        cls = ""
        if name in (spec.get("done_when") or []):
            cls = "ok" if p >= th.get("check_true", 0.8) else "bad"
        elif name in (spec.get("never") or []):
            cls = "bad" if p >= th.get("never_true", 0.8) else ""
        parts.append(f'<span class="{cls}">{_e(name)}={p:.2f}</span>')
    return "<br>".join(parts)


def _operation_cell(step: dict) -> str:
    ex = step.get("executed") or {}
    op = step.get("operation") or {}
    label = _e(op.get("choice") or "?")
    action = ex.get("action")
    if action in ("AUTO_DONE", "DONE", "BLOCKED", "STOP"):
        label = _e(action if action != "STOP" else f"{op.get('choice')} (stopped)")
        if ex.get("confirmed"):
            label += " (confirmed)"
    elif action == "WAIT" and ex.get("reason"):
        label += f' <span class="probs">({_e(ex["reason"])})</span>'
    return label + _probs(op if op else None)


def _target_cell(step: dict) -> str:
    tg = step.get("target")
    if not tg:
        return "-"
    if tg.get("missing"):
        return f'<span class="bad">no target answer: {_e(tg.get("invalid"))}</span>'
    out = _e(tg.get("label") or tg.get("choice")) + _probs(tg)
    tv = step.get("type_value")
    if tv:
        out += f'<div>&larr; {_e(tv.get("choice"))}</div>' + _probs(tv)
    return out


def _outcome_cell(step: dict) -> str:
    o = step.get("outcome")
    parts = []
    if o:
        parts.append(_e(o.get("choice")) + _probs(o))
    for key in ("blocked_reason", "stuck_reason"):
        if step.get(key):
            parts.append(f'<div class="probs">{key}: {_e(step[key].get("choice"))}</div>')
    return "".join(parts) or "-"


def _elements_table(step: dict) -> str:
    rows = []
    for el in step.get("elements") or []:
        extra = " ".join(f"{k}={_e(el[k])}" for k in ("value", "context", "text") if el.get(k))
        rows.append(f"[{el.get('idx')}] {_e(el.get('role'))} &quot;{_e(el.get('name'))}&quot; {extra}")
    if not rows:
        return ""
    return (f"<details><summary>{len(rows)} elements offered</summary><pre>" + "\n".join(rows) + "</pre></details>")


def render_report(trace: dict, result: dict | None, images: dict[str, bytes], run_dir: str = "") -> str:
    spec = trace.get("spec") or {}
    result = result or trace.get("result") or {}
    usage = trace.get("usage") or {}
    verdict = result.get("verdict") or (UNDETERMINED if result.get("outcome") == UNDETERMINED else trace.get("status"))
    parts = [f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{_e(trace.get('spec_id'))} · {_e(result.get('outcome') or trace.get('status'))}</title>",
             f"<style>{CSS}</style></head><body>",
             f"<h1>{_e(trace.get('spec_id'))} <span class=\"badge {_e(verdict)}\">{_e(result.get('outcome') or trace.get('status'))}"
             + (f" · {_e(verdict)}" if result.get("verdict") else "") + "</span></h1>",
             f"<div class=\"probs\">{_e(spec.get('goal'))}</div>",
             "<div class=\"head\">",
             f"<span>status <b>{_e(trace.get('status'))}</b></span>",
             f"<span>actions <b>{_e(trace.get('actions_executed'))}</b></span>",
             f"<span>duration <b>{(trace.get('duration_ms') or 0) / 1000:.1f} s</b></span>",
             f"<span>Jev <b>{_e(usage.get('model'))}</b> · {_e(usage.get('jev_requests'))} requests · {_e(usage.get('input_tokens'))} in / {_e(usage.get('output_tokens'))} out</span>",
             f"<span>start <code>{_e(spec.get('start_url'))}</code></span>",
             f"<span>end <code>{_e((trace.get('final') or {}).get('url'))}</code></span>",
             "</div>"]
    if result:
        parts.append("<h2>Result</h2><ul>")
        if result.get("note"):
            parts.append(f"<li>note: {_e(result['note'])}</li>")
        ev = result.get("evidence") or {}
        if ev.get("line"):
            parts.append(f'<li>evidence: <span class="evidence">&ldquo;{_e(ev["line"])}&rdquo;</span>'
                         + (f" (present {ev['present']:.2f})" if isinstance(ev.get("present"), (int, float)) else "") + "</li>")
        if result.get("seen_at_step"):
            parts.append(f"<li>seen at step {_e(result.get('first_seen_at_step') or result['seen_at_step'])}"
                         + (f", confirmed at step {result['seen_at_step']}" if result.get("confirmed") else "")
                         + f"; probability {_e(result.get('probability'))}, path confidence {_e(result.get('path_confidence'))}</li>")
        if result.get("reason"):
            r = result["reason"]
            parts.append(f"<li>reason: status <b>{_e(r.get('status'))}</b>"
                         + (f", blocked_reason {_e(r['blocked_reason'])}" if r.get("blocked_reason") else "")
                         + (f", stuck_reason {_e(r['stuck_reason'])}" if r.get("stuck_reason") else "")
                         + (f" &rarr; suggested <b>{_e(r['suggested_verdict'])}</b>" if r.get("suggested_verdict") else " &rarr; no suggestion: judge from the trace")
                         + (f"<br>error: <code>{_e(r['error'])}</code>" if r.get("error") else "") + "</li>")
        if result.get("assertions"):
            items = []
            for a in result["assertions"]:
                kind = next(k for k in a if k not in ("ok", "actual"))
                items.append(f'<li class="{"ok" if a.get("ok") else "bad"}">{"✓" if a.get("ok") else "✗"} {_e(kind)} {_e(json.dumps(a[kind]))}'
                             + ("" if a.get("ok") else f" &mdash; actual: <code>{_e(json.dumps(a.get('actual')))}</code>") + "</li>")
            parts.append("<li>assertions<ul>" + "".join(items) + "</ul></li>")
        if result.get("story"):
            parts.append('<li>story<ol class="story">' + "".join(f"<li>{_e(s)}</li>" for s in result["story"]) + "</ol></li>")
        parts.append("</ul>")
    parts.append("<h2>Steps</h2><table><tr><th>#</th><th>operation</th><th>target / value</th><th>checks</th><th>outcome</th>"
                 "<th>flags</th><th>executed · settle · ms</th><th>page</th></tr>")
    steps = trace.get("steps") or []
    for s in steps:
        flags = _flags(s)
        cls = "terminal" if s is steps[-1] else ("flagged" if flags else "")
        ex = s.get("executed") or {}
        exec_text = _e(ex.get("action"))
        if ex.get("ok") is False:
            exec_text += f' <span class="bad">failed: {_e(ex.get("error"))}</span>'
        settle = s.get("settle") or {}
        lat = s.get("latency_ms") or {}
        exec_text += f'<div class="probs">settle {_e(settle.get("ended", "-"))} · jev {_e(lat.get("jev"))} ms · browser {_e(lat.get("browser"))} ms'
        if s.get("page_changed") is not None:
            exec_text += f' · page_changed {str(s["page_changed"]).lower()}'
        exec_text += "</div>"
        page = (f'<div class="probs"><code>{_e(s.get("url"))}</code></div>' + _img(images, s.get("screenshot"), f"step {s['n']}")
                + _img(images, s.get("screenshot_after_failure"), f"step {s['n']} after the failed action") + _elements_table(s))
        parts.append(f'<tr class="{cls}"><td class="num">{s["n"]}</td><td>{_operation_cell(s)}</td><td>{_target_cell(s)}</td>'
                     f'<td>{_checks(s.get("checks") or {}, spec)}</td><td>{_outcome_cell(s)}</td>'
                     f'<td>{"".join(f"<span class=flag>{_e(f)}</span>" for f in flags.split()) or "-"}</td><td>{exec_text}</td><td>{page}</td></tr>')
    parts.append("</table>")
    final = trace.get("final") or {}
    if final:
        parts.append("<h2>Final page</h2>" + f'<div class="probs"><code>{_e(final.get("url"))}</code> · {_e(final.get("title"))}</div>'
                     + _img(images, final.get("screenshot"), "final page"))
    if run_dir:
        parts.append(f'<p class="probs">trace: <code>{_e(os.path.join(run_dir, "trace.json"))}</code> · result: <code>{_e(os.path.join(run_dir, "result.json"))}</code></p>')
    parts.append("</body></html>")
    return "\n".join(parts)


def build(run_dir: str, out_path: str | None = None) -> str:
    """Read a run directory and write its report.html (default: inside the run directory). Returns the path."""
    with open(os.path.join(run_dir, "trace.json"), encoding="utf-8") as f:
        trace = json.load(f)
    result = None
    result_path = os.path.join(run_dir, "result.json")
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
    images: dict[str, bytes] = {}
    for step in [*(trace.get("steps") or []), trace.get("final") or {}]:
        for key in ("screenshot", "screenshot_after_failure"):
            rel = step.get(key)
            if rel and rel not in images:
                try:
                    with open(os.path.join(run_dir, rel), "rb") as img:
                        images[rel] = img.read()
                except OSError:
                    pass
    out_path = out_path or os.path.join(run_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render_report(trace, result, images, run_dir))
    return out_path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dirs", nargs="+", help="run directories (each holding trace.json)")
    ap.add_argument("--out", help="output file (only with a single run directory; default <run dir>/report.html)")
    args = ap.parse_args(argv[1:])
    if args.out and len(args.run_dirs) != 1:
        print("--out needs exactly one run directory", file=sys.stderr)
        return 2
    code = 0
    for run_dir in args.run_dirs:
        if not os.path.exists(os.path.join(run_dir, "trace.json")):
            print(f"no trace.json in {run_dir}", file=sys.stderr)
            code = 2
            continue
        print(build(run_dir, args.out))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
