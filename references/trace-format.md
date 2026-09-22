# Trace and result format

Every run writes `result.json`, `trace.json` and `steps/NNN.png` screenshots into its output directory.
`result.json` is the *verdict*: exactly one of the spec's declared outcomes (or `undetermined`) with its
evidence, the file Claude reads first. The trace is the *evidence* behind it; the summary
(`scripts/summarize_trace.py`) is the fast way to read it.

## result.json

```jsonc
{
  "spec_id": "smoke-login-badpw",
  "outcome": "bad_credentials", "verdict": "pass",              // one of the spec's outcomes, or "undetermined" with verdict null
  "note": "the wrong password is deliberate: ...",             // the outcome's note, copied for Claude
  "probability": 0.91, "confidence": 0.88,                      // the outcome Choice at the step it was seen (null for a checks-only outcome's confidence)
  "seen_at_step": 5, "first_seen_at_step": 4, "confirmed": true, // first_seen: the sighting; seen_at: the confirming step for a pass (the same step for other verdicts)
  "path_confidence": 0.89,                                      // the weakest executed decision on the way: report the least certain judgment
  "reason": null,                                               // for undetermined: see below
  "evidence": { "line": "Your password is invalid!",            // the page line Jev selected in the adjudication request (verbatim), or null
                "present": 0.94,                                // the adjudication's Noul over the outcome statement
                "screenshot": "steps/005.png",                  // the sighting step's picture (forced for non-pass outcomes), else final.png
                "checks": { "logged_in": 0.03, "login_error": 0.81 } },   // the checks at the sighting step
  "assertions": [ { "url_matches": "**/login", "ok": true, "actual": "https://.../login" } ],   // every assertion with what was found
  "outcomes_seen_earlier": [],                                  // non-terminal sightings: non-pass ones (fail_fast: false) and pass sightings that vanished on their recheck ({.., "unconfirmed": true})
  "story": [ "1 TYPE_TEXT [0] textbox \"Username\" <- username", "2 TYPE_TEXT [1] textbox \"Password\" <- password", "3 CLICK [2] button \"Login\"" ],
  "status": "passed", "duration_ms": 6200,
  "usage": { "jev_requests": 6, "input_tokens": 9774, "output_tokens": 1741, "model": "jev-1.13.0", "reconnects": 0 },
  "trace": "runs/smoke-login-badpw/20260922-101500/trace.json"
}
```

