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
  "confirmed_by": "recheck",                                    // "assertions": every assertion held on the sighting page (spec.confirm "assert"); "recheck": a settle, a second observation and Jev again
                                                                //   (also when Jev chose DONE before the pass was in sight, so the sighting happened on the checking step); null unless confirmed
  "path_confidence": 0.89,                                      // the weakest executed decision on the way: report the least certain judgment
  "reason": null,                                               // for undetermined: see below
  "evidence": { "line": "Your password is invalid!",            // the page line Jev selected in the adjudication request (verbatim), or null
                "present": 0.94,                                // the adjudication's Noul over the outcome statement
                "screenshot": "steps/005.png",                  // the sighting step's picture (forced for non-pass outcomes), else steps/final.png
                "checks": { "logged_in": 0.03, "login_error": 0.81 } },   // the checks at the sighting step; with spec evidence "failures", a pass whose
                                                                // assertions held has line null and "skipped": why the line was not asked
  "assertions": [ { "url_matches": "**/login", "ok": true, "actual": "https://.../login" } ],   // every assertion with what was found
  "outcomes_seen_earlier": [],                                  // non-terminal sightings: non-pass ones (fail_fast: false) and pass sightings that vanished on their recheck ({.., "unconfirmed": true})
  "story": [ "1 TYPE_TEXT [0] textbox \"Username\" <- username", "2 TYPE_TEXT [1] textbox \"Password\" <- password", "3 CLICK [2] button \"Login\"" ],
  "announcements": [ { "step": 6, "text": "Successfully Saved", "kind": "live", "tone": "success" } ],   // every toast / live message of the run, with the step whose observation it preceded
  "run_stamp": "tj4x2ka7",                                       // what ${RUN_STAMP} became in this run (the data it created carries it); null when the spec has none
                                                                 // (dates: trace.spec.run_date is the day ${DATE...} counted from, trace.spec.dates what each placeholder became; null without one)
  "status": "passed", "duration_ms": 6200,
  "usage": { "jev_requests": 5, "input_tokens": 9774, "output_tokens": 1741, "model": "jev-1.13.0", "reconnects": 0 },
  "trace": "runs/smoke-login-badpw/20260922-101500/trace.json",
  "diagnostics": { "counts": { "page_errors": 1, "console_errors": 0, "failed_requests": 0, "http_errors": 2, "server_errors": 1 },   // only when the browser reported something:
                   "page_errors": [ { "text": "TypeError: x is undefined", "step": 4 } ],                    //   uncaught exceptions, 5xx responses and failed requests, five of each at most
                   "server_errors": [ { "status": 500, "method": "POST", "url": ".../api/save", "resource": "fetch", "step": 4 } ] },   //   (4xx responses and console errors are in trace.diagnostics)
  "teardown": { "ok": true, "steps": 3, "ran": 3 },             // only for a spec with `teardown`; on a failure ok false and "failed": { "n", "action", "error" }. Never changes the result
  "via": { "action": { "type": "Search" }, "executed_at_step": 2, "target": "[3] textbox \"Search\"", "effect": false, "waited_ms": 10072, "then": "CLICK [22] link \"Suppliers\"" },   // only for a spec with `via`. executed_at_step null: the control was never used. effect true: the page answered (with "changed": ["controls", "text"], "effect_at_step", "answered_after_ms"); false: nothing but the control itself changed, and `then` is what the run wanted to do instead (the ending is then outcome via_no_effect); null with "not_judged": no conclusion (a scroll came first, or the page was still loading when the control was used)
  "expected": { "expect": { "outcome": "bad_credentials" }, "actual": { "outcome": "bad_credentials" },   // only when the spec declares `expect`:
                "matched": true, "mismatches": {} },                                                     // did the run end in the declared result?
  "batch": { "fields_typed": 2, "stopped": [ { "step": 5, "reason": "the page's text changed after a field was typed ...", "fields_left": 1 } ] },   // only with batch_fields
  "replay": { "path": ".jev/paths/shop-checkout.json", "used": true,      // only with replay on (spec `replay`, --replay). used: a saved path was read
              "steps_in_path": 8, "steps_replayed": 8, "steps_by_jev": 0,  //   saved steps, how many ran without a request, executed actions Jev chose
              "handed_back": null,                                         //   or { "at_step": 4, "path_step": 4, "reason": "the page's fields and buttons differ ..." }
              "resumed": [],                                               //   after a handover: [{ "at_step": 4, "path_step": 4 }] where Jev's own action was the saved step and the path went on
              "waited_ms": 12, "verified_by": "jev",                       //   time spent waiting for saved steps' pages; how the ending was decided ("jev" | "assertions")
              "saved": false, "save_note": "the saved path was replayed to its end and stands" }   // also "not_used" (why no path was read) and,
                                                                           //   for a red after saved steps, "note": run it once more with --no-replay
}
```

`outcome: "undetermined"` means no declared outcome was seen: the loop ended `stuck | blocked |
low_confidence | done_unverified | budget_exhausted | unstable_page | error`, or a pass outcome was seen but
an assertion failed (`assert_failed`). Then `reason` is `{ "status", "blocked_reason", "stuck_reason",
"suggested_verdict" }` plus `failed_assertions` (with `actual` values) and `outcome_seen` for
`assert_failed`, `pending_outcome` for a `budget_exhausted` whose final look saw a pass for the first time, `assertions_at_last_look`
with `last_look_step` for a `done_unverified` whose confirmation looks evaluated the assertions (the whole list as
last evaluated, held or not)
(not rechecked, so not a pass: give the run one more step), `hints` for a stalled run whose last page keeps controls
the observer was not asked to look at (an unlisted `<iframe>`, shadow DOM turned off, a file field without `files`: the
sentences the summary prints as `hint:`; with `control_not_on_page` they turn the suggestion into `test_issue` and
`suggestion_from` reads `"hints"`), and `error` for `error`; an `error` whose `phase` is
`navigation` or `setup` never observed the page (the start URL did not load within `browser.navigation_timeout_ms`,
or a setup step failed): it is not a verdict (suggested `flaky` for navigation, `test_issue` for setup), the runner
exits 2 and a suite lists it as an environment/setup failure. `blocked_reason` is Jev's answer on the terminal step (asked there, in one follow-up request, and on the
final look; not on ordinary steps) to "what most prevents progress" (`nothing | missing_data_value | control_not_on_page | site_refused_or_error |
human_step_required | wrong_page | other`); `stuck_reason` is asked only after an action with
`page_changed: false` (`control_had_no_effect | overlay_or_modal | still_loading |
needs_scroll_or_other_control | other`). The suggestion comes from a fixed table: `stuck_reason` counts for
`stuck`, for a `budget_exhausted` spent on a streak of WAITs, and for a `blocked` chosen right after an action
that changed nothing when `blocked_reason` has no row of its own (`other`, `nothing`); `blocked_reason` for
`blocked`, `stuck`, `low_confidence` and `budget_exhausted` (a typed reason with a row wins over the status
row there); for `done_unverified`, `assert_failed`, `unstable_page` and `error`
the status row alone decides, because on those endings the step's `blocked_reason` is about progress on the
page, not about the verdict:

| reason or status | suggested verdict |
|---|---|
| `missing_data_value`, `wrong_page`, `low_confidence`, `budget_exhausted` | TEST_ISSUE |
| `control_not_on_page`, `control_had_no_effect`, `overlay_or_modal`, `site_refused_or_error` | BUG |
| `human_step_required` | NEEDS_HUMAN |
| `still_loading`, `unstable_page`, `error` | FLAKY |
| `done_unverified`, `assert_failed`, `other`, `nothing`, `needs_scroll_or_other_control` | none: Claude judges from the trace |

Exit codes: 0 ⇔ verdict `pass` (status `passed`), or for a spec with `expect` ⇔ `expected.matched`; 1 for
every other outcome and for `undetermined`; 2 for a spec or environment problem (no result is written), and for a
run that ended before its first observation (`reason.phase`; a result *is* written then).

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
  "hosts": { "www.saucedemo.com": { "limit": 2, "peak": 2, "specs": 4 } },   // per host: runs allowed at once, the most it saw, its specs
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
      "agreement": 1.0,                       // share of the observed runs that ended in the most common VERDICT (two pass endings agree)
      "outcome_agreement": 1.0,               // the same over outcome names
      "expected_matched": null,               // for a spec with `expect`: how many observed runs ended in the declared result
      "verdict": "pass",                      // one verdict everywhere -> it; undetermined everywhere -> "undetermined"; a spec with `expect` -> "expected" when every run matched; else "flaky"
      "environment_failures": [],             // runs that wrote no trace, or ended before their first observation (phase navigation / setup): [{ "run": 2, "exit_code": 2, "error": "..." }]
      "reason": null,                         // set (and verdict "undetermined") when every run was an environment failure
      "medians": { "wall_ms": 6100, "duration_ms": 6000, "jev_ms": 2000, "browser_ms": 1270, "requests": 6, "input_tokens": 8900, "decision_confidence": 0.96, "steps": 5 },
      "replay": null,                         // with --replay: { "full": runs that walked their path to its end, "handed_back", "rerun_without": red after saved
                                              //   steps and run again without the path (each such run has "replay_attempt": the first run, and "replay_disagreed"), "disagreed" }
      "passes": 5
    }
  },
  "suite": { "all_pass": true, "verdicts": { "smoke-login": "pass" }, "flaky": [], "undetermined": [], "environment_failures": {} }
}
```

