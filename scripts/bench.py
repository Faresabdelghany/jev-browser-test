"""Measure the runner: run one or more specs N times each and report medians.

    python scripts/bench.py specs/smoke-login.json [specs/other.json ...] --repeat 5 [--json out.json]
                            [--label name] [--out-root runs/bench] [--run-arg=--screenshots=none ...]

Each repeat is a fresh `run_test.py` subprocess (its own browser, its own Jev connection), so the
numbers are what a user of the skill sees. Per run it records the subprocess wall-clock, the trace's
`duration_ms`, Jev ms (sum of `latency_ms.jev`), browser ms (sum of `latency_ms.browser`), requests,
tokens, decision confidence (median over the steps that carry one), status, outcome and stale steps.
Per spec it reports the medians of those plus status, outcome and stale-step counts.

Every number quoted in the README or the references comes from this script's `--json` output; the
before/after files live under docs/superpowers/measurements/.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_TEST = os.path.join(HERE, "run_test.py")

RUN_FIELDS = (
    "wall_ms", "duration_ms", "jev_ms", "browser_ms", "requests", "input_tokens", "output_tokens",
    "steps", "actions_executed", "decision_confidence", "min_decision_confidence", "stale_steps",
)


def _median(values: list) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return None
    m = statistics.median(vals)
    return round(m, 3) if isinstance(m, float) and not m.is_integer() else int(m)


def measure_trace(trace: dict) -> dict:
    """Pure: the per-run metrics derived from one trace.json."""
    steps = trace.get("steps") or []
    confs = [s["decision_confidence"] for s in steps if isinstance(s.get("decision_confidence"), (int, float))]
    usage = trace.get("usage") or {}
    return {
        "status": trace.get("status"),
        "pass": bool(trace.get("pass")),
        "error": trace.get("error"),
        "duration_ms": trace.get("duration_ms"),
        "jev_ms": sum(int((s.get("latency_ms") or {}).get("jev") or 0) for s in steps),
        "browser_ms": sum(int((s.get("latency_ms") or {}).get("browser") or 0) for s in steps),
        "requests": usage.get("jev_requests"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "model": usage.get("model"),
        "steps": len(steps),
        "actions_executed": trace.get("actions_executed"),
        "decision_confidence": _median(confs),
        "min_decision_confidence": min(confs) if confs else None,
        "step_confidences": confs,
        "stale_steps": sum(1 for s in steps if s.get("stale")),
        "low_confidence_steps": sum(1 for s in steps if s.get("low_confidence")),
    }


def run_once(spec_path: str, out_dir: str, python: str, run_args: list[str]) -> dict:
    cmd = [python, RUN_TEST, spec_path, "--out", out_dir, *run_args]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    rec: dict = {"out_dir": out_dir, "exit_code": proc.returncode, "wall_ms": wall_ms}
    trace_path = os.path.join(out_dir, "trace.json")
    if os.path.exists(trace_path):
        with open(trace_path, encoding="utf-8") as f:
            rec.update(measure_trace(json.load(f)))
    else:
        rec.update({"status": "error", "pass": False, "error": (proc.stderr or proc.stdout or "")[-500:].strip()})
    result_path = os.path.join(out_dir, "result.json")
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
        rec["outcome"] = result.get("outcome")
        rec["verdict"] = result.get("verdict")
    return rec


def aggregate(runs: list[dict]) -> dict:
    """Pure: medians and counts over the per-run records of one spec."""
    medians = {k: _median([r.get(k) for r in runs]) for k in RUN_FIELDS}
    all_confs = [c for r in runs for c in (r.get("step_confidences") or [])]
    medians["decision_confidence_all_steps"] = _median(all_confs)
    counts: dict = {}
    for r in runs:
        counts[str(r.get("status"))] = counts.get(str(r.get("status")), 0) + 1
    outcomes: dict = {}
    for r in runs:
        if r.get("outcome") is not None:
            outcomes[str(r["outcome"])] = outcomes.get(str(r["outcome"]), 0) + 1
    return {
        "medians": medians,
        "status_counts": counts,
        "outcome_counts": outcomes,
        "stale_steps_total": sum(int(r.get("stale_steps") or 0) for r in runs),
        "passes": sum(1 for r in runs if r.get("pass")),
    }


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=os.path.dirname(HERE)).stdout.strip() or None
    except OSError:
        return None


def format_spec(spec_id: str, runs: list[dict], agg: dict) -> str:
    lines = [f"== {spec_id}  ({len(runs)} runs)"]
    lines.append(f"{'#':>3} {'status':<16} {'outcome':<16} {'wall':>7} {'dur':>7} {'jev':>6} {'brow':>6} {'req':>4} "
                 f"{'in_tok':>7} {'conf':>5} {'stale':>5}")
    for i, r in enumerate(runs, 1):
        lines.append(
            f"{i:>3} {str(r.get('status')):<16} {str(r.get('outcome') or '-'):<16} {r.get('wall_ms', 0):>7} "
            f"{str(r.get('duration_ms') or '-'):>7} {str(r.get('jev_ms') or '-'):>6} {str(r.get('browser_ms') or '-'):>6} "
            f"{str(r.get('requests') or '-'):>4} {str(r.get('input_tokens') or '-'):>7} "
            f"{str(r.get('decision_confidence') if r.get('decision_confidence') is not None else '-'):>5} "
            f"{str(r.get('stale_steps') or 0):>5}"
        )
    m = agg["medians"]
    lines.append(
        f"med {'':<16} {'':<16} {str(m['wall_ms']):>7} {str(m['duration_ms']):>7} {str(m['jev_ms']):>6} "
        f"{str(m['browser_ms']):>6} {str(m['requests']):>4} {str(m['input_tokens']):>7} "
        f"{str(m['decision_confidence']):>5} {str(m['stale_steps']):>5}"
    )
    lines.append(f"    status: {agg['status_counts']}  outcomes: {agg['outcome_counts'] or '-'}  "
                 f"stale steps total: {agg['stale_steps_total']}  "
                 f"conf (all steps) median: {m['decision_confidence_all_steps']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="spec files to run")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--json", dest="json_out", help="write the full measurement here")
    ap.add_argument("--label", default="", help="free-text label stored in the JSON (e.g. track1-baseline)")
    ap.add_argument("--out-root", default=os.path.join("runs", "bench"), help="where the run folders go")
    ap.add_argument("--run-arg", action="append", default=[], help="extra argument passed through to run_test.py (repeatable)")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args(argv[1:])
    if args.repeat < 1:
        print("--repeat must be >= 1", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report: dict = {
        "label": args.label,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "repeat": args.repeat,
        "run_args": args.run_arg,
        "env": {k: v for k, v in os.environ.items() if k.startswith("JEV_") or k == "TYPESAFE_MODEL"},
        "specs": {},
    }
    for spec_path in args.specs:
        with open(spec_path, encoding="utf-8") as f:
            spec_id = json.load(f).get("id") or os.path.splitext(os.path.basename(spec_path))[0]
        runs = []
        for i in range(1, args.repeat + 1):
            out_dir = os.path.join(args.out_root, spec_id, f"{stamp}-{i:02d}")
            rec = run_once(spec_path, out_dir, args.python, args.run_arg)
            runs.append(rec)
            print(f"{spec_id} run {i}/{args.repeat}: {rec.get('status')} "
                  f"{('outcome=' + str(rec['outcome']) + ' ') if rec.get('outcome') else ''}"
                  f"wall={rec['wall_ms']}ms jev={rec.get('jev_ms')}ms browser={rec.get('browser_ms')}ms "
                  f"req={rec.get('requests')} conf={rec.get('decision_confidence')} stale={rec.get('stale_steps')}",
                  flush=True)
        agg = aggregate(runs)
        report["specs"][spec_id] = {"spec": spec_path, "runs": runs, **agg}
        print(format_spec(spec_id, runs, agg))
        print()
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"saved {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
