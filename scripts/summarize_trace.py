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

# executed.action values that are not browser actions: terminal markers. Runner-inserted WAITs carry a `reason`.
NON_ACTIONS = (None, "STOP", "DONE", "AUTO_DONE", "BLOCKED")
NO_EFFECT_ACTIONS = ("CLICK", "TYPE_TEXT", "SELECT", "PRESS_ENTER")  # the same set run_test flags; older traces lack `no_effect`


def is_action_step(step: dict) -> bool:
    """True for a step whose action changed the browser: not a terminal marker, not a runner-inserted WAIT.
    The one definition behind trace.actions_executed, result.story / path_confidence (run_test) and the
    per-action latencies (bench, run_suite)."""
    ex = step.get("executed") or {}
    return ex.get("action") not in NON_ACTIONS and not ex.get("reason")


def _via_lines(via: dict | None) -> list[str]:
    """The summary's line about the control under test (spec `via`): used or not, and what the page did in answer."""
    if not via:
        return []
    named = ", ".join(f"{k} '{v}'" for k, v in (via.get("action") or {}).items())
    if via.get("executed_at_step") is None:
        return [f"  via ({named}): never used; a pass seen without it does not count (the goal should say to use it)"]
    head = f"  via ({named}): step {via['executed_at_step']}, {via.get('target')}"
    if via.get("effect") is True:
        return [head + f"; the page answered at step {via.get('effect_at_step')} ({', '.join(via.get('changed') or [])} changed)"]
    if via.get("effect") is False:
        then = f"; the run then wanted: {via['then']}" if via.get("then") else ""
        return [head + f"; NOTHING on the page changed but the control itself ({via.get('waited_ms', 0)} ms given){then}"]
    return [head + "; " + (f"not judged ({via['not_judged']})" if via.get("not_judged") else "the run ended before the next look")]


def _fmt_conf(step: dict) -> str:
    if step.get("replayed"):
        return "saved path"  # no request, so no confidence: the step came from the path of an earlier passing run
    op = step.get("operation") or {}
    tg = step.get("target") or {}
    a = f"{op.get('confidence', 0):.2f}" if op else "-"
    b = f"{tg.get('confidence', 0):.2f}" if tg and not tg.get("missing") else "-"
    tv = step.get("type_value") or step.get("upload_file")  # which value to type, or which file to attach
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


def _replay_lines(rp: dict | None) -> list[str]:
    """What a run with replay on did with the saved path: how many steps it walked without Jev, where Jev took over
    and why, how the ending was decided, whether this run's path was saved."""
    if not rp:
        return []
    if not rp.get("used"):
        line = f"  replay: no saved step used ({rp.get('not_used')})"
    else:
        line = f"  replay: {rp.get('steps_replayed')} of {rp.get('steps_in_path')} saved steps replayed without Jev"
        hb = rp.get("handed_back")
        if hb:
            at = f"saved step {hb['path_step']}" if hb.get("path_step") else "the ending"
            line += f"; Jev took over at step {hb.get('at_step')} ({at}): {hb.get('reason')}"
            if rp.get("resumed"):
                line += f"; the path resumed after Jev chose the saved step itself ({len(rp['resumed'])} time{'s' if len(rp['resumed']) != 1 else ''})"
        elif rp.get("verified_by"):
            line += "; the ending was decided by " + ("the assertions alone" if rp["verified_by"] == "assertions" else "Jev (one request) and the assertions")
    line += "; path saved" if rp.get("saved") else ""
    return [line] + ([f"  replay: {rp['note']}"] if rp.get("note") else [])


