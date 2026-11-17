"""Pick what a live run publishes to the live-results branch: python .github/live/publish.py <out dir> <publish dir>.

Every summary the plan wrote (results.md / results.json of a suite, ab.md / ab.json of an A/B, junit.xml), every
run's result.json, and for a run that was not green its trace.json and pictures too. A green run's trace stays in the
workflow's artifact: two hundred of them would be most of a hundred megabytes. SUMMARY.md opens with one line per
run and then repeats the suites' and A/Bs' own tables. A file the plan wants published whatever it is goes into
<out dir>/keep/.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

SUMMARIES = ("results.md", "results.json", "ab.md", "ab.json", "junit.xml")


def green(result: dict) -> bool:
    expected = result.get("expected")
    return bool(expected.get("matched")) if expected else result.get("status") == "passed"


def main(out: str, publish: str) -> int:
    os.makedirs(publish, exist_ok=True)
    lines, tables = [], []
    for root, dirs, files in os.walk(out):
        dirs.sort()
        rel = os.path.relpath(root, out)
        if rel == "keep" or rel.startswith("keep" + os.sep):
            dest = os.path.join(publish, rel)
            os.makedirs(dest, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(root, name), dest)
            continue
        wanted = [f for f in files if f in SUMMARIES]
        result = None
        if "result.json" in files:
            try:
                with open(os.path.join(root, "result.json"), encoding="utf-8") as f:
                    result = json.load(f)
            except (OSError, ValueError):
                result = None
            wanted.append("result.json")
            if result is None or not green(result):
                wanted += [f for f in ("trace.json",) if f in files]
                steps = os.path.join(root, "steps")
                if os.path.isdir(steps):
                    shutil.copytree(steps, os.path.join(publish, rel, "steps"), dirs_exist_ok=True)
        if not wanted:
            continue
        os.makedirs(os.path.join(publish, rel), exist_ok=True)
        for name in wanted:
            shutil.copy2(os.path.join(root, name), os.path.join(publish, rel, name))
        if result is not None:
            reason = result.get("reason") or {}
            usage = result.get("usage") or {}
            diag = (result.get("diagnostics") or {}).get("counts") or {}
            noted = ", ".join(f"{k} {v}" for k, v in diag.items() if v)
            lines.append(f"| {rel.replace(os.sep, '/')} | {'green' if green(result) else '**red**'} | {result.get('outcome')} | {result.get('status')} | "
                         f"{reason.get('suggested_verdict') or ''} | {usage.get('jev_requests')} | {usage.get('input_tokens')} | "
                         f"{(result.get('duration_ms') or 0) / 1000:.1f} | {(result.get('evidence') or {}).get('line') or ''} | {noted} |")
        for name in ("results.md", "ab.md"):
            if name in files:
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    tables.append(f"## {rel.replace(os.sep, '/')}/{name}\n\n{f.read()}")
    head = ["# Live run", "", f"{len(lines)} run(s), {sum(1 for ln in lines if '**red**' in ln)} not green.", "",
            "| run | | outcome | status | suggested | requests | input tokens | s | evidence | browser diagnostics |", "|---|---|---|---|---|---:|---:|---:|---|---|"]
    with open(os.path.join(publish, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(head + lines) + "\n\n" + "\n\n".join(tables) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
