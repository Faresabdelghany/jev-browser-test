"""Run several specs, each N times, on a pool of runner subprocesses, and write one verdict per spec.

    python scripts/run_suite.py specs/*.json [--repeat 3] [--workers 2] [--out runs/suite/<ts>]
                                [--run-arg=--screenshots=none ...] [--label name] [--junit runs/junit.xml]

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
import fnmatch
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from urllib.parse import urlsplit

from bench import _git_commit, _median, measure_trace
from spec import UNDETERMINED, load_dotenv, substitute_env, utf8_stdio

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_TEST = os.path.join(HERE, "run_test.py")
FLAKY = "flaky"
EXPECTED = "expected"  # a spec with `expect` whose every run ended in the declared result: green, like pass
GREEN = ("pass", EXPECTED)
MEDIAN_FIELDS = ("wall_ms", "duration_ms", "jev_ms", "browser_ms", "requests", "input_tokens", "decision_confidence", "steps", "replayed_steps",
                 "launch_ms", "navigation_ms", "login_ms", "setup_ms")
ENVIRONMENT_REASON = "every run failed before observing a page (browser, start URL or setup): see environment_failures"


DEFAULT_PER_HOST = 2  # runs at once against one host unless told otherwise: what a shared demo host takes without timing out


def spec_host(spec_path: str) -> tuple[str, int | None]:
    """The host a spec runs against (its start_url's, with ${ENV} filled in from the environment when it can be) and
    the spec's own `host_limit`, if it declares one. A spec that cannot be read is its own host: it fails by itself."""
    try:
        with open(spec_path, encoding="utf-8") as f:
            raw = json.load(f)
        url = substitute_env(str(raw.get("start_url") or ""), [])
        limit = raw.get("host_limit")
        return (urlsplit(url).netloc or url or spec_path), (limit if isinstance(limit, int) and not isinstance(limit, bool) and limit >= 1 else None)
    except (OSError, ValueError):
        return spec_path, None


def host_limits(spec_paths: list[str], per_host: int = DEFAULT_PER_HOST, overrides: list[tuple[str, int]] | None = None) -> tuple[dict, dict]:
    """({spec path: host}, {host: how many runs it takes at once}). A host's limit is the command line's
    `--host-limit PATTERN=N` when a pattern matches it (the first that does), else `--per-host`, lowered to the
    smallest `host_limit` a spec on that host declares: a spec can ask for less than the default, never for more
    (more is a statement about the host, and that is the command line's to make)."""
    hosts, declared = {}, {}
    for path in spec_paths:
        host, limit = spec_host(path)
        hosts[path] = host
        if limit is not None:
            declared[host] = min(limit, declared.get(host, limit))
    limits = {}
    for host in dict.fromkeys(hosts.values()):
        forced = next((n for pattern, n in overrides or [] if fnmatch.fnmatch(host, pattern)), None)
        limits[host] = forced if forced is not None else min(per_host, declared.get(host, per_host))
    return hosts, limits


def run_pool(jobs: list, workers: int, host_of, limits: dict, work) -> tuple[list, dict]:
    """Run `work(job)` for every job on `workers` threads with at most `limits[host_of(job)]` jobs of one host at a
    time. Returns (results in the jobs' order, {host: the most that ran at once}). A free worker takes, among the
    jobs whose host has room, one from the host with the most work left per slot (jobs waiting / its limit): the
    host that will finish last is the one that must never sit idle. Ties go to the earlier job."""
    results: list = [None] * len(jobs)
    pending = list(range(len(jobs)))
    running: dict = {}
    peaks: dict = {}
    cond = threading.Condition()

    def take() -> int | None:
        waiting: dict = {}
        for i in pending:
            waiting[host_of(jobs[i])] = waiting.get(host_of(jobs[i]), 0) + 1
        best, best_load = None, -1.0
        for i in pending:
            host = host_of(jobs[i])
            if running.get(host, 0) >= limits.get(host, 1):
                continue
            load = waiting[host] / limits.get(host, 1)
            if load > best_load:
                best, best_load = i, load
        return best

    def worker() -> None:
        while True:
            with cond:
                while True:
                    if not pending:
                        return
                    i = take()
                    if i is not None:
                        break
                    cond.wait()
                pending.remove(i)
                host = host_of(jobs[i])
                running[host] = running.get(host, 0) + 1
                peaks[host] = max(peaks.get(host, 0), running[host])
            try:
                results[i] = work(jobs[i])
            except Exception:  # noqa: BLE001 - one job's failure leaves its result None; the worker and the slot go on
                pass
            finally:
                with cond:
                    running[host] -= 1
                    cond.notify_all()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, min(workers, len(jobs))))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, peaks


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
        return os.path.relpath(path, base).replace(os.sep, "/")  # the same results.json on every system; "/" opens on Windows too
    except ValueError:  # another drive on Windows: no relative form exists
        return path