def _flags(step: dict, nxt: dict | None = None) -> str:
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
    if ex.get("slow_navigation"):
        f.append(f"SLOW-NAV:{ex['slow_navigation'].get('ms', 0) / 1000:.1f}s")  # the action landed; its navigation outlasted action_timeout_ms
    if step.get("repeat_count", 0) > 1:
        f.append(f"REPEAT×{step['repeat_count']}")
    if step.get("never_violated"):
        f.append("NEVER:" + ",".join(step["never_violated"]))
    if step.get("outcome_seen"):
        f.append("OUTCOME:" + step["outcome_seen"])
    if step.get("pending_outcome"):
        f.append("PENDING:" + step["pending_outcome"])
    if step.get("recheck_again"):
        f.append(f"RECHECK:{step['recheck_again']}")  # the confirmation look found the page still changing or busy and parked again
    if step.get("assertions_pending"):
        f.append(f"ASSERT-PENDING:{len(step['assertions_pending'])}")  # a pass in sight whose assertions do not hold yet on this busy page
    if step.get("final_look"):
        f.append("FINAL-LOOK")
    if step.get("batched"):
        f.append("BATCHED")  # typed without a request of its own: Jev assigned the value in the request that typed the form's first field
    if step.get("batch_stopped"):
        f.append("BATCH-ENDED")  # the page reacted to what was typed (step.batch_stopped says how); Jev decides again from here
    if step.get("replay_resumed"):
        f.append("REPLAY-RESUMED")  # Jev decided this step after a handover and chose what the saved step says: the path goes on
    if step.get("replay_handback"):
        f.append("REPLAY-ENDED")  # the saved path stopped applying here (step.replay_handback says why); Jev decides from this step on
    if step.get("replay_verify"):
        f.append("REPLAY-VERIFY")  # the look that decides the ending of a replayed run: outcome and checks, no operation
    if step.get("outcome_unconfirmed"):
        f.append("UNCONFIRMED:" + step["outcome_unconfirmed"])
    if step.get("assertions") and not all(a.get("ok") for a in step["assertions"]):
        f.append("ASSERT-FAILED")
    if step.get("no_effect") or (step.get("page_changed") is False and ex.get("action") in NO_EFFECT_ACTIONS and ex.get("ok")):
        f.append("NO-EFFECT")  # the action landed and the page Jev sees did not change (a dead control?); derived for older traces
    if step.get("via"):
        f.append("VIA")  # the action the spec's `via` names: the control under test was used here
    if step.get("via_deferred"):
        f.append("VIA-WAIT")  # the control under test was about to be used on a page still loading: waited for, then decided again
    if step.get("via_no_effect"):
        f.append("VIA-NO-EFFECT")  # a look at the page after the via action: nothing but the control itself has changed
    if step.get("via_effect"):
        f.append("VIA-ANSWERED")  # the first look on which the page differs from the one the via action was used on
    if step.get("outcome_held"):
        f.append("HELD:" + step["outcome_held"]["outcome"])  # a non-pass outcome read off a page that said it was loading: not the ending yet
    if step.get("undecided_wait"):
        # undecided, the looks used up, and the page still said it was loading: waited for without a request, then decided again
        f.append(f"LOADING-WAIT:{step['undecided_wait'].get('ms', 0) / 1000:.1f}s")
    if step.get("outcome_deferred"):
        f.append("DEFERRED:" + ",".join(step["outcome_deferred"]))  # true of the page, but no action was taken yet (requires_action)
    if step.get("covered_controls"):
        # controls on screen under another layer, not offered; (layer:m) when the layer has m controls of its own (a dialog, an
        # open list), nothing when it is blank (a loading or saving overlay)
        layer = f"(layer:{step['layer_controls']})" if step.get("layer_controls") else ""
        f.append(f"COVERED:{step['covered_controls']}{layer}")
    if step.get("loading_options"):
        f.append(f"LOADING:{step['loading_options']}")  # autocomplete rows that only said 'Searching....' / 'Loading...': not offered
    if step.get("action_deferred"):
        d = step["action_deferred"]  # a marginal action while that many controls were under a blank layer (or, with none covered,
        f.append(f"DEFERRED-{d.get('operation')}:{d.get('covered') or 'loading'}")  # while an autocomplete's placeholder showed): a wait instead
    if step.get("deferrals_exhausted"):
        f.append(f"DEFER-LIMIT:{step['deferrals_exhausted']}")  # executed on a page still under its blank layer, after that many deferrals
    if step.get("announcements"):
        # what the page announced (a toast, a live message) between the previous observation and this one; the first message shown
        first = step["announcements"][0].get("text") or ""
        more = len(step["announcements"]) - 1
        f.append(f'ANNOUNCED:"{first[:40]}{"…" if len(first) > 40 else ""}"' + (f" +{more}" if more else ""))
    if step.get("loading_indicators"):
        f.append(f"LOADING-IND:{step['loading_indicators']}")  # spinners / progress bars / 'Loading...' lines that cover nothing
    d = step.get("diagnostics") or {}
    # what the browser reported between the previous observation and this one (the action before this step caused it)
    if d.get("page_errors"):
        f.append(f"JS-ERROR:{d['page_errors']}")  # uncaught JavaScript exceptions
    if d.get("server_errors"):
        f.append(f"HTTP-5xx:{d['server_errors']}")
    if d.get("http_errors", 0) - d.get("server_errors", 0) > 0:
        f.append(f"HTTP-4xx:{d['http_errors'] - d.get('server_errors', 0)}")
    if d.get("failed_requests"):
        f.append(f"REQ-FAILED:{d['failed_requests']}")  # requests that never got an answer (DNS, refused, reset)
    if d.get("console_errors"):
        f.append(f"CONSOLE-ERR:{d['console_errors']}")
    if step.get("new_tab"):
        f.append("NEW-TAB" if step["new_tab"].get("followed") else "NEW-TAB(not followed)")  # the action opened a tab
    if step.get("adjudication_merged"):
        f.append("EVIDENCE-ASKED")  # the evidence questions rode in this confirmation request
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
    if "NO-EFFECT" in f and nxt and ((nxt.get("covered_controls") and not nxt.get("layer_controls")) or nxt.get("announcements")):
        # the next look showed a blank layer over the controls or a toast: the click landed and the app was working on it
        # (a Save in flight on a single-page app), which a dead control never shows; read NO-EFFECT alone as the dead control
        f.append("IN-FLIGHT")
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
            head += (f"  ({r.get('status')}" + (f"; {typed}" if typed else "") + f"; suggested verdict: {r.get('suggested_verdict') or 'judge yourself'}"
                     + (", from the hint below" if r.get("suggestion_from") == "hints" else "") + ")")
        elif result.get("seen_at_step"):
            head += f"  seen at step {result['seen_at_step']}" + (f" (confirmed by {result.get('confirmed_by') or 'recheck'})" if result.get("confirmed") else "")
        lines.append(head)
        if (result.get("evidence") or {}).get("line"):
            lines.append(f"  evidence: \"{result['evidence']['line']}\"")
        elif (result.get("evidence") or {}).get("skipped"):
            asked = "evidence: \"failures\"" if "failures" in result["evidence"]["skipped"] else result["evidence"]["skipped"]
            lines.append(f"  evidence: line not asked ({asked}); the assertions below are the proof")
        if result.get("note"):
            lines.append(f"  note: {result['note']}")
    lines.extend(_via_lines(trace.get("via")))
    lines.extend(_replay_lines(trace.get("replay")))
    if trace.get("expected") is not None:
        ex = trace["expected"]
        lines.append(f"  expected result: {'MATCHED' if ex.get('matched') else 'NOT MATCHED'}  expect={ex.get('expect')}"
                     + ("" if ex.get("matched") else f"  actual={ex.get('mismatches')}"))
    if trace.get("status_meaning"):
        lines.append(f"  meaning: {trace['status_meaning']}")
    if trace.get("failed_before_observation"):
        lines.append(f"  not a verdict: the {trace['failed_before_observation']} failed before the flow was observed "
                     f"({'a slow or unreachable host: environment' if trace['failed_before_observation'] == 'navigation' else 'a setup step: fix the spec'}); exit 2")
    if trace.get("error"):
        lines.append(f"  error: {trace['error']}")
    if trace.get("passed_without_actions"):
        lines.append("  WARNING: passed on the start page before any action; the done_when checks may be too weak")
    lines.append(f"  goal: {spec.get('goal')}")
    sess = trace.get("session")
    if sess and sess.get("reused"):
        lines.append(f"  login: skipped, the session saved {sess.get('age_s', 0) // 60} min ago was reused")
    elif trace.get("login"):
        ok = sum(1 for s in trace["login"] if s.get("ok"))
        lines.append(f"  login: {ok}/{len(trace['login'])} scripted steps ok"
                     + (f"; no saved session used ({sess.get('not_reused')})" if sess and sess.get("not_reused") else "")
                     + ("; session saved" if sess and sess.get("saved") else ""))
    if trace.get("setup"):
        ok = sum(1 for s in trace["setup"] if s.get("ok"))
        lines.append(f"  setup: {ok}/{len(trace['setup'])} scripted steps ok")
    td = trace.get("teardown_result")
    if td:
        lines.append(f"  teardown: {td.get('ran')}/{td.get('steps')} scripted steps ok"
                     + ("" if td.get("ok") else f"  (step {td['failed'].get('n')} failed: {td['failed'].get('error')}; the result above stands)"))
    device = (trace.get("browser") or {}).get("device")
    if device:
        lines.append(f"  device: {device}")
    diag = (trace.get("diagnostics") or {}).get("counts")
    if diag:
        lines.append("  browser diagnostics: " + ", ".join(f"{diag.get(k, 0)} {label}" for k, label in (
            ("page_errors", "uncaught JS exception(s)"), ("server_errors", "5xx response(s)"), ("http_errors", "4xx/5xx response(s) in all"),
            ("failed_requests", "failed request(s)"), ("console_errors", "console error(s)")) if diag.get(k))
                     + "  (trace.diagnostics has each one, with the step it preceded)")
    final = trace.get("final") or {}
    lines.append(f"  start: {spec.get('start_url')}")
    lines.append(f"  end:   {final.get('url')}  \"{final.get('title')}\"")
    lines.append("")
    lines.append(f"{'#':>3}  {'operation':<20} {'target / value':<58} {'conf op/tgt/val':<16} checks  flags")
    steps = trace.get("steps", [])
    for i, s in enumerate(steps):
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
        if s.get("upload_file"):
            target += f" <- file {s['upload_file'].get('choice')}"
        if len(target) > 58:
            target = target[:55] + "..."
        lines.append(
            f"{s['n']:>3}  {op:<20} {target:<58} {_fmt_conf(s):<16} {_fmt_checks(s.get('checks', {}), spec)}  {_flags(s, steps[i + 1] if i + 1 < len(steps) else None)}".rstrip()
        )
    lines.extend(_hidden_controls_hint(trace))
    lines.append("")
    lines.append("final checks: " + _fmt_checks(final.get("checks", {}), spec))
    assertions = (trace.get("result") or {}).get("assertions") or []
    if assertions:
        lines.append("assertions: " + "  ".join(
            f"{'✓' if a.get('ok') else '✗'} {next(k for k in a if k not in ('ok', 'actual'))}" for a in assertions))
    if out_dir:
        lines.append(f"result: {os.path.join(out_dir, 'result.json')}  trace: {os.path.join(out_dir, 'trace.json')}" + _screenshot_hint(trace))
    return "\n".join(lines)


