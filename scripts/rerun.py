"""Run a suite again and say, in a few lines, what is not green and what changed. The one command for a rerun.

    python scripts/rerun.py specs/                       # every spec in a folder
    python scripts/rerun.py specs/a.json specs/b.json    # these specs
    python scripts/rerun.py runs/suite/20261117-101500   # the specs of an earlier suite

Each spec runs once, with what makes a rerun cheap turned on: its saved path (`--replay`: the steps of its last
passing run without asking Jev, one request for the ending), a saved login for specs that share one (`login`
blocks), and as many runs at once as `--workers` allows while no host sees more than its limit (`--per-host`,
`--host-limit`, a spec's `host_limit`). A run that ends red after saved steps is run again without the path, so a
red here is always a run in which Jev chose every step. The suite's `results.json` and `results.md` are written as
by `run_suite.py`, and `summary.md` beside them holds what this command prints:

    GREEN: 22 of 22 specs in 48 s (4 workers, 24 Jev requests). Nothing to read.

or, when something is not green, one line per such spec with its verdict, its outcome, the page's own line and the
run folder to open, and after them what changed since the last rerun of the same specs:

    NOT GREEN: 20 of 22 specs green in 51 s (4 workers, 61 Jev requests)
      notify-random  BUG  action_unsuccessful  "Action unsuccesful, please try again"  -> runs/suite/<ts>/notify-random/01
      ...
    Changed since the last rerun (2026-11-17 15:02): notify-random pass -> bug
    Read result.json in those folders, then the trace if it does not settle it. The 20 green specs need no reading.

Exit 0 when every spec is green (`pass`, or the result a spec's `expect` declares), 1 otherwise, 2 when the suite
could not run. That is the whole interface for whoever runs it: the exit code, these lines, and for a spec that is
not green its run folder. Nothing else needs opening.

What each spec ended in is remembered in `.jev/reruns/` (local state, ignored by git) so the next rerun can say what
changed; `--no-replay`, `--no-sessions` and `--repeat` are there for the day the cheap way is not wanted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

from replay import private_dir
from run_suite import DEFAULT_PER_HOST, GREEN, RUN_TEST, run_suite, spec_id_of
from spec import load_dotenv, utf8_stdio

DEFAULT_WORKERS = 4
STATE_DIR = os.path.join(".jev", "reruns")


def is_spec_file(path: str) -> bool:
    """A JSON file that reads as a spec (an object with a start_url and a goal): a folder of specs may hold other JSON."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return False
    return isinstance(raw, dict) and isinstance(raw.get("start_url"), str) and isinstance(raw.get("goal"), str)


def collect_specs(args: list[str]) -> tuple[list[str], list[str]]:
    """(spec files, problems) for what was named on the command line: spec files, folders of them (the folder's own
    *.json, not its subfolders'), or an earlier suite (its folder or its results.json: the specs it ran)."""
    specs: list[str] = []
    problems: list[str] = []
    for arg in args:
        results = arg if os.path.basename(arg) == "results.json" else os.path.join(arg, "results.json")
        if os.path.isfile(results):
            base = os.path.dirname(os.path.abspath(results))
            try:
                with open(results, encoding="utf-8") as f:
                    listed = [sp.get("spec") for sp in json.load(f).get("specs", {}).values()]
            except (OSError, ValueError) as e:
                problems.append(f"{results}: could not be read ({type(e).__name__})")
                continue
            for rel in listed:
                path = os.path.normpath(os.path.join(base, rel)) if rel else None
                if path and os.path.isfile(path):
                    specs.append(path)
                else:
                    problems.append(f"{results}: the spec it ran is no longer there: {rel}")
        elif os.path.isdir(arg):
            found = sorted(os.path.join(arg, n) for n in os.listdir(arg) if n.endswith(".json") and is_spec_file(os.path.join(arg, n)))
            if not found:
                problems.append(f"{arg}: no spec files in this folder")
            specs.extend(found)
        elif os.path.isfile(arg):
            specs.append(arg)
        else:
            problems.append(f"{arg}: no such file or folder")
    return list(dict.fromkeys(os.path.abspath(p) for p in specs)), problems


