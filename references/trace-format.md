# Trace format

Every run writes `trace.json` (plus `steps/NNN.png` screenshots) into its output directory. The trace is
the *evidence*; the summary (`scripts/summarize_trace.py`) is the fast way to read it.

## Reading order

1. `python scripts/summarize_trace.py runs/<id>/<ts>/trace.json` — one line per step, flags on the right.
2. For any flagged or suspicious step: `--step N` dumps it in full (probabilities, checks, the element table
   Jev was offered) and `steps/NNN.png` shows what the page looked like *before* that decision.
3. `steps/final.png` shows where the run ended.
4. Only open `trace.json` directly when you need something the above does not show.

## Terminal statuses

| `status` | Meaning | Typical verdict |
|---|---|---|
| `passed` | All `done_when` checks ≥ threshold, no `never` fired | PASS (sanity-check the screenshots once) |
| `done_unverified` | Jev said DONE confidently; the runner settled, re-observed, and `done_when` is still not satisfied | Either the check wording is off (test issue) or the app did not do what it claims (bug). Look at `final.png`. Timing is already ruled out by the recheck |
| `blocked` | Jev chose BLOCKED | Usually a test issue: missing `data` value, missing precondition, wrong start page. Sometimes a real bug: the needed control is not rendered |
| `never_violated` | A `never` check crossed its threshold | Often a product bug. Confirm the error is real in the screenshot, and that the preceding action was reasonable |
| `stuck` | Same action on an unchanged page `max_repeat` times | The action had no effect: dead button (bug), or Jev is confused by the page (test issue: add a note or a `setup` step) |
| `low_confidence` | `max_low_confidence_steps` consecutive uncertain decisions, none of them executed | Jev could not choose between the offered options: look at `decision_confidence` and the probabilities in `--step N`. A split over `type_value` means the `data` key names do not match the field labels (rename them); a split over targets means the goal/notes do not say which of several similar controls to use |
| `budget_exhausted` | Ran out of steps or seconds | Wandering (test issue, tighten the goal) or a very long flow (raise the budget) |
| `error` | Runner, browser or API failure (`trace.error`). `invalid operation answer: <reason>` means Jev's `operation` answer failed validation twice in a row for one step (the step carries `invalid_answer` and `retried`) | Environment issue; rerun before concluding anything |

`trace.pass` is `true` only for `passed`.

## Structure

```jsonc
{
  "spec_id": "search-add-to-cart",
  "status": "passed", "status_meaning": "...", "pass": true, "error": null,
  "started_at": "...", "ended_at": "...", "duration_ms": 6210,
  "actions_executed": 4,                 // steps that changed the browser (not DONE/STOP, not runner-inserted WAITs)
  "passed_without_actions": true,        // only present if the start page already satisfied done_when
  "usage": { "jev_requests": 5, "input_tokens": 2100, "output_tokens": 300, "model": "jev-1.13.0",
             "reconnects": 0 },      // reconnects > 0: the kept-alive API connection dropped mid-run and was reopened
  "spec": { ... },                       // the spec as run, secrets replaced by "<secret>"
  "setup": [ { "n": 0, "action": "fill", "selector": "...", "ok": true, "error": null } ],
  "steps": [
    {
      "n": 1, "url": "...", "title": "...", "signature": "7be5a4cf2445",
      "screenshot": "steps/001.png",
      "elements": [ { "idx": 3, "role": "button", "name": "Add to cart", "x": 116, "y": 151, "w": 79, "h": 21, ... } ],
      "truncated_elements": 0, "visible_text": "first 600 chars...",
      "offered_operations": ["CLICK", "TYPE_TEXT", "WAIT", "DONE", "BLOCKED"],
      "operation": { "choice": "CLICK", "confidence": 0.91, "top_probabilities": { "CLICK": 0.9, "DONE": 0.05 } },
      "target": { "question": "click_target", "choice": "3", "element": 3, "label": "[3] button \"Add to cart\"",
                  "confidence": 0.88, "top_probabilities": { "3": 0.86, "4": 0.11 } },
      "type_value": { "choice": "search_query", "confidence": 0.95, "top_probabilities": {...} },   // TYPE_TEXT only
      "checks": { "cart_has_item": 0.02, "error_visible": 0.01 },   // evaluated on the page BEFORE the action
      "low_confidence": false, "decision_confidence": 0.94, "repeat_count": 1,
      "never_violated": ["error_visible"],                           // only when a never check fired
      "invalid_answer": "operation: choice 'FLY' was not offered",   // only when an answer failed validation
      "retried": true,                                               // only when the request was re-sent
      "executed": { "action": "CLICK", "ok": true, "error": null, "element": 3 },
      "latency_ms": { "jev": 131, "browser": 640 }
    }
  ],
  "final": { "url": "...", "title": "...", "checks": { "cart_has_item": 0.97 }, "screenshot": "steps/final.png" }
}
```

Notes that matter when judging:

- `checks` in step *n* describe the page **before** step *n*'s action. The effect of action *n* shows up in
  step *n+1*'s checks (or in `final.checks`).
- `executed.action` is `AUTO_DONE`, `DONE`, `BLOCKED` or `STOP` on the terminal step; `STOP` means the runner
  stopped for its own reason (`never_violated`, `stuck`, `low_confidence`) and `operation.choice` is what Jev
  *would* have done next.
- `decision_confidence` is the weakest of the operation, target and (for TYPE_TEXT) `type_value` confidences.
  When it is below `min_confidence`, `low_confidence` is true and **nothing was executed**: `executed` is
  `{ "action": "WAIT", "reason": "low confidence; <op> not executed" }`. The runner never acts on a guess.
- `executed.action == "WAIT"` with `reason == "confirming DONE"` means Jev chose DONE while `done_when` was
  unsatisfied; the next step's checks are the verdict and carry `executed.confirmed == true`. This absorbs
  reloads and redirects still in flight when Jev declared victory.
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