STALLED_STATUSES = ("stuck", "blocked", "low_confidence", "budget_exhausted")


def unobserved_controls(spec: dict, last: dict) -> list[str]:
    """Where the last page may keep controls the observer did not offer, one sentence each naming the spec option that
    opens it: an <iframe> the spec does not list, shadow DOM the spec turned off, a file field without `files`. Empty
    when the page has none of them. The summary prints these under the step table of a stalled run, and result.json
    carries them as `reason.hints` (run_test.build_result), where they also turn a `control_not_on_page` suggestion
    from bug into test_issue: the control may be exactly where the spec did not let the runner look."""
    listed = ((spec or {}).get("observation") or {}).get("frames") or []
    hints = []
    if last.get("iframes", 0) > len([f for f in last.get("frames") or [] if f.get("elements")]):
        hints.append(f"the last page shows {last['iframes']} <iframe>(s)" + (f", {len(listed)} listed in observation.frames" if listed else "")
                     + ". Controls inside a frame are offered only when the spec lists the frame's selector in observation.frames "
                       "(or script them in setup with \"frame\").")
    if last.get("shadow_hosts"):
        hints.append(f"{last['shadow_hosts']} element(s) on the last page keep controls inside shadow DOM, which the observer "
                     "does not offer because the spec turns it off (\"observation\": {\"shadow_dom\": false} or --no-shadow-dom). A scripted setup "
                     "step reaches them too: Playwright selectors go into open shadow roots.")
    if not (spec or {}).get("files") and any(e.get("role") == "file" for e in last.get("elements") or []):
        hints.append("the last page has a file field and the spec declares no `files`. Give the files Jev may attach "
                     "(\"files\": {\"cv\": \"fixtures/cv.pdf\"}) and UPLOAD_FILE is offered, or script the upload in setup.")
    return hints


