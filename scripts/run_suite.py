"""Run several specs, each N times, on a pool of runner subprocesses, and write one verdict per spec.

    python scripts/run_suite.py specs/*.json [--repeat 3] [--workers 4] [--out runs/suite/<ts>]
                                [--run-arg=--screenshots=none ...] [--label name]

Every (spec, repeat) is its own `run_test.py` subprocess with its own browser and Jev connection, so the
runs are independent and the pool only bounds how many browsers are open at once. The suite writes
`results.json` and `results.md` into the output directory:

  * per spec: every run's outcome / verdict / status / exit code / wall-clock and result path, the outcome
    distribution across the repeats, the agreement rate (share of runs that ended in the most common
    outcome), medians (wall, Jev ms, browser ms, requests, input tokens, decision confidence), and a
    **suite verdict**: unanimous -> that outcome's verdict (or `undetermined` when every run was
    undetermined); any disagreement -> `flaky`, with the distribution. Flaky is computed, not diagnosed.
  * for the suite (`suite.all_pass`, `suite.verdicts`, `suite.flaky`, ...): all_pass iff every spec is `pass` or `expected`; and the elapsed time.

A run that wrote no `trace.json` at all is an **environment failure**, not an outcome: the runner exited 2
(a spec or environment problem: missing key, unreachable browser), could not be launched, or was killed
before it observed anything. It is recorded (`status: "error"`, `environment_failure: true`, the stderr
tail in `error`), listed per spec under `environment_failures`, and left out of the outcome distribution,
the agreement rate and the medians, so one launch failure among passes does not read `flaky`. A spec whose
every run failed that way ends `undetermined` with `reason` saying so. A run whose trace or result is
unreadable (the runner was killed mid-write) is different: it ran, so it is an `undetermined` error run in
the distribution.

Every path in `results.json` / `results.md` (`spec`, each run's `out_dir`, `trace`, `result`) is relative
to the output directory, so the files stay readable after the directory moves; `report.py <suite dir>`
resolves them against the `results.json` it reads. The top-level `out_dir` is the directory as it was given.

Exit code 0 iff every spec is unanimously `pass`; 1 otherwise; 2 when the suite itself could not run (a
spec file missing, two spec files with the same id, or every run of every spec was an environment failure:
the environment, not the flows, failed).

This is the hands-off entry point for Claude: launch it in the background, do nothing until it returns,
read results.json, and open a trace only for a spec that is `undetermined` or `flaky`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from bench import _git_commit, _median, measure_trace
from spec import UNDETERMINED

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_TEST = os.path.join(HERE, "run_test.py")
FLAKY = "flaky"
EXPECTED = "expected"  # a spec with `expect` whose every run ended in the declared result: green, like pass
GREEN = ("pass", EXPECTED)
MEDIAN_FIELDS = ("wall_ms", "duration_ms", "jev_ms", "browser_ms", "requests", "input_tokens", "decision_confidence", "steps")
ENVIRONMENT_REASON = "every run failed before observing a page (browser, start URL or setup): see environment_failures"


def spec_id_of(spec_path: str) -> str:
    try:
        with open(spec_path, encoding="utf-8") as f:
            return json.load(f).get("id") or os.path.splitext(os.path.basename(spec_path))[0]
    except (OSError, ValueError):
        return os.path.splitext(os.path.basename(spec_path))[0]


def _rel(path: str | None, base: str | None) -> str | None:
    """`path` relative to `base` (the directory that holds results.json); unchanged without a base or a common root."""
    if not path or not base:
        return path
    try:
        return os.path.relpath(path, base)
    except ValueError:  # another drive on Windows: no relative form exists
        return path


def run_once(runner: str, python: str, spec_path: str, out_dir: str, run_args: list[str], base: str | None = None) -> dict:
    """One runner subprocess. Returns the run record: exit code, wall-clock, the result.json headline fields
    and the trace-derived measures (bench.measure_trace). No trace.json at all -> an environment failure
    (`environment_failure: true`, status error, the stderr tail, no outcome); an unreadable trace or result
    -> an undetermined error run. `out_dir`, `trace` and `result` are written relative to `base` when given."""
    cmd = [python, runner, spec_path, "--out", out_dir, *run_args]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    rec: dict = {"out_dir": out_dir, "exit_code": proc.returncode, "wall_ms": int((time.perf_counter() - t0) * 1000),
                 "outcome": None, "verdict": None, "status": None}
    tail = (proc.stderr or proc.stdout or "").strip()[-500:]
    result_path = os.path.join(out_dir, "result.json")
    trace_path = os.path.join(out_dir, "trace.json")
    if not os.path.exists(trace_path):
        # nothing was observed: exit 2 (spec / environment problem), or the runner died before its first step
        rec.update({"status": "error", "environment_failure": True, "error": tail})
        return _relativize(rec, base)
    rec["trace"] = trace_path
    result = None
    try:
        with open(trace_path, encoding="utf-8") as f:
            rec.update(measure_trace(json.load(f)))
        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
    except (OSError, ValueError) as e:  # a runner killed mid-write leaves a truncated file: this run, not the suite, is lost
        rec["error"] = f"unreadable trace/result: {type(e).__name__}: {str(e)[:200]}"
        result = None
    if result is not None:
        rec["result"] = result_path
        rec["outcome"] = result.get("outcome")
        rec["verdict"] = result.get("verdict")
        rec["status"] = result.get("status")
        rec["suggested_verdict"] = (result.get("reason") or {}).get("suggested_verdict")
        rec["evidence_line"] = (result.get("evidence") or {}).get("line")
        rec["first_seen_at_step"] = result.get("first_seen_at_step")
        phase = (result.get("reason") or {}).get("phase")
        if phase:
            # the start page never loaded or a setup step failed (exit 2): nothing about the flow was observed, so
            # the run is an environment/setup failure, not an outcome in the distribution
            rec.update({"environment_failure": True, "phase": phase,
                        "error": f"{phase} failed: {(result.get('reason') or {}).get('error') or tail}"})
        if result.get("expected") is not None:
            rec["expected"] = result["expected"].get("matched")
            rec["expected_mismatches"] = result["expected"].get("mismatches")
    else:
        # the runner ran but wrote no readable result (a crash after the first observation): an error run
        rec["status"] = rec.get("status") or "error"
        rec["outcome"] = UNDETERMINED
        rec["error"] = rec.get("error") or tail
    return _relativize(rec, base)


def _relativize(rec: dict, base: str | None) -> dict:
    for key in ("out_dir", "trace", "result"):
        if rec.get(key):
            rec[key] = _rel(rec[key], base)
    return rec


def aggregate_spec(runs: list[dict]) -> dict:
    """Pure: the outcome distribution, agreement and suite verdict of one spec's repeats.

    Environment failures (`environment_failure: true`: no trace was written) are listed under
    `environment_failures` and left out of everything else: they say nothing about the flow, so on their own
    they cannot make a spec `flaky`. A spec with nothing but environment failures ends `undetermined` with
    `reason` set; otherwise `reason` is null."""
    failures = [r for r in runs if r.get("environment_failure")]
    observed = [r for r in runs if not r.get("environment_failure")]
    outcome_counts: dict = {}
    verdict_counts: dict = {}
    for r in observed:
        o = str(r.get("outcome") or UNDETERMINED)
        outcome_counts[o] = outcome_counts.get(o, 0) + 1
        v = str(r.get("verdict") or (UNDETERMINED if o == UNDETERMINED else "?"))
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    expected_runs = [r for r in observed if "expected" in r]
    # Agreement is on verdicts: two legitimate pass endings (or two bug endings) agree; an undetermined run does
    # not agree with a declared outcome. The outcome distribution is still reported (`outcome_agreement`).
    top_outcome = max(outcome_counts.values()) if outcome_counts else 0
    top_verdict = max(verdict_counts.values()) if verdict_counts else 0
    outcome_agreement = round(top_outcome / len(observed), 3) if observed else 0.0
    agreement = round(top_verdict / len(observed), 3) if observed else 0.0
    if not observed:
        verdict = UNDETERMINED
    elif expected_runs and len(expected_runs) == len(observed):
        # a spec with `expect`: green when every run ended in the declared result, otherwise its runs are judged like
        # any other's (a different outcome each time is flaky, the same unexpected outcome is that outcome's verdict)
        matched = sum(1 for r in expected_runs if r.get("expected"))
        agreement = round(max(matched, len(observed) - matched) / len(observed), 3)
        if matched == len(observed):
            verdict = EXPECTED
        elif matched:
            verdict = FLAKY
        else:
            verdict = FLAKY if len(verdict_counts) > 1 else next(iter(verdict_counts))
    elif len(verdict_counts) == 1:
        verdict = next(iter(verdict_counts))
    else:
        verdict = FLAKY
    suggestions: dict = {}
    for r in observed:
        if r.get("outcome") == UNDETERMINED:
            s = str(r.get("suggested_verdict") or "none")
            suggestions[s] = suggestions.get(s, 0) + 1
    return {
        "verdict": verdict,
        "agreement": agreement,
        "outcome_agreement": outcome_agreement,
        "expected_matched": sum(1 for r in expected_runs if r.get("expected")) if expected_runs else None,
        "outcome_counts": outcome_counts,
        "verdict_counts": verdict_counts,
        "suggested_verdicts": suggestions,
        "medians": {k: _median([r.get(k) for r in observed]) for k in MEDIAN_FIELDS},
        "passes": sum(1 for r in observed if r.get("verdict") == "pass"),
        "environment_failures": [{"run": r.get("run"), "exit_code": r.get("exit_code"), "error": r.get("error")} for r in failures],
        "reason": ENVIRONMENT_REASON if runs and not observed else None,
    }


def suite_verdict(specs: dict) -> dict:
    """Pure: the whole suite. all_pass iff every spec's verdict is pass or expected; environment failures counted per spec."""
    verdicts = {sid: s["verdict"] for sid, s in specs.items()}
    all_pass = bool(specs) and all(v in GREEN for v in verdicts.values())
    flaky = sorted(sid for sid, v in verdicts.items() if v == FLAKY)
    undetermined = sorted(sid for sid, v in verdicts.items() if v == UNDETERMINED)
    environment = {sid: len(s["environment_failures"]) for sid, s in specs.items() if s.get("environment_failures")}
    return {"all_pass": all_pass, "verdicts": verdicts, "flaky": flaky, "undetermined": undetermined,
            "environment_failures": environment}