def state_file(specs: list[str], directory: str = STATE_DIR) -> str:
    """Where the last rerun of this set of specs is remembered: one file per set, named by the set."""
    key = hashlib.sha256("\n".join(sorted(specs)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(directory, f"{key}.json")


def changes(previous: dict | None, verdicts: dict) -> list[str]:
    """What ended differently from the last rerun of the same specs: 'spec: was -> now', new specs, specs that are gone."""
    if not previous:
        return []
    was = previous.get("verdicts") or {}
    out = [f"{sid} {was[sid]} -> {now}" for sid, now in verdicts.items() if sid in was and was[sid] != now]
    out += [f"{sid} is new ({now})" for sid, now in verdicts.items() if sid not in was]
    out += [f"{sid} is no longer in the suite" for sid in was if sid not in verdicts]
    return out


def _line(text: str | None, cut: int = 90) -> str:
    text = " ".join((text or "").split())
    return (text[:cut - 1] + "…") if len(text) > cut else text


def summarize(report: dict, previous: dict | None = None) -> str:
    """The few lines a rerun is read by (see the module's docstring)."""
    specs = report["specs"]
    verdicts = report["suite"]["verdicts"]
    green = [sid for sid, v in verdicts.items() if v in GREEN]
    red = [sid for sid in specs if sid not in green]
    requests = sum(r.get("requests") or 0 for sp in specs.values() for r in sp["runs"])
    took = f"{report['elapsed_ms'] / 1000:.0f} s ({report['workers']} worker{'s' if report['workers'] != 1 else ''}, {requests} Jev requests)"
    out_dir = report["out_dir"]
    lines = []
    if not red:
        lines.append(f"GREEN: {len(green)} of {len(specs)} specs in {took}. Nothing to read.")
    else:
        lines.append(f"NOT GREEN: {len(green)} of {len(specs)} specs green in {took}")
        width = max(len(sid) for sid in red)
        for sid in red:
            sp = specs[sid]
            run = next((r for r in sp["runs"] if not r.get("environment_failure")), sp["runs"][0] if sp["runs"] else {})
            if sp["verdict"] == "flaky":
                what = "runs disagreed: " + ", ".join(f"{k} x{v}" for k, v in sp["outcome_counts"].items())
            elif run.get("environment_failure") or not sp["outcome_counts"]:
                what = "never observed a page (environment or setup): " + _line(run.get("error"), 70)
            else:
                what = str(run.get("outcome"))
                if run.get("outcome") == "undetermined":
                    what += f" ({run.get('status')}" + (f", suggested: {run['suggested_verdict']}" if run.get("suggested_verdict") else "") + ")"
                if run.get("evidence_line"):
                    what += f'  "{_line(run["evidence_line"], 70)}"'
                if run.get("replay_attempt"):
                    what += "  (the same without the saved path)" if not run.get("replay_disagreed") else \
                        f"  (with the saved path it ended {run['replay_attempt'].get('outcome')})"
            where = os.path.join(out_dir, run.get("out_dir") or sid).replace(os.sep, "/")
            lines.append(f"  {sid:<{width}}  {sp['verdict'].upper():<12} {what}  -> {where}")
    changed = changes(previous, verdicts)
    if previous:
        when = (previous.get("timestamp") or "")[:16].replace("T", " ")
        lines.append(f"Changed since the last rerun ({when}): " + "; ".join(changed) if changed
                     else f"Same verdicts as the last rerun ({when}).")
    rp = report["suite"].get("replay")
    if rp:
        handed = [f"{sid} at step {(r['replay'].get('handed_back') or {}).get('at_step')}: {_line((r['replay'].get('handed_back') or {}).get('reason'), 100)}"
                  for sid, sp in specs.items() for r in sp["runs"] if (r.get("replay") or {}).get("handed_back")]
        fresh = sum(1 for sp in specs.values() for r in sp["runs"] if r.get("replay") and not r["replay"].get("used") and not r.get("replay_attempt"))
        lines.append(f"Replay: {rp['full']} walked their saved path, {rp['handed_back']} handed over to Jev on the way, {fresh} had no path "
                     f"to walk (first run, edited spec, or a spec that does not end in a pass)"
                     + (f", {rp['rerun_without']} red after saved steps and run again without" if rp["rerun_without"] else "") + ".")
        lines += [f"  handed over: {h}" for h in handed[:5]]
    if red:
        lines.append(f"Read result.json in {'that folder' if len(red) == 1 else 'those folders'}, then the trace if it does not settle it. "
                     + (f"The {len(green)} green spec{'s' if len(green) != 1 else ''} need{'s' if len(green) == 1 else ''} no reading." if green else ""))
    lines.append(f"Report: {os.path.join(out_dir, 'results.md').replace(os.sep, '/')}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="*", help="spec files, folders of specs, or an earlier suite's folder (default: specs/)")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                    help=f"runs at once over all hosts (default {DEFAULT_WORKERS}; each host still sees at most --per-host)")
    ap.add_argument("--per-host", type=int, default=DEFAULT_PER_HOST,
                    help=f"runs at once against one host (default {DEFAULT_PER_HOST}; a spec's host_limit lowers it; raise it for an application you host)")
    ap.add_argument("--host-limit", action="append", default=[], metavar="HOST=N", help="runs at once against the hosts matching a pattern (repeatable)")
    ap.add_argument("--repeat", type=int, default=1, help="runs per spec (default 1; 3 to 5 to measure stability, as with run_suite.py)")
    ap.add_argument("--no-replay", action="store_true", help="every step is Jev's: no saved path is walked or written")
    ap.add_argument("--replay-verify", choices=("jev", "assert"), help="how a replayed run's ending is decided (run_test.py --replay-verify)")
    ap.add_argument("--no-sessions", action="store_true", help="every spec logs in by itself")
    ap.add_argument("--http-cache", action="store_true", help="keep the browser's HTTP cache between runs (run_test.py --http-cache)")
    ap.add_argument("--run-arg", action="append", default=[], help="extra argument passed through to run_test.py (repeatable)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--headed", action="store_true", help="show the browser windows (use --workers 1)")
    mode.add_argument("--headless", action="store_true", help="hide them; beats JEV_HEADED=1")
    ap.add_argument("--out", help="output directory (default runs/suite/<timestamp>)")
    ap.add_argument("--label", default="rerun", help="free-text label stored in results.json")
    ap.add_argument("--junit", metavar="FILE", help="also write the suite as a JUnit XML report")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--runner", default=RUN_TEST, help=argparse.SUPPRESS)  # the offline tests substitute a fake runner
    ap.add_argument("--state-dir", default=STATE_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args(argv[1:])
    if min(args.workers, args.per_host, args.repeat) < 1:
        print("--workers, --per-host and --repeat must be >= 1", file=sys.stderr)
        return 2
    overrides: list[tuple[str, int]] = []
    for item in args.host_limit:
        pattern, _, n = item.rpartition("=")
        if not pattern or not n.isdigit() or int(n) < 1:
            print(f"--host-limit takes HOST=N with N >= 1, got '{item}'", file=sys.stderr)
            return 2
        overrides.append((pattern, int(n)))
    named = args.specs or (["specs"] if os.path.isdir("specs") else [])
    specs, problems = collect_specs(named)
    if problems or not specs:
        for p in problems or ["no specs named and no specs/ folder here: give spec files, a folder of them, or an earlier suite's folder"]:
            print(p, file=sys.stderr)
        return 2
    ids: dict[str, str] = {}
    for p in specs:
        sid = spec_id_of(p)
        if sid in ids:
            print(f"two spec files share the id '{sid}': {ids[sid]} and {p}", file=sys.stderr)
            return 2
        ids[sid] = p
    load_dotenv()
    replay = not args.no_replay
    run_args = [*args.run_arg, *(["--headed"] if args.headed else []), *(["--headless"] if args.headless else []),
                *(["--replay"] if replay else []), *(["--replay-verify", args.replay_verify] if replay and args.replay_verify else []),
                *([] if args.no_sessions else ["--reuse-sessions"]), *(["--http-cache"] if args.http_cache else [])]
    out_root = args.out or os.path.join("runs", "suite", datetime.now().strftime("%Y%m%d-%H%M%S"))
    report = run_suite(specs, args.repeat, args.workers, out_root, run_args, args.python, args.runner, args.label, replay,
                       per_host=args.per_host, host_overrides=overrides, quiet=True)
    remembered = state_file(specs, args.state_dir)
    previous = None
    try:
        with open(remembered, encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, ValueError):
        pass
    text = summarize(report, previous)
    with open(os.path.join(out_root, "summary.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    try:
        private_dir(args.state_dir)
        with open(remembered, "w", encoding="utf-8") as f:
            json.dump({"timestamp": report["timestamp"], "out_dir": out_root, "verdicts": report["suite"]["verdicts"]}, f, indent=2)
    except OSError:
        pass  # a read-only checkout: the next rerun has nothing to compare with, and says nothing about changes
    print(text)
    if args.junit:
        from junit import suite_cases, write_junit
        write_junit(args.junit, args.label or "jev-browser-test", suite_cases(report))
    runs = [r for sp in report["specs"].values() for r in sp["runs"]]
    if runs and all(r.get("environment_failure") for r in runs):
        return 2
    return 0 if report["suite"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