`flaky` is computed from disagreement of **verdicts** across repeats, never diagnosed from one run: two
runs that ended in two different `pass` outcomes agree, a declared outcome and an `undetermined` do not. A run
that wrote **no `trace.json` at all**, or whose result says `reason.phase` (`navigation`: the start URL never
loaded; `setup`: a scripted step failed), is an **environment/setup failure**, not an outcome: the runner exited
2, could not be started, or was killed before its first observation. Its record has `status: "error"`,
`environment_failure: true` (and `phase` when known), no outcome and the error in `error`; the spec lists it
under `environment_failures` and leaves it out of
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
   `pending_outcome`, `outcome_unconfirmed`, `never_violated`, `low_confidence`, `stale`, `repeat_count ≥ 2`,
   `outcome_deferred`, `after_no_effect`) have one; a failed action also leaves `NNN-failed.png`. The step after
   an action flagged `NO-EFFECT` (`page_changed: false` on a click, a typed value, a select) always has a
   picture: it shows the page the action failed to change.
   The step *before* a divergence usually has no picture: its element table and probabilities are still in
   the trace, and `--screenshots all` restores a picture per step for a rerun.
3. `steps/final.png` shows where the run ended (always written unless screenshots are off).
4. Only open `trace.json` directly when you need something the above does not show.