def render_markdown(report: dict) -> str:
    """results.md: one table for the suite, then the runs of every spec."""
    s = report["suite"]
    env_total = sum((s.get("environment_failures") or {}).values())
    lines = [f"# Suite {report.get('label') or ''} {report['timestamp']}".rstrip(),
             "",
             f"**{'ALL PASS' if s['all_pass'] else 'NOT ALL PASS'}** · {len(report['specs'])} spec(s) × {report['repeat']} repeat(s), "
             f"{report['workers']} worker(s), {report['elapsed_ms'] / 1000:.1f} s wall-clock"
             + (f" · commit `{report['git_commit']}`" if report.get("git_commit") else "")
             + (f" · **{env_total} environment/setup failure(s)** (the browser, the start URL or a setup step failed before "
                f"the flow was observed; not counted as outcomes)" if env_total else ""),
             "",
             "| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |",
             "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for sid, sp in report["specs"].items():
        m = sp["medians"]
        failures = sp.get("environment_failures") or []
        observed = len(sp["runs"]) - len(failures)
        outcomes = ", ".join(f"{k} {v}/{observed}" for k, v in sorted(sp["outcome_counts"].items(), key=lambda kv: -kv[1]))
        verdict = sp["verdict"].upper()
        if sp["verdict"] == UNDETERMINED and sp["suggested_verdicts"]:
            verdict += " (suggested: " + ", ".join(f"{k} {v}" for k, v in sp["suggested_verdicts"].items()) + ")"
        if sp.get("expected_matched") is not None:
            verdict += f" (declared result in {sp['expected_matched']}/{observed})"
        if failures:
            verdict += f" (environment/setup failures {len(failures)}/{len(sp['runs'])})"
        lines.append(f"| `{sid}` | **{verdict}** | {sp['agreement']:.0%} | {outcomes or '-'} | {m['wall_ms']} ms | {m['jev_ms']} | "
                     f"{m['requests']} | {m['input_tokens']} | {m['decision_confidence']} |")
    for sid, sp in report["specs"].items():
        lines += ["", f"## `{sid}`", "", "| # | outcome | verdict | status | wall | exit | evidence | result |", "|---:|---|---|---|---:|---:|---|---|"]
        for i, r in enumerate(sp["runs"], 1):
            evidence = " ".join((r.get("evidence_line") or r.get("error") or "").split()).replace("|", "\\|")[:120]
            outcome = f"{r.get('phase') or 'environment'} failure" if r.get("environment_failure") else r.get("outcome")
            if r.get("expected") is not None:
                outcome = f"{outcome} ({'expected' if r['expected'] else 'NOT the expected result'})"
            lines.append(f"| {i} | {outcome} | {r.get('verdict') or '-'} | {r.get('status')} | {r.get('wall_ms')} ms | "
                         f"{r.get('exit_code')} | {evidence} | `{r.get('result') or r.get('out_dir')}` |")
    if s["flaky"] or s["undetermined"]:
        lines += ["", "Open a trace only for: " + ", ".join(f"`{x}` (flaky)" for x in s["flaky"])
                  + (", " if s["flaky"] and s["undetermined"] else "") + ", ".join(f"`{x}` (undetermined)" for x in s["undetermined"])]
    return "\n".join(lines) + "\n"


def run_suite(spec_paths: list[str], repeat: int, workers: int, out_root: str, run_args: list[str],
              python: str = sys.executable, runner: str = RUN_TEST, label: str = "") -> dict:
    """Run the pool, aggregate, write results.json + results.md, return the report."""
    os.makedirs(out_root, exist_ok=True)
    jobs = []
    for spec_path in spec_paths:
        sid = spec_id_of(spec_path)
        for i in range(1, repeat + 1):
            jobs.append((spec_path, sid, i, os.path.join(out_root, sid, f"{i:02d}")))
    t0 = time.perf_counter()
    records: dict[str, list] = {sid: [None] * repeat for _, sid, _, _ in jobs}

    def work(job):
        spec_path, sid, i, out_dir = job
        t0 = time.perf_counter()
        try:
            rec = run_once(runner, python, spec_path, out_dir, run_args, base=out_root)
        except Exception as e:  # noqa: BLE001 - one run's failure to launch or to be read must not lose the suite
            rec = {"out_dir": _rel(out_dir, out_root), "exit_code": None, "wall_ms": int((time.perf_counter() - t0) * 1000),
                   "outcome": None, "verdict": None, "status": "error", "environment_failure": True,
                   "error": f"{type(e).__name__}: {str(e)[:300]}"}
        rec = {"run": i, **rec}
        shown = f"environment failure (exit {rec.get('exit_code')})" if rec.get("environment_failure") else \
            f"{rec.get('outcome')} ({rec.get('verdict') or rec.get('status')})"
        print(f"{sid} {i}/{repeat}: {shown} {rec['wall_ms']} ms", flush=True)
        return sid, i, rec

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for sid, i, rec in pool.map(work, jobs):
            records[sid][i - 1] = rec
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    specs = {}
    for spec_path in spec_paths:
        sid = spec_id_of(spec_path)
        runs = [r for r in records[sid] if r is not None]
        specs[sid] = {"spec": _rel(spec_path, out_root), "runs": runs, **aggregate_spec(runs)}
    report = {
        "label": label,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "repeat": repeat,
        "workers": workers,
        "run_args": run_args,
        "elapsed_ms": elapsed_ms,
        "out_dir": out_root,
        "specs": specs,
        "suite": suite_verdict(specs),
    }
    with open(os.path.join(out_root, "results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_root, "results.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="spec files to run")
    ap.add_argument("--repeat", type=int, default=1, help="runs per spec (default 1; use 3-5 to measure agreement)")
    ap.add_argument("--workers", type=int, default=4, help="runner subprocesses at once (default 4)")
    ap.add_argument("--out", help="output directory (default runs/suite/<timestamp>)")
    ap.add_argument("--label", default="", help="free-text label stored in results.json")
    ap.add_argument("--run-arg", action="append", default=[], help="extra argument passed through to run_test.py (repeatable)")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--runner", default=RUN_TEST, help=argparse.SUPPRESS)  # the offline tests substitute a fake runner
    args = ap.parse_args(argv[1:])
    if args.repeat < 1 or args.workers < 1:
        print("--repeat and --workers must be >= 1", file=sys.stderr)
        return 2
    missing = [p for p in args.specs if not os.path.exists(p)]
    if missing:
        print("spec file(s) not found: " + ", ".join(missing), file=sys.stderr)
        return 2
    ids: dict[str, str] = {}
    for p in args.specs:
        sid = spec_id_of(p)
        if sid in ids and os.path.abspath(ids[sid]) != os.path.abspath(p):
            print(f"two spec files share the id '{sid}': {ids[sid]} and {p} (they would write the same run directories)",
                  file=sys.stderr)
            return 2
        ids.setdefault(sid, p)
    specs = list(dict.fromkeys(os.path.abspath(p) for p in args.specs))  # the same file twice runs once
    out_root = args.out or os.path.join("runs", "suite", datetime.now().strftime("%Y%m%d-%H%M%S"))
    report = run_suite(specs, args.repeat, args.workers, out_root, args.run_arg, args.python, args.runner, args.label)
    print()
    print(render_markdown(report))
    print(f"results: {os.path.join(out_root, 'results.json')}  {os.path.join(out_root, 'results.md')}")
    runs = [r for sp in report["specs"].values() for r in sp["runs"]]
    if runs and all(r.get("environment_failure") for r in runs):
        print("every run failed before observing a page (browser, start URL or setup; see the error column): the environment "
              "or the specs, not the flows, failed", file=sys.stderr)
        return 2
    return 0 if report["suite"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