def run_once(runner: str, python: str, spec_path: str, out_dir: str, run_args: list[str], base: str | None = None) -> dict:
    """One runner subprocess. Returns the run record: exit code, wall-clock, the result.json headline fields
    and the trace-derived measures (bench.measure_trace). No trace.json at all -> an environment failure
    (`environment_failure: true`, status error, the stderr tail, no outcome); an unreadable trace or result
    -> an undetermined error run. `out_dir`, `trace` and `result` are written relative to `base` when given."""
    cmd = [python, runner, spec_path, "--out", out_dir, *run_args]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
        if result.get("replay"):
            rp = result["replay"]
            rec["replay"] = {k: rp.get(k) for k in ("used", "steps_in_path", "steps_replayed", "handed_back", "verified_by", "saved")}
    else:
        # the runner ran but wrote no readable result (a crash after the first observation): an error run
        rec["status"] = rec.get("status") or "error"
        rec["outcome"] = UNDETERMINED
        rec["error"] = rec.get("error") or tail
    return _relativize(rec, base)


def green_run(rec: dict) -> bool:
    return rec.get("exit_code") == 0


def run_with_replay(runner: str, python: str, spec_path: str, out_dir: str, run_args: list[str], base: str | None = None) -> dict:
    """One run with replay on, and the rule that keeps a saved path from ever being the reason for a red: a run that
    walked saved steps and did not end green is run again at once without the saved path (`--replay-record`: every
    step is Jev's, and a pass writes the path afresh). The second run is the run of record; the first is kept under
    `replay_attempt` (its outcome, verdict, status, wall-clock and result file), and `replay_disagreed` says whether
    the two ended differently."""
    rec = run_once(runner, python, spec_path, out_dir, run_args, base)
    walked = (rec.get("replay") or {}).get("steps_replayed") or 0
    if green_run(rec) or rec.get("environment_failure") or not walked:
        return rec
    again = run_once(runner, python, spec_path, out_dir + "-without-replay", [*run_args, "--replay-record"], base)
    again["replay_attempt"] = {k: rec.get(k) for k in ("outcome", "verdict", "status", "exit_code", "wall_ms", "result", "out_dir", "replay")}
    again["replay_disagreed"] = (rec.get("outcome"), rec.get("verdict")) != (again.get("outcome"), again.get("verdict"))
    again["wall_ms"] = (again.get("wall_ms") or 0) + (rec.get("wall_ms") or 0)  # what this spec cost the suite
    return again


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
        # with replay on: runs that walked their saved path to its end, runs where Jev took over before it, and runs
        # that ended red after saved steps and were run again without the path (run_with_replay)
        "replay": ({"full": sum(1 for r in observed if (r.get("replay") or {}).get("used") and not (r.get("replay") or {}).get("handed_back")
                                and not r.get("replay_attempt")),
                    "handed_back": sum(1 for r in observed if (r.get("replay") or {}).get("handed_back")),
                    "rerun_without": sum(1 for r in observed if r.get("replay_attempt")),
                    "disagreed": sum(1 for r in observed if r.get("replay_disagreed"))}
                   if any(r.get("replay") or r.get("replay_attempt") for r in observed) else None),
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
    out = {"all_pass": all_pass, "verdicts": verdicts, "flaky": flaky, "undetermined": undetermined,
           "environment_failures": environment}
    replays = {sid: s["replay"] for sid, s in specs.items() if s.get("replay")}
    if replays:
        out["replay"] = {k: sum(r[k] for r in replays.values()) for k in ("full", "handed_back", "rerun_without", "disagreed")}
        out["replay"]["disagreed_specs"] = sorted(sid for sid, r in replays.items() if r["disagreed"])
    return out


def _hosts_note(report: dict) -> str:
    """' over N hosts, at most K at once on any (host: 1)' when the suite ran more than one run at a time."""
    hosts = report.get("hosts") or {}
    if report.get("workers", 1) < 2 or not hosts:
        return ""
    top = max(h["limit"] for h in hosts.values())
    lower = [f"{host}: {h['limit']}" for host, h in hosts.items() if h["limit"] < top]
    return f" over {len(hosts)} host(s), at most {top} at once on any" + (f" ({', '.join(lower)})" if lower else "")