## Terminal statuses

| `status` | Meaning | Typical verdict |
|---|---|---|
| `passed` | An outcome with verdict `pass` was seen, survived the settle-and-recheck, and every assertion held | PASS (sanity-check `evidence.line` and `final.png` once) |
| `outcome` | A declared outcome with another verdict was seen; `result.outcome` names it, `result.verdict` is its pre-declared verdict | That verdict. The outcome name is always in the result, so a mislabelled verdict is visible and is a one-line spec fix |
| `assert_failed` | A pass outcome was confirmed but an assertion did not hold on the final page (`result.reason.failed_assertions` has the actual values). A pass sighted while the page was still busy (covered controls, an empty document before the app renders, or changed during the pause) is looked at again first, twice at most, and while the page stays busy for as long as `navigation_timeout_ms` (`assertions_pending`, `recheck_again`, `recheck_waited_ms`) | Claude judges: the app is wrong (BUG) or the assertion is (TEST_ISSUE). Never loosen an assertion to get green without saying so. If the last steps carry `RECHECK:n ASSERT-PENDING` on a busy page, the page took longer than `navigation_timeout_ms` to settle: raise it, or `settle_ms` on a page that kept changing |
| `done_unverified` | Jev said DONE confidently; the runner settled, re-observed (again while the page kept changing between looks or stayed busy, covered controls or an empty document, `recheck_again` on those steps, twice at most, and while the page stays busy for as long as `navigation_timeout_ms`), and no pass outcome is visible; `reason.assertions_at_last_look` (with `last_look_step`) is the assertions as evaluated on the last look that had a pass in sight, which held and which did not yet | Either the outcome wording is off (test issue) or the app did not do what it claims (bug). Look at `final.png`. Timing is ruled out by the recheck unless the last two steps still carry `recheck_again`: then the page never held still, raise `settle_ms` |
| `blocked` | Jev chose BLOCKED (`result.reason.blocked_reason` says why; right after a click that changed nothing, `reason.stuck_reason` says why that was) | Usually a test issue: missing `data` value, missing precondition, wrong start page. Sometimes a real bug: the needed control is not rendered, or a control that does nothing (`stuck_reason: control_had_no_effect` → BUG) |
| `never_violated` | (Runs before the results contract only.) A `never` check crossed its threshold; today this ends as `outcome` with `never_<check>` | Often a product bug. Confirm the error is real in the screenshot, and that the preceding action was reasonable |
| `stuck` | Same action on an unchanged page `max_repeat` times. A WAIT is not an action: waiting on a page that keeps loading never ends `stuck`, only the budget bounds it | The action had no effect: dead button (bug), or Jev is confused by the page (test issue: add a note or a `setup` step) |
| `low_confidence` | `max_low_confidence_steps` consecutive uncertain decisions, none of them executed | Jev could not choose between the offered options: look at `decision_confidence` and the probabilities in `--step N`. A split over `type_value` means the `data` key names do not match the field labels (rename them); a split over targets means the goal/notes do not say which of several similar controls to use |
| `budget_exhausted` | Ran out of steps or seconds. The final look is one more step (`final_look: true`): a sighting or DONE on the last step is confirmed by it (then the status is `passed`), a pass first seen there is recorded as `reason.pending_outcome`. When the budget went on a streak of WAITs, `reason.stuck_reason` carries the last reason Jev gave for the no-op (`still_loading`) | Wandering (test issue, tighten the goal) or a very long flow (raise the budget); with `pending_outcome`, one more step would very likely have passed; with `stuck_reason: still_loading` the page never finished loading (flaky: rerun, then raise the budget or suspect the app) |
| `unstable_page` | `thresholds.max_stale` consecutive decisions were stale: the page changed between the observation and Jev's answer every time, so nothing was executed | Environment: the page never holds still (animation, polling, a slow render). Raise `browser.quiet_ms` / `settle_ms`, or add a `setup` `wait_for` for the thing that keeps changing. Each stale step's `stale` says what moved |
| `error` | Runner, browser or API failure (`trace.error`). `invalid operation answer: <reason>` means Jev's `operation` answer failed validation twice in a row for one step (the step carries `invalid_answer` and `retried`). With `trace.failed_before_observation` (`result.reason.phase`) the start URL never loaded or a setup step failed: no step exists, exit 2 | Environment issue; rerun before concluding anything. A `phase: setup` is the spec's selector or wait, never the app |

