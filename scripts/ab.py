"""A/B a runner option over a set of specs: does turning it on change what the specs that do not need it end in?

    python scripts/ab.py specs/examples/*.json --b-arg=--hover --repeat 3
    python scripts/ab.py specs/examples/*.json --b-arg=--shadow-dom --b-arg=--hover --repeat 5 --out runs/ab/both

Arm A runs every spec as it is; arm B runs it with the `--b-arg` options added to `run_test.py`. The question this
answers is the one the standing rules were measured with: an option that is offered on every step is a choice on
every step, and a choice Jev does not need can still pull its confidence apart. So the report compares, per spec,
what each arm ended in, the median decision confidence over every step, the Jev requests and the wall-clock.

The runs are **interleaved** (A, B, A, B, ... for one spec, then the next spec), one at a time: a shared demo host has
slow hours, and two arms run one after the other would measure the hour, not the option. Every run is its own
`run_test.py` subprocess with its own browser, as in a suite.

Writes `ab.json` (every run) and `ab.md` (the table and the reading) into the output directory and prints the table.
Exit 0 when no spec's result moved between the arms, 1 when one did, 2 when the comparison could not run.

Reading it: a verdict that differs between the arms in every repeat is the option's doing; one that differs in some
repeats needs more repeats before it is anything (run the spec alone with `--repeat 10`). A median confidence that
falls by more than 0.05 with the verdicts unchanged is a warning, not a result: the wordings the rules A/B rejected
fell from 0.95 to 0.5.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

from bench import _median, run_once
from run_suite import spec_id_of

CONFIDENCE_DROP = 0.05  # a fall of the median decision confidence beyond this is flagged
ENVIRONMENT = "environment"  # a run that never observed a page (exit 2): not an ending of the flow


def ending(run: dict) -> str:
    """What one run ended in, as the arms are compared on: the declared outcome, or the status of an undetermined
    run; an exit-2 run (spec or environment problem, start page never loaded) is `environment` and is left out."""
    if run.get("exit_code") == 2:
        return ENVIRONMENT
    outcome = run.get("outcome")
    return outcome if outcome and outcome != "undetermined" else f"undetermined:{run.get('status')}"


def arm_summary(runs: list[dict]) -> dict:
    observed = [r for r in runs if ending(r) != ENVIRONMENT]
    endings: dict[str, int] = {}
    for r in observed:
        endings[ending(r)] = endings.get(ending(r), 0) + 1
    confs = [c for r in observed for c in (r.get("step_confidences") or [])]
    return {
        "runs": len(runs),
        "observed": len(observed),
        "green": sum(1 for r in observed if r.get("exit_code") == 0),
        "endings": endings,
        "decision_confidence": _median(confs),  # over every step of every observed run
        "min_decision_confidence": min(confs) if confs else None,
        "low_confidence_steps": sum(int(r.get("low_confidence_steps") or 0) for r in observed),
        "requests": _median([r.get("requests") for r in observed]),
        "input_tokens": _median([r.get("input_tokens") for r in observed]),
        "wall_ms": _median([r.get("wall_ms") for r in observed]),
    }


def compare(a: dict, b: dict) -> dict:
    """Pure: how arm B differs from arm A for one spec. `moved` is "all" when the two arms share no ending, "some"
    when the sets of endings differ, None when they are the same set; `confidence_delta` is B minus A."""
    moved = None
    if a["observed"] and b["observed"]:
        if not set(a["endings"]) & set(b["endings"]):
            moved = "all"
        elif set(a["endings"]) != set(b["endings"]) or a["green"] * b["observed"] != b["green"] * a["observed"]:
            moved = "some"
    delta = None
    if isinstance(a["decision_confidence"], (int, float)) and isinstance(b["decision_confidence"], (int, float)):
        delta = round(b["decision_confidence"] - a["decision_confidence"], 3)
    return {"moved": moved, "confidence_delta": delta,
            "confidence_fell": delta is not None and delta < -CONFIDENCE_DROP,
            "compared": bool(a["observed"] and b["observed"])}


def _endings(s: dict) -> str:
    if not s["observed"]:
        return f"no run observed a page ({s['runs']} environment failures)"
    text = ", ".join(f"{k} x{v}" for k, v in sorted(s["endings"].items(), key=lambda kv: -kv[1]))
    return text + (f" (+{s['runs'] - s['observed']} environment)" if s["runs"] != s["observed"] else "")


def _num(v, digits: int = 2) -> str:
    return "-" if v is None else (f"{v:.{digits}f}" if isinstance(v, float) else str(v))


def render(report: dict) -> str:
    lines = [f"# A/B: {' '.join(report['b_args'])}", "",
             f"{len(report['specs'])} spec(s) x {report['repeat']} repeat(s) per arm, interleaved; arm A as the spec is, arm B with "
             f"`{' '.join(report['b_args'])}`. {report['timestamp']}", "",
             "| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |",
             "|---|---|---|---|---:|---:|---:|---:|---:|"]
    for spec_id, sp in report["specs"].items():
        a, b, c = sp["a"], sp["b"], sp["compare"]
        moved = {"all": "**yes, every run**", "some": "some runs", None: "no"}[c["moved"]] if c["compared"] else "not compared"
        delta = "-" if c["confidence_delta"] is None else f"{c['confidence_delta']:+.3f}" + (" ⚠" if c["confidence_fell"] else "")
        lines.append(f"| {spec_id} | {_endings(a)} | {_endings(b)} | {moved} | {_num(a['decision_confidence'])} | {_num(b['decision_confidence'])} | "
                     f"{delta} | {_num(a['requests'], 0)} / {_num(b['requests'], 0)} | "
                     f"{_num((a['wall_ms'] or 0) / 1000, 1)} / {_num((b['wall_ms'] or 0) / 1000, 1)} |")
    s = report["summary"]
    lines += ["", f"**{s['moved_all']} spec(s) ended differently in every run, {s['moved_some']} in some runs, {s['confidence_fell']} lost more than "
                  f"{CONFIDENCE_DROP} of median decision confidence, {s['not_compared']} could not be compared.**", ""]
    if s["moved_all"] or s["moved_some"] or s["confidence_fell"]:
        lines.append("Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some "
                     "runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a "
                     "moved spec side by side: the step where the operations differ is where to look.")
    elif s["not_compared"]:
        lines.append("No spec moved among those compared, but some never observed a page in one arm (the host, the key or the spec): rerun those.")
    else:
        lines.append("No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it "
                     "the default, as strong as the specs are varied and the repeats many.")
    return "\n".join(lines) + "\n"


def summarize(specs: dict) -> dict:
    return {"moved_all": sum(1 for sp in specs.values() if sp["compare"]["moved"] == "all"),
            "moved_some": sum(1 for sp in specs.values() if sp["compare"]["moved"] == "some"),
            "confidence_fell": sum(1 for sp in specs.values() if sp["compare"]["confidence_fell"]),
            "not_compared": sum(1 for sp in specs.values() if not sp["compare"]["compared"])}


def main(argv: list[str]) -> int:
    from spec import utf8_stdio
    utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="spec files to run in both arms")
    ap.add_argument("--b-arg", action="append", default=[], metavar="ARG",
                    help="a run_test.py option arm B adds, e.g. --b-arg=--hover (repeatable; required)")
    ap.add_argument("--a-arg", action="append", default=[], metavar="ARG", help="an option arm A adds (default: none, the spec as it is)")
    ap.add_argument("--repeat", type=int, default=3, help="runs per spec per arm (default 3; 5 or more before deciding anything)")
    ap.add_argument("--out", help="output directory (default runs/ab/<timestamp>)")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args(argv[1:])
    if not args.b_arg:
        print("nothing to compare: give arm B at least one option, e.g. --b-arg=--hover", file=sys.stderr)
        return 2
    if args.repeat < 1:
        print("--repeat must be >= 1", file=sys.stderr)
        return 2
    missing = [p for p in args.specs if not os.path.exists(p)]
    if missing:
        print("spec file(s) not found: " + ", ".join(missing), file=sys.stderr)
        return 2
    out_root = args.out or os.path.join("runs", "ab", datetime.now().strftime("%Y%m%d-%H%M%S"))
    specs: dict = {}
    for path in dict.fromkeys(os.path.abspath(p) for p in args.specs):
        spec_id = spec_id_of(path)
        runs: dict[str, list[dict]] = {"a": [], "b": []}
        for i in range(1, args.repeat + 1):
            for arm, extra in (("a", args.a_arg), ("b", args.b_arg)):  # interleaved: both arms see the same hour
                rec = run_once(path, os.path.join(out_root, spec_id, f"{arm}{i:02d}"), args.python, list(extra))
                runs[arm].append(rec)
                print(f"{spec_id} {arm.upper()}{i}: {ending(rec)}  conf {_num(rec.get('decision_confidence'))}  "
                      f"{_num(rec.get('requests'), 0)} requests  {(rec.get('wall_ms') or 0) / 1000:.1f} s", file=sys.stderr)
        a, b = arm_summary(runs["a"]), arm_summary(runs["b"])
        specs[spec_id] = {"spec": path, "a": a, "b": b, "compare": compare(a, b), "runs": runs}
    report = {"timestamp": datetime.now().isoformat(timespec="seconds"), "repeat": args.repeat, "a_args": args.a_arg,
              "b_args": args.b_arg, "specs": specs, "summary": summarize(specs)}
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "ab.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    text = render(report)
    with open(os.path.join(out_root, "ab.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"results: {os.path.join(out_root, 'ab.json')}  {os.path.join(out_root, 'ab.md')}")
    s = report["summary"]
    if s["not_compared"] == len(specs):
        return 2
    return 1 if (s["moved_all"] or s["moved_some"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