def render_markdown(report: dict) -> str:
    """results.md: one table for the suite, then the runs of every spec."""
    s = report["suite"]
    env_total = sum((s.get("environment_failures") or {}).values())
    lines = [f"# Suite {report.get('label') or ''} {report['timestamp']}".rstrip(),
             "",
             f"**{'ALL PASS' if s['all_pass'] else 'NOT ALL PASS'}** · {len(report['specs'])} spec(s) × {report['repeat']} repeat(s), "
             f"{report['workers']} worker(s){_hosts_note(report)}, {report['elapsed_ms'] / 1000:.1f} s wall-clock"
             + (f" · commit `{report['git_commit']}`" if report.get("git_commit") else "")
             + (f" · **{env_total} environment/setup failure(s)** (the browser, the start URL or a setup step failed before "
                f"the flow was observed; not counted as outcomes)" if env_total else ""),
             ""]
    rp = s.get("replay")
    if rp:
        lines += [f"Replay: {rp['full']} run(s) walked their saved path to its end, {rp['handed_back']} handed over to Jev on the way"
                  + (f", {rp['rerun_without']} ended red after saved steps and ran again without the path (that second run is the "
                     f"result{'; ' + str(rp['disagreed']) + ' ended differently: ' + ', '.join('`' + x + '`' for x in rp['disagreed_specs']) if rp['disagreed'] else ''})"
                     if rp["rerun_without"] else "") + ".", ""]
    lines += ["| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |",
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
            if r.get("replay_attempt"):
                outcome = f"{outcome} (without the saved path; with it: {r['replay_attempt'].get('outcome')})"
            elif (r.get("replay") or {}).get("used"):
                hb = r["replay"].get("handed_back")
                outcome = f"{outcome} (replayed {r['replay'].get('steps_replayed')}/{r['replay'].get('steps_in_path')}" + \
                    (f", Jev from step {hb.get('at_step')}" if hb else "") + ")"
            lines.append(f"| {i} | {outcome} | {r.get('verdict') or '-'} | {r.get('status')} | {r.get('wall_ms')} ms | "
                         f"{r.get('exit_code')} | {evidence} | `{r.get('result') or r.get('out_dir')}` |")
    if s["flaky"] or s["undetermined"]:
        lines += ["", "Open a trace only for: " + ", ".join(f"`{x}` (flaky)" for x in s["flaky"])
                  + (", " if s["flaky"] and s["undetermined"] else "") + ", ".join(f"`{x}` (undetermined)" for x in s["undetermined"])]
    return "\n".join(lines) + "\n"


def run_suite(spec_paths: list[str], repeat: int, workers: int, out_root: str, run_args: list[str],
              python: str = sys.executable, runner: str = RUN_TEST, label: str = "", replay: bool = False,
              per_host: int | None = None, host_overrides: list[tuple[str, int]] | None = None, quiet: bool = False) -> dict:
    """Run the pool, aggregate, write results.json + results.md, return the report. `per_host` (default: `workers`,
    so a caller that names only `workers` gets the pool it always got) and `host_overrides` bound how many runs one
    host sees at once (host_limits)."""
    os.makedirs(out_root, exist_ok=True)
    hosts, limits = host_limits(spec_paths, workers if per_host is None else per_host, host_overrides)
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
            rec = (run_with_replay if replay else run_once)(runner, python, spec_path, out_dir, run_args, base=out_root)
        except Exception as e:  # noqa: BLE001 - one run's failure to launch or to be read must not lose the suite
            rec = {"out_dir": _rel(out_dir, out_root), "exit_code": None, "wall_ms": int((time.perf_counter() - t0) * 1000),
                   "outcome": None, "verdict": None, "status": "error", "environment_failure": True,
                   "error": f"{type(e).__name__}: {str(e)[:300]}"}
        rec = {"run": i, **rec}
        shown = f"environment failure (exit {rec.get('exit_code')})" if rec.get("environment_failure") else \
            f"{rec.get('outcome')} ({rec.get('verdict') or rec.get('status')})"
        if not quiet:  # rerun.py prints its own few lines and nothing else
            print(f"{sid} {i}/{repeat}: {shown} {rec['wall_ms']} ms", flush=True)
        return sid, i, rec

    done, peaks = run_pool(jobs, workers, lambda job: hosts[job[0]], limits, work)
    for sid, i, rec in done:
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
        # how many runs each host was allowed at once, and the most it actually saw
        "hosts": {host: {"limit": limits[host], "peak": peaks.get(host, 0), "specs": sum(1 for h in hosts.values() if h == host)} for host in limits},
        "replay": replay,
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
    utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="spec files to run")
    ap.add_argument("--repeat", type=int, default=1, help="runs per spec (default 1; use 3-5 to measure agreement)")
    ap.add_argument("--workers", type=int, default=2,
                    help="runner subprocesses at once, over all hosts (default 2). Raising it is safe for the hosts: each "
                         "still sees at most --per-host runs at a time")
    ap.add_argument("--per-host", type=int, default=DEFAULT_PER_HOST,
                    help=f"runs at once against one host (default {DEFAULT_PER_HOST}: more than that against a shared host turns its "
                         "load timeouts into your flakiness). A spec's `host_limit` lowers it for its host; raise it for an "
                         "application you host yourself")
    ap.add_argument("--host-limit", action="append", default=[], metavar="HOST=N",
                    help="runs at once against the hosts matching a pattern, e.g. --host-limit 'staging.example.com=8' or "
                         "'*.example.com=4' (repeatable; beats --per-host and the specs' host_limit)")
    ap.add_argument("--out", help="output directory (default runs/suite/<timestamp>)")
    ap.add_argument("--label", default="", help="free-text label stored in results.json")
    ap.add_argument("--run-arg", action="append", default=[], help="extra argument passed through to run_test.py (repeatable)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--headed", action="store_true", help="every runner shows its browser window (use --workers 1); beats JEV_HEADED")
    mode.add_argument("--headless", action="store_true", help="every runner hides it; beats JEV_HEADED=1")
    ap.add_argument("--junit", metavar="FILE", help="also write the suite as a JUnit XML report (one test case per spec) for a CI dashboard")
    ap.add_argument("--replay", action="store_true",
                    help="every run walks the path its spec's last passing run saved (.jev/paths), asking Jev only where a step no "
                         "longer applies and about the ending, and saves its own when it passes. A run that ends red after saved "
                         "steps is run again without the path, and that run is the result")
    ap.add_argument("--sessions", action="store_true",
                    help="log in once per site and account: specs with a `login` block reuse the session the first of them saved "
                         "(run_test.py --reuse-sessions)")
    ap.add_argument("--http-cache", action="store_true", help="keep the browser's HTTP cache between runs (run_test.py --http-cache)")
    ap.add_argument("--replay-verify", choices=("jev", "assert"),
                    help="how a fully replayed run's ending is decided (run_test.py --replay-verify)")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--runner", default=RUN_TEST, help=argparse.SUPPRESS)  # the offline tests substitute a fake runner
    args = ap.parse_args(argv[1:])
    if args.repeat < 1 or args.workers < 1 or args.per_host < 1:
        print("--repeat, --workers and --per-host must be >= 1", file=sys.stderr)
        return 2
    overrides: list[tuple[str, int]] = []
    for item in args.host_limit:
        pattern, _, n = item.rpartition("=")
        if not pattern or not n.isdigit() or int(n) < 1:
            print(f"--host-limit takes HOST=N with N >= 1 (a host name or a pattern such as '*.example.com'), got '{item}'", file=sys.stderr)
            return 2
        overrides.append((pattern, int(n)))
    load_dotenv()  # a start_url written as ${BASE_URL} names its host only with the environment the runs will have
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
    run_args = [*args.run_arg, *(["--headed"] if args.headed else []), *(["--headless"] if args.headless else []),
                *(["--replay"] if args.replay else []), *(["--replay-verify", args.replay_verify] if args.replay_verify else []),
                *(["--reuse-sessions"] if args.sessions else []), *(["--http-cache"] if args.http_cache else [])]
    replay = args.replay or "--replay" in args.run_arg
    report = run_suite(specs, args.repeat, args.workers, out_root, run_args, args.python, args.runner, args.label, replay,
                       per_host=args.per_host, host_overrides=overrides)
    print()
    print(render_markdown(report))
    print(f"results: {os.path.join(out_root, 'results.json')}  {os.path.join(out_root, 'results.md')}")
    if args.junit:
        from junit import suite_cases, write_junit
        print(f"junit: {write_junit(args.junit, args.label or 'jev-browser-test', suite_cases(report))}")
    runs = [r for sp in report["specs"].values() for r in sp["runs"]]
    if runs and all(r.get("environment_failure") for r in runs):
        print("every run failed before observing a page (browser, start URL or setup; see the error column): the environment "
              "or the specs, not the flows, failed", file=sys.stderr)
        return 2
    return 0 if report["suite"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