`trace.pass` is `true` only for `passed`.

## Structure

```jsonc
{
  "spec_id": "search-add-to-cart",
  "status": "passed", "status_meaning": "...", "pass": true, "error": null,
  "outcome": "item_added", "verdict": "pass",  // as in result.json; "result" holds the whole result.json, "outcomes" the effective outcomes (declared + synthesized)
  "adjudication": { "outcome": "item_added", "statement": "...", "line": "Cart: 1 items", "line_id": "3", "present": 0.95, "confidence": 0.9, "merged": true },
  //   "merged": the evidence questions rode in the confirming step's request (a pass: no extra round trip; the step has "adjudication_merged": true);
  //   a bug outcome seen at first sighting gets its own request instead: "latency_ms": 290, "usage": { "input_tokens": 720, "output_tokens": 60 }
  //   a statement of several sentences (split on ". ", "; ", ", and ") adds "sentences": [{ "sentence", "line_id", "line", "confidence" }, …],
  //   one Choice per sentence in the same request; "line" / "line_id" / "confidence" are those of the most confident sentence that found a line
  "started_at": "...", "ended_at": "...", "duration_ms": 6210,
  "actions_executed": 4,                 // steps that changed the browser (not DONE/STOP, not runner-inserted WAITs)
  "timing": { "launch_ms": 150, "navigation_ms": 2000, "setup_ms": 0, "steps_ms": 2500, "final_ms": 30,   // where the wall-clock went
              "login_ms": 2400,              // only for a spec with `login`: its steps (about 0 when a saved session was reused); setup_ms is then the rest
  //  "login": [ ... ] beside "setup": the login steps as they ran (empty when a session was reused);
  //  "session": { "reused": true, "age_s": 340 } with session reuse on: or { "reused": false, "not_reused": "no saved session yet", "saved": true },
  //             and "expired": true when a saved session was tried and the application no longer accepted it (also result.session);
  //  "browser.http_cache": "slot-0" with browser.http_cache: the cache profile the run used
              "teardown_ms": 900,            // only for a spec with `teardown`
              "jev_connect_ms": 460 },       // the TCP + TLS handshake to the API, paid in the background while the browser launched
  "failed_before_observation": "navigation", // only when the start URL never loaded ("navigation") or a setup step failed ("setup"): no steps, exit 2
  "expected": { "expect": {...}, "matched": true, ... },  // only for a spec with `expect` (the same record as result.expected)
  "browser": { "attached": false },      // or { attached: true, cdp_url, storage_state_ignored } when browser.cdp_url was used;
                                         // with browser.device also "device": "iPhone 13" and the "viewport" it brought
  "diagnostics": { "counts": {...}, "page_errors": [...], "console_errors": [...], "failed_requests": [...], "http_errors": [...] },
                                         // only when the browser reported something: every entry (fifty a kind at most; counts are complete), masked like
                                         //   page text, each with the "step" whose observation first followed it. http_errors: { status, method, url, resource };
                                         //   failed_requests: { method, url, resource, failure }; page_errors / console_errors: { text, url? }
  "passed_without_actions": true,        // only present if the start page already satisfied done_when
  "observation_retries": 1,              // only when > 0: observations that raced a navigation ("Execution context was destroyed") and were retried on the new document
  "usage": { "jev_requests": 5, "input_tokens": 2100, "output_tokens": 300, "model": "jev-1.13.0",
             "reconnects": 0 },      // reconnects > 0: the kept-alive API connection dropped mid-run and was reopened
  "spec": { ... },                       // the spec as run, secrets replaced by "<secret>"
  "setup": [ { "n": 0, "action": "fill", "selector": "...", "ok": true, "error": null } ],   // "frame" when the step named one; "files" for an upload; "scripts_ms" when the step waited for the page's scripts before it ran (the first step that touches a page after it opened)
  "teardown": [ ... ], "teardown_result": { "ok": true, "steps": 3, "ran": 3 },   // the teardown's steps in the same shape, and result.teardown
  "steps": [
    {
      "n": 1, "url": "...", "title": "...", "signature": "7be5a4cf2445",
      "screenshot": "steps/001.png",       // null unless the policy captured this step; "screenshot_after_failure": "steps/001-failed.png" when the action failed
                                           // "screenshot_error": "TimeoutError: ..." when a capture the policy wanted failed (3 s cap; a web font that never loads)
      "elements": [ { "idx": 3, "role": "button", "name": "Add to cart", "x": 116, "y": 151, "w": 79, "h": 21, ... } ],
      "truncated_elements": 0, "visible_text": "first 600 chars of the viewport-first text Jev saw...",
      "covered_controls": 3,                                         // only when > 0: controls on screen but under another layer (a loading overlay, a dialog), counted, not offered; Jev sees the count in its state; flag COVERED:3
      "layer_controls": 0,                                           // with covered_controls: how many offered controls belong to the covering layer (a dialog's buttons, an open list's options); 0 is a blank layer, a loading or saving overlay (run_test.blank_layer); flag COVERED:3(layer:2) when > 0
      "loading_indicators": 1,                                       // only on an undecided (low-confidence) step, when > 0: spinners, indeterminate progress bars and 'Loading...' lines that cover nothing, counted when the decision came back: such a page gets the extra looks a blank layer gets, and nothing else (flag LOADING-IND)
      "outcome_held": { "outcome": "no_records", "loading_indicators": 1, "held_ms": 0 },   // a non-pass outcome seen while the page said it was loading: not taken as the ending, the step is a wait (flag HELD:no_records); held_ms since the first hold, never past navigation_timeout_ms
      "via": true,                                                   // the action the spec's `via` names was executed on this step (flag VIA)
      "via_deferred": { "why": "5 request(s) in flight", "waited_ms": 36738 },   // Jev chose the via action while the page was still loading: waited for without a request, then decided again (flag VIA-WAIT)
      "via_no_effect": { "since_step": 2, "waited_ms": 10072 },      // a look after the via action on which nothing but the control itself has changed (flag VIA-NO-EFFECT, a key picture); on the terminal step also "then"
      "via_effect": { "of_step": 2, "changed": ["controls", "text"] },   // the first look on which the page differs from the one the via action was used on (flag VIA-ANSWERED)
      "via_awaited": "not executed yet",                             // beside outcome_deferred: a pass seen before the via action was executed, or before the page answered it
      "frames": [ { "selector": "#card-frame", "elements": 2, "label": "Secure card payment", "url": "..." } ],   // with observation.frames: what each listed <iframe> contributed to the table, or "skipped": why not; its elements carry "frame" and a context "frame: <label>"
      "iframes": 1, "shadow_hosts": 1,                              // only when > 0: visible <iframe>s, and elements whose shadow root holds controls (not offered): what the hints of a stalled run read (the summary's `hint:` lines, `result.reason.hints`)
      "diagnostics": { "page_errors": 1, "http_errors": 1, "server_errors": 1 },   // only when the browser reported something since the previous observation (flags JS-ERROR, HTTP-5xx, HTTP-4xx, REQ-FAILED, CONSOLE-ERR)
      "new_tab": { "followed": true, "url": "..." },                // on the step whose action opened a tab; followed only with browser.follow_new_tabs (flags NEW-TAB / NEW-TAB(not followed))
      "loading_options": 1,                                          // only when > 0: autocomplete rows that only say 'Searching....' / 'Loading...': not offered, the suggestions are on their way (run_test.page_loading); flag LOADING:1
      "recheck_again": 1,                                            // a confirmation look (after a pass sighting or DONE) that found the page changed during the pause with no pass visible: it parked and looked again (1, then 2; CONFIRM_RECHECKS_MAX; two more on a busy page, and on a busy page for as long as navigation_timeout_ms, can_recheck); flag RECHECK:1
      "recheck_waited_ms": 3500,                                     // with recheck_again: the confirmation's waits so far (settle_ms x 2, 4, 4, ...), the figure a busy page's looks run against navigation_timeout_ms
      "assertions_pending": [ { "url_matches": "**/x", "ok": false, "actual": "..." } ],  // a pass in sight on a page still busy (covered controls, an empty document, or changed during the pause) whose assertions do not hold yet: parked again instead of assert_failed; flag ASSERT-PENDING:1
      "offered_operations": ["CLICK", "TYPE_TEXT", "WAIT", "DONE", "BLOCKED"],
      "operation": { "choice": "CLICK", "confidence": 0.91, "top_probabilities": { "CLICK": 0.9, "DONE": 0.05 } },
      "target": { "question": "click_target", "choice": "3", "element": 3, "label": "[3] button \"Add to cart\"",
                  "confidence": 0.88, "top_probabilities": { "3": 0.86, "4": 0.11 } },
      "type_value": { "choice": "search_query", "confidence": 0.95, "top_probabilities": {...} },   // TYPE_TEXT only
      "upload_file": { "choice": "cv", "confidence": 0.95, "top_probabilities": {...} },             // UPLOAD_FILE only: which of the spec's `files`; executed then carries "file_key" and "file" (the name)
      "checks": { "cart_has_item": 0.02, "error_visible": 0.01 },   // evaluated on the page BEFORE the action
      "outcome": { "choice": "none_yet", "confidence": 0.9, "probabilities": { "item_added": 0.03, "app_error": 0.02, "none_yet": 0.95 } },  // the outcome Choice (only when an outcome has a `when`)
      "blocked_reason": { "choice": "missing_data_value", ... },   // only on the terminal step of blocked / stuck / low_confidence (a follow-up request) and on the final look
      "reason_request": true,                                        // that follow-up was sent for this step; its latency is in latency_ms.jev
      "stuck_reason": { "choice": "control_had_no_effect", ... },    // only after an action with page_changed: false
      "outcome_seen": "app_error",                                   // a non-pass outcome was seen here (terminal with fail_fast)
      "pending_outcome": "item_added",                               // a pass was seen here; executed is a WAIT "confirming outcome ..." and the next step decides
      "outcome_unconfirmed": "item_added",                           // the recheck did not see it again: a transient sighting, the run went on
      "final_look": true,                                            // the one step after the budget ran out: asked only the checks, the outcome and blocked_reason
      "outcome_deferred": ["not_reordered"],                         // an outcome true of the page whose requires_action (no action yet) or after (the named action not executed yet) holds it back: recorded, not a verdict
      "announcements": [ { "text": "Successfully Saved", "kind": "live", "tone": "success", "ms_before_observation": 2140 } ],
      //   toasts and ARIA live messages that appeared between the previous observation and this one (observe.ANNOUNCE_INIT_JS reports them as they
      //   appear, so a toast gone before the runner looked is here); kind = alert | status | log | live (aria-live) | toast (a toast-like class name),
      //   tone = success | error | warning | info when the class names say; also on the history entry of the last executed action ("announced":
      //   [texts]) and in Jev's state for this and the next two steps; flag ANNOUNCED:"…"
      "action_deferred": { "operation": "TYPE_TEXT", "covered": 9, "loading": 0 },  // a CLICK / TYPE_TEXT / SELECT below thresholds.covered_action_confidence while 9 controls sat under a blank layer (or, covered 0, while `loading` autocomplete rows said the suggestions were loading): not executed, executed is a runner WAIT (settle_ms x 1, 2, 4, 4, 4 by "deferrals") ending when the page changes; flag DEFERRED-TYPE_TEXT:9, DEFERRED-CLICK:loading
      "deferrals": 2,                                                // with action_deferred: the k-th deferral on this page signature, deferral_limit (max_low_confidence_steps + 2) at most
      "deferrals_exhausted": 5,                                      // this action was executed on a page still under its blank layer, after that many deferrals there: the layer is the page now; flag DEFER-LIMIT:5
      "no_effect": true,                                             // this step's executed CLICK/TYPE_TEXT/SELECT/PRESS_ENTER changed nothing (page_changed false): flag NO-EFFECT
      "after_no_effect": true,                                       // this observation is the page the previous action failed to change (a key-mode picture)
      "adjudication_merged": true,                                   // the confirming step: the evidence questions rode in this request (state.lines added)
      "fill": { "3": { "choice": "last_name", "confidence": 0.97 }, "4": { "choice": "leave_empty", "confidence": 0.91 } },   // with batch_fields, on a TYPE_TEXT step
                                                                     //   of a page with several empty fields: Jev's answer per field (by element index)
      "batch_planned": [ { "field": "textbox \"Last Name\"", "value_key": "last_name", "confidence": 0.97 } ],   // the fields the runner will type next without asking
      "batched": true,                                               // this TYPE_TEXT was one of them: no request (operation / target / type_value carry the assignment's
                                                                     //   confidence and "batched": true; flag BATCHED)
      "batch_stopped": "a list of suggestions opened",               // the page reacted to what was typed: the rest of the batch was dropped and Jev decided (flag BATCH-ENDED)
      // "settle": { "ended": "network", "ms": 412, "network": { "requests": 2, "ms": 340 } } with browser.settle "network": the action's requests were waited
      //   for (how many were in flight, for how long); "left": n when some were still in flight at the cap (ended "cap")
      "at_ms": 2392,                                                 // when this page was observed, in ms from the start of the run
      "replayed": true, "replay_waited_ms": 0,                       // with replay: this action came from the saved path, no request (operation / target / type_value carry
                                                                     //   "replayed": true and no confidence; the summary shows `saved path`); how long the step waited for its page
      "replay_waited_for": "button \"Save\" is not on the page",     // with replay_waited_ms > 0: what the page lacked on the last look before the step applied
      "replay_handback": "the page's fields and buttons differ ...", // the step where the saved path stopped applying and Jev took over, and why (flag REPLAY-ENDED)
      "replay_resumed": true,                                        // Jev decided this step after a handover and chose what the saved step says: the next step is the path's again (flag REPLAY-RESUMED)
      "replay_verify": true,                                         // the look that decides a replayed run's ending: checks, outcome and evidence line, no operation
                                                                     //   (flag REPLAY-VERIFY); "replay_final_mismatch": why the page is not the one the recorded run ended on
      "assertions": [ ... ],                                         // on the confirming step: the assert block's results
      "low_confidence": false, "decision_confidence": 0.94, "repeat_count": 1,
      //   an undecided step (low_confidence true) is not executed: "low_streak" counts consecutive undecided steps on one page signature (the run ends
      //   low_confidence at thresholds.max_low_confidence_steps; a page change restarts it), and its executed is a runner WAIT with "wait_ms" (settle_ms x 1, 2, 4)
      //   and "wait" like a chosen WAIT's, ending as soon as the page changes
      "page_changed": true,                                          // set once the next observation exists: did this step's action change the page signature?
      "never_violated": ["error_visible"],                           // only when a never check fired
      "invalid_answer": "operation: choice 'FLY' was not offered",   // only when an answer failed validation
      "retried": true,                                               // only when the request was re-sent
      "stale": "target [3] changed: disabled",                       // only when the page changed during the decision; nothing was executed
      "executed": { "action": "CLICK", "ok": true, "error": null, "element": 3 },
      //   "slow_navigation": { "ended": "navigated", "ms": 9640, "action_timeout_ms": 8000 } when the action landed but the navigation it started outlasted action_timeout_ms (flag SLOW-NAV:9.6s; Jev's history says ok)
      //   a WAIT's executed carries "wait_ms", its ceiling (a WAIT chosen again on an unchanged page: settle_ms x 1, 2, 4, then 4; "wait_streak" on the step),
      //   and "wait": { "ended": "changed" | "timeout" | "navigated", "ms": 412 }: the WAIT ended as soon as the page's fingerprint changed, else at the ceiling
      "settle": { "ended": "quiet", "ms": 118 },                     // how the post-action wait ended: quiet | options | options_timeout | cap | navigated
      "latency_ms": { "jev": 131, "browser": 640 },
      "usage": { "input_tokens": 1450, "output_tokens": 210 }  // this step's request's tokens; a retry or the reason follow-up adds to it
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
  declared victory; the confirming request also carries the evidence questions (`adjudication_merged`), so a
  pass costs one extra request in all, not two.
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
- `executed.slow_navigation` means the action was performed and only the navigation it started was outstanding
  when `action_timeout_ms` ran out (Playwright's log: "click action done", then "waiting for scheduled navigations
  to finish"); the runner waited for the page (the rest of `navigation_timeout_ms`; `ended` says how the wait ended,
  `ms` the action's total) and Jev's history says the action landed. A slow host, not a failure; the same field on
  a `setup` click record. Live: OrangeHRM's demo answering a module page in 9-12 s.
- `executed.forced == true` means the click needed `force=True` because a transparent overlay intercepted it.
  Worth a look: an invisible layer blocking clicks is a classic UI bug.
- `executed.dispatched == true` means the target was a form control under its own styled box (a hidden
  checkbox input) and the click was dispatched on the control directly. Normal for antd/MUI checkboxes.
- Element indices are re-assigned every step. Never compare `idx` across steps; compare `label`.
- Typed values are never stored; only the `data` key name (`value_key`) is.
- `usage.reconnects` counts the times the client's kept-alive connection to the API died and the request
  was retried on a fresh one. Jev calls are read-only, so a retry is harmless; the number is evidence of an
  unstable network or an API idle timeout, not of anything the page did.