`outcome: "undetermined"` means no declared outcome was seen: the loop ended `stuck | blocked |
low_confidence | done_unverified | budget_exhausted | unstable_page | error`, or a pass outcome was seen but
an assertion failed (`assert_failed`). Then `reason` is `{ "status", "blocked_reason", "stuck_reason",
"suggested_verdict" }` plus `failed_assertions` (with `actual` values) and `outcome_seen` for
`assert_failed`, `pending_outcome` for a `budget_exhausted` whose final look saw a pass for the first time
(not rechecked, so not a pass: give the run one more step), and `error` for `error`. `blocked_reason` is Jev's answer on the terminal step to "what most
prevents progress" (`nothing | missing_data_value | control_not_on_page | site_refused_or_error |
human_step_required | wrong_page | other`); `stuck_reason` is asked only after an action with
`page_changed: false` (`control_had_no_effect | overlay_or_modal | still_loading |
needs_scroll_or_other_control | other`). The suggestion comes from a fixed table: `stuck_reason` counts for
`stuck`, `blocked_reason` for `blocked`, `stuck`, `low_confidence` and `budget_exhausted` (a typed reason with
a row wins over the status row there); for `done_unverified`, `assert_failed`, `unstable_page` and `error`
the status row alone decides, because on those endings the step's `blocked_reason` is about progress on the
page, not about the verdict:

| reason or status | suggested verdict |
|---|---|
| `missing_data_value`, `wrong_page`, `low_confidence`, `budget_exhausted` | TEST_ISSUE |
| `control_not_on_page`, `control_had_no_effect`, `overlay_or_modal`, `site_refused_or_error` | BUG |
| `human_step_required` | NEEDS_HUMAN |
| `still_loading`, `unstable_page`, `error` | FLAKY |
| `done_unverified`, `assert_failed`, `other`, `nothing`, `needs_scroll_or_other_control` | none: Claude judges from the trace |

Exit codes: 0 ⇔ verdict `pass` (status `passed`); 1 for every other outcome and for `undetermined`; 2 for a
spec or environment problem (no result is written).

## Suite results (`scripts/run_suite.py`)

A suite run writes `results.json` and `results.md` into `runs/suite/<ts>/`. Every path under `specs` (the
`spec` file, each run's `out_dir`, `trace` and `result`) is **relative to the directory holding
`results.json`**, so the files stay meaningful when the directory is moved, copied or committed; the top-level
`out_dir` is the output directory as it was given on the command line. `python scripts/report.py
runs/suite/<ts>` (or its `results.json`) resolves them against that location and writes one `report.html`
per run that has a trace.

```jsonc
{
  "label": "", "timestamp": "...", "git_commit": "185a10f", "repeat": 5, "workers": 4, "elapsed_ms": 18400,
  "out_dir": "runs/suite/<ts>",
  "specs": {
    "smoke-login": {
      "spec": "../../../specs/smoke-login.json",
      "runs": [ { "run": 1, "out_dir": "smoke-login/01", "trace": "smoke-login/01/trace.json", "result": "smoke-login/01/result.json",
                  "exit_code": 0, "wall_ms": 6100,
                  "outcome": "logged_in", "verdict": "pass", "status": "passed", "first_seen_at_step": 4,
                  "evidence_line": "You logged into a secure area!", "suggested_verdict": null,
                  "duration_ms": 6000, "jev_ms": 2000, "requests": 6, "input_tokens": 8900, "decision_confidence": 0.96, ... } ],
      "outcome_counts": { "logged_in": 5 }, "verdict_counts": { "pass": 5 }, "suggested_verdicts": {},
      "agreement": 1.0,                       // share of the observed runs that ended in the most common outcome
      "verdict": "pass",                      // unanimous -> that outcome's verdict; undetermined everywhere -> "undetermined"; else "flaky"
      "environment_failures": [],             // runs that wrote no trace: [{ "run": 2, "exit_code": 2, "error": "could not attach to the browser at ..." }]
      "reason": null,                         // set (and verdict "undetermined") when every run was an environment failure
      "medians": { "wall_ms": 6100, "duration_ms": 6000, "jev_ms": 2000, "browser_ms": 1270, "requests": 6, "input_tokens": 8900, "decision_confidence": 0.96, "steps": 5 },
      "passes": 5
    }
  },
  "suite": { "all_pass": true, "verdicts": { "smoke-login": "pass" }, "flaky": [], "undetermined": [], "environment_failures": {} }
}
```

`flaky` is computed from disagreement across repeats, never diagnosed from one run. A run that wrote **no
`trace.json` at all** is an **environment failure**, not an outcome: the runner exited 2 (spec or environment
problem: a missing key, a browser that could not be launched or attached), could not be started, or was killed
before its first observation. Its record has `status: "error"`, `environment_failure: true`, no outcome and
the runner's last stderr lines in `error`; the spec lists it under `environment_failures` and leaves it out of
`outcome_counts`, `agreement`, `medians` and `passes`, so one launch failure among passes does not make the
spec `flaky` (the suite header of `results.md` counts them, and `suite.environment_failures` has the count per
spec). A spec whose every run failed that way is `undetermined` with `reason` saying so. A run that wrote a
trace or result the suite cannot read (killed mid-write) did run: it stays an `undetermined` error run in the
distribution. The exit code is 0 iff `suite.all_pass`, 1 otherwise, 2 when every run of every spec was an
environment failure (or a spec file is missing / two files share an id).

## Reading order

0. `python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --result` — the result above. For a declared
   outcome the verdict is pre-declared; look at `evidence.line`, the screenshot and `path_confidence` to
   sanity-check it. For `undetermined`, start from `reason.suggested_verdict` and read on.
1. `python scripts/summarize_trace.py runs/<id>/<ts>/trace.json` — one line per step, flags on the right.
2. For any flagged or suspicious step: `--step N` dumps it in full (probabilities, checks, the element table
   Jev was offered) and `steps/NNN.png` shows the page Jev decided on (taken after its answer, before the
   action). With the default `screenshots: "key"` only the terminal step and flagged steps (`outcome_seen`,
   `pending_outcome`, `outcome_unconfirmed`, `never_violated`, `low_confidence`, `stale`, `repeat_count ≥ 2`)
   have one; a failed action also leaves `NNN-failed.png`.
   The step *before* a divergence usually has no picture: its element table and probabilities are still in
   the trace, and `--screenshots all` restores a picture per step for a rerun.
3. `steps/final.png` shows where the run ended (always written unless screenshots are off).
4. Only open `trace.json` directly when you need something the above does not show.

## Terminal statuses

| `status` | Meaning | Typical verdict |
|---|---|---|
| `passed` | An outcome with verdict `pass` was seen, survived the settle-and-recheck, and every assertion held | PASS (sanity-check `evidence.line` and `final.png` once) |
| `outcome` | A declared outcome with another verdict was seen; `result.outcome` names it, `result.verdict` is its pre-declared verdict | That verdict. The outcome name is always in the result, so a mislabelled verdict is visible and is a one-line spec fix |
| `assert_failed` | A pass outcome was confirmed but an assertion did not hold on the final page (`result.reason.failed_assertions` has the actual values) | Claude judges: the app is wrong (BUG) or the assertion is (TEST_ISSUE). Never loosen an assertion to get green without saying so |
| `done_unverified` | Jev said DONE confidently; the runner settled, re-observed, and no pass outcome is visible | Either the outcome wording is off (test issue) or the app did not do what it claims (bug). Look at `final.png`. Timing is already ruled out by the recheck |
| `blocked` | Jev chose BLOCKED (`result.reason.blocked_reason` says why) | Usually a test issue: missing `data` value, missing precondition, wrong start page. Sometimes a real bug: the needed control is not rendered |
| `never_violated` | (Runs before the results contract only.) A `never` check crossed its threshold; today this ends as `outcome` with `never_<check>` | Often a product bug. Confirm the error is real in the screenshot, and that the preceding action was reasonable |
| `stuck` | Same action on an unchanged page `max_repeat` times | The action had no effect: dead button (bug), or Jev is confused by the page (test issue: add a note or a `setup` step) |
| `low_confidence` | `max_low_confidence_steps` consecutive uncertain decisions, none of them executed | Jev could not choose between the offered options: look at `decision_confidence` and the probabilities in `--step N`. A split over `type_value` means the `data` key names do not match the field labels (rename them); a split over targets means the goal/notes do not say which of several similar controls to use |
| `budget_exhausted` | Ran out of steps or seconds. The final look is one more step (`final_look: true`): a sighting or DONE on the last step is confirmed by it (then the status is `passed`), a pass first seen there is recorded as `reason.pending_outcome` | Wandering (test issue, tighten the goal) or a very long flow (raise the budget); with `pending_outcome`, one more step would very likely have passed |
| `unstable_page` | `thresholds.max_stale` consecutive decisions were stale: the page changed between the observation and Jev's answer every time, so nothing was executed | Environment: the page never holds still (animation, polling, a slow render). Raise `browser.quiet_ms` / `settle_ms`, or add a `setup` `wait_for` for the thing that keeps changing. Each stale step's `stale` says what moved |
| `error` | Runner, browser or API failure (`trace.error`). `invalid operation answer: <reason>` means Jev's `operation` answer failed validation twice in a row for one step (the step carries `invalid_answer` and `retried`) | Environment issue; rerun before concluding anything |

`trace.pass` is `true` only for `passed`.

## Structure

```jsonc
{
  "spec_id": "search-add-to-cart",
  "status": "passed", "status_meaning": "...", "pass": true, "error": null,
  "outcome": "item_added", "verdict": "pass",  // as in result.json; "result" holds the whole result.json, "outcomes" the effective outcomes (declared + synthesized)
  "adjudication": { "outcome": "item_added", "statement": "...", "line": "Cart: 1 items", "line_id": "3", "present": 0.95, "confidence": 0.9, "latency_ms": 290 },
  "started_at": "...", "ended_at": "...", "duration_ms": 6210,
  "actions_executed": 4,                 // steps that changed the browser (not DONE/STOP, not runner-inserted WAITs)
  "timing": { "launch_ms": 150, "navigation_ms": 2000, "setup_ms": 0, "steps_ms": 2500, "final_ms": 30 },  // where the wall-clock went
  "browser": { "attached": false },      // or { attached: true, cdp_url, storage_state_ignored } when browser.cdp_url was used
  "passed_without_actions": true,        // only present if the start page already satisfied done_when
  "usage": { "jev_requests": 5, "input_tokens": 2100, "output_tokens": 300, "model": "jev-1.13.0",
             "reconnects": 0 },      // reconnects > 0: the kept-alive API connection dropped mid-run and was reopened
  "spec": { ... },                       // the spec as run, secrets replaced by "<secret>"
  "setup": [ { "n": 0, "action": "fill", "selector": "...", "ok": true, "error": null } ],
  "steps": [
    {
      "n": 1, "url": "...", "title": "...", "signature": "7be5a4cf2445",
      "screenshot": "steps/001.png",       // null unless the policy captured this step; "screenshot_after_failure": "steps/001-failed.png" when the action failed
                                           // "screenshot_error": "TimeoutError: ..." when a capture the policy wanted failed (3 s cap; a web font that never loads)
      "elements": [ { "idx": 3, "role": "button", "name": "Add to cart", "x": 116, "y": 151, "w": 79, "h": 21, ... } ],
      "truncated_elements": 0, "visible_text": "first 600 chars of the viewport-first text Jev saw...",
      "offered_operations": ["CLICK", "TYPE_TEXT", "WAIT", "DONE", "BLOCKED"],
      "operation": { "choice": "CLICK", "confidence": 0.91, "top_probabilities": { "CLICK": 0.9, "DONE": 0.05 } },
      "target": { "question": "click_target", "choice": "3", "element": 3, "label": "[3] button \"Add to cart\"",
                  "confidence": 0.88, "top_probabilities": { "3": 0.86, "4": 0.11 } },
      "type_value": { "choice": "search_query", "confidence": 0.95, "top_probabilities": {...} },   // TYPE_TEXT only
      "checks": { "cart_has_item": 0.02, "error_visible": 0.01 },   // evaluated on the page BEFORE the action
      "outcome": { "choice": "none_yet", "confidence": 0.9, "probabilities": { "item_added": 0.03, "app_error": 0.02, "none_yet": 0.95 } },  // the outcome Choice (only when an outcome has a `when`)
      "blocked_reason": { "choice": "nothing", "confidence": 0.9, "top_probabilities": {...} },   // asked every step, consumed for undetermined
      "stuck_reason": { "choice": "control_had_no_effect", ... },    // only after an action with page_changed: false
      "outcome_seen": "app_error",                                   // a non-pass outcome was seen here (terminal with fail_fast)
      "pending_outcome": "item_added",                               // a pass was seen here; executed is a WAIT "confirming outcome ..." and the next step decides
      "outcome_unconfirmed": "item_added",                           // the recheck did not see it again: a transient sighting, the run went on
      "final_look": true,                                            // the one step after the budget ran out: asked only the checks, the outcome and blocked_reason
      "assertions": [ ... ],                                         // on the confirming step: the assert block's results
      "low_confidence": false, "decision_confidence": 0.94, "repeat_count": 1,
      "page_changed": true,                                          // set once the next observation exists: did this step's action change the page signature?
      "never_violated": ["error_visible"],                           // only when a never check fired
      "invalid_answer": "operation: choice 'FLY' was not offered",   // only when an answer failed validation
      "retried": true,                                               // only when the request was re-sent
      "stale": "target [3] changed: disabled",                       // only when the page changed during the decision; nothing was executed
      "executed": { "action": "CLICK", "ok": true, "error": null, "element": 3 },
      "settle": { "ended": "quiet", "ms": 118 },                     // how the post-action wait ended: quiet | options | options_timeout | cap | navigated
      "latency_ms": { "jev": 131, "browser": 640 }
    }
  ],
  "final": { "url": "...", "title": "...", "checks": { "cart_has_item": 0.97 }, "screenshot": "steps/final.png" }  // url and title masked like a step's
}
```

Notes that matter when judging:

- `checks` in step *n* describe the page **before** step *n*'s action. The effect of action *n* shows up in
  step *n+1*'s checks (or in `final.checks`).
- `executed.action` is `AUTO_DONE`, `DONE`, `BLOCKED` or `STOP` on the terminal step; `STOP` means the runner
  stopped for its own reason (`never_violated`, `stuck`, `low_confidence`, `unstable_page`, `error`) and
  `operation.choice` is what Jev *would* have done next.
- `decision_confidence` is the weakest of the operation, target and (for TYPE_TEXT) `type_value` confidences.
  When it is below `min_confidence`, `low_confidence` is true and **nothing was executed**: `executed` is
  `{ "action": "WAIT", "reason": "low confidence; <op> not executed" }`, the runner waits `settle_ms` and
  settles like the WAIT operation (`settle` records how that ended), then observes again. It never acts on a guess.
- `executed.action == "WAIT"` with `reason == "confirming outcome <name>"` (or `"confirming DONE"` when Jev
  chose DONE) means a pass outcome was in sight; the runner waited `settle_ms`, settled and observed again,
  and the next step is the verdict: a pass seen again is confirmed (`executed.confirmed == true`, then the
  assertions run), a DONE without a pass ends `done_unverified`, an auto sighting that vanished is recorded
  as `outcome_unconfirmed` and the run goes on. This absorbs reloads and redirects still in flight when Jev
  declared victory, and costs one extra request per pass.
- A non-pass outcome is terminal at its first sighting (`outcome_seen`, status `outcome`), with the picture
  forced; the outcome Choice's full distribution is on the step, so a near miss is visible too.
- Every Choice answer is validated before it is used: the choice must be one of the keys the question
  offered, every probability key must be offered, values finite in [0, 1] and summing to 1 (± 0.02),
  `confidence` in [0, 1], and the choice must carry the top probability. `invalid_answer` names the
  question and the reason (`"operation: choice 'FLY' was not offered"`; several are joined with `"; "`).
  An invalid or missing `operation` answer makes the runner send the **same** request once more:
  `retried` is true, `latency_ms.jev` is the sum of both round trips, and `checks` and `operation` come
  from the second response. Still invalid → the run ends `error` with `invalid operation answer: <reason>`
  and the step is a `STOP`. An invalid target or `type_value` answer is not retried: `target` is
  `{ "question": ..., "missing": true, "invalid": "<reason>" }` (flag `NO-TARGET-ANSWER`) and the action
  fails safely with `executed.ok == false`. A check whose Noul value is malformed is simply absent from
  `checks` for that step. None of this is evidence about the page; it is evidence about the API answer.
- `stale` means the freshness guard fired: after Jev answered and before anything was executed, the runner
  re-read the identity and meaning of what the decision depends on (for CLICK/TYPE_TEXT/SELECT the target
  node: connected, visible, value, checked, disabled and the text of its form/dialog/row; for DONE, BLOCKED
  and PRESS_ENTER the url, title, text head and every node) and it differed. `executed` is a WAIT with the
  reason, the step is not an action and is not in Jev's `recent_actions`; the loop observed again. Geometry
  is deliberately not compared: animations move boxes without changing meaning, and Playwright resolves
  position at click time. `max_stale` in a row ends the run as `unstable_page`.
- `page_changed` on a step compares the page signature (URL, title, element table, first 500 chars of text)
  the decision was made on with the **next** observation. `false` after a CLICK means the click did nothing
  Jev could see; Jev gets the same flag in `recent_actions`, so a repeated no-op is its mistake, not blindness.
  The terminal step has no `page_changed` (nothing was observed after it).
- `executed.ok == false` means Playwright could not perform the action Jev chose (timeout, detached element).
  One failure is noise; the same failure repeating is a real signal (element not clickable → possible bug).
- `executed.forced == true` means the click needed `force=True` because a transparent overlay intercepted it.
  Worth a look: an invisible layer blocking clicks is a classic UI bug.
- `executed.dispatched == true` means the target was a form control under its own styled box (a hidden
  checkbox input) and the click was dispatched on the control directly. Normal for antd/MUI checkboxes.
- Element indices are re-assigned every step. Never compare `idx` across steps; compare `label`.
- Typed values are never stored; only the `data` key name (`value_key`) is.
- `usage.reconnects` counts the times the client's kept-alive connection to the API died and the request
  was retried on a fresh one. Jev calls are read-only, so a retry is harmless; the number is evidence of an
  unstable network or an API idle timeout, not of anything the page did.