def _hidden_controls_hint(trace: dict) -> list[str]:
    """A run that could not make progress on a page with an <iframe> the spec does not list, or with controls inside
    shadow DOM, may have been looking for a control the observer never offered: say where to look. Silent for runs
    that ended in a declared outcome, and for pages with neither."""
    steps = trace.get("steps") or []
    if trace.get("status") not in STALLED_STATUSES or not steps:
        return []
    return ["  hint: " + h for h in unobserved_controls(trace.get("spec") or {}, steps[-1])]


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
                f"[{e['idx']}] {e['role']} \"{e.get('name', '')}\""
                + (f" <{e.get('tag', '?')}> at ({e.get('x', '?')},{e.get('y', '?')})" if not e.get("name") else "")  # an unnamed element: what and where
                + (f" value=\"{e['value']}\"" if e.get("value") else "")
                + (" (below the fold)" if e.get("below") else "")
                for e in elements
            ) or "(no element table recorded for this step: only steps that chose an element carry one)"
            return f"{body}\n\nelements offered at step {n}:\n{table}"
    return f"no step {n} in trace"


def main(argv: list[str]) -> int:
    from spec import utf8_stdio
    utf8_stdio()
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
        result_path = os.path.join(run_dir, "result.json")
        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as f:
                print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
            return 0
        trace_path = os.path.join(run_dir, "trace.json")
        if os.path.exists(trace_path):  # a run recorded before the results contract, or a trace handed over alone
            with open(trace_path, encoding="utf-8") as f:
                embedded = json.load(f).get("result")
            if embedded:
                print(json.dumps(embedded, indent=2, ensure_ascii=False))
                return 0
        print(f"no result.json in {run_dir or '.'} (a run from before the results contract, or a trace on its own): "
              f"read the step summary instead", file=sys.stderr)
        return 1
    with open(path, encoding="utf-8") as f:
        trace = json.load(f)
    if args.step:
        print(dump_step(trace, args.step))
    else:
        print(summarize(trace, run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
