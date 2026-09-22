# Runner design

Read this when you need to change the runner (new operation, iframe support, a different observation
strategy), not for ordinary test runs.

## Lineage

The step loop follows browser-use/jev-ultrafast, the reference Jev browser agent:

1. **Indexed action space.** Every step, Playwright rebuilds a numbered table of *visible, unoccluded,
   interactive* elements (`observe.py`). Jev chooses indices, never selectors and never free text, so it
   cannot act on something that is not on screen. Indices are fresh each step; elements carry
   `data-jev-idx` so the runner can act on the exact node Jev saw.
2. **Speculative targets, one round trip.** `policy.py` asks `operation` and *every* possible target
   (`click_target`, `type_target` + `type_value`, `select_target`) in the same request. Jev evaluates all
   questions in parallel, so this costs almost nothing extra, and the runner executes only the target that
   matches the chosen operation. Two decisions, one network call. Target options are objects, not lines:
   `{"element": "[4] button \"Login\"", "role", "current_value", "checked", "context", "text"}` with empty
   fields omitted (text fields and selects always carry `current_value`, so "do not re-fill a field that
   already holds the value" is decidable); `type_value` options are `{"key", "value"}` with secrets shown
   as `<secret>`; `select_target` options are `{"element", "option", "current_value"}` keyed `idx:option`.
3. **Only possible operations are offered.** No text field → no TYPE_TEXT. Nothing below the fold →
   no SCROLL_DOWN. PRESS_ENTER only right after a successful TYPE_TEXT. BLOCKED is always available so
   "I can't" is a first-class answer instead of a hallucinated click.
4. **Checks ride along.** The spec's Noul checks are appended to the same request, so verification is free
   and continuous. `done_when` satisfied → the runner stops itself (`auto_done`); a `never` check firing →
   stop with evidence.

What this skill changes relative to jev-ultrafast: there is no text model in the loop at all. jev-ultrafast
uses a small text model to produce values to type; here **Claude prepares every string up front** in
`spec.data` and Jev only chooses among them (`type_value`). That keeps the inner loop 100% typed, keeps
secrets out of any model that does not need them, and turns a missing value into a clean `BLOCKED` escalation.

## Files

| File | Role |
|---|---|
| `scripts/spec.py` | Defaults, `${ENV}` substitution, validation. CLI validates a spec |
| `scripts/observe.py` | The injected JS that builds the element table and the freshness fingerprint: `observe`, `fingerprint`, `compare_fingerprint`, `mask_secrets`, `signature` (and `element_label` for trace labels) |
| `scripts/policy.py` | State + question construction, strict answer validation, target resolution |
| `scripts/rules.py` | The optional standing rules (`"rules": true`) and the measurement that made them opt-in |
| `scripts/jev_client.py` | Stdlib HTTP client for `POST /v1/systemone`: one persistent connection per run (reconnects and retries once if the socket was dropped; Jev calls are read-only), 429/5xx backoff, usage counters; honours `https_proxy` / `no_proxy` like urllib |
| `scripts/run_test.py` | The loop, setup steps, action execution, stop conditions, the results contract (outcome sightings, confirmation, assertions, adjudication), trace and result writing |
| `scripts/summarize_trace.py` | Summary table, `--step N` dump, `--result` |
| `scripts/run_suite.py` | Specs × repeats as `run_test.py` subprocesses on a thread pool; `aggregate_spec` (outcome distribution, agreement, unanimous verdict or `flaky`), `suite_verdict`, `results.json` + `results.md`; exit 0 iff all unanimously pass |
| `scripts/report.py` | `render_report(trace, result, images)`: one self-contained `report.html` per run, screenshots inline as base64; given a suite directory, `suite_run_dirs` resolves the relative paths of its `results.json` and renders every run that has a trace |
| `scripts/bench.py` | Runs a spec N times as subprocesses and reports medians; every number in the docs comes from its `--json` output |
| `scripts/selftest.py` | Offline end-to-end test with local pages and a rule-based fake Jev |
| `scripts/unit_tests.py` | Stdlib `unittest` for the pure parts: client, validation, criteria, fingerprint compare, masking, bench |

`run_test.run(spec, jev, out_dir)` accepts any object with `system_one(state, questions)` and
`usage_summary()`, which is how the self-test swaps Jev for a fake. Keep that seam when refactoring.

## Stop conditions (in the order they are evaluated each step)

time budget → observe → ask Jev (re-ask once if the `operation` answer fails validation) → a non-pass
outcome seen (fail_fast → `outcome`) → a pending pass confirmed (`passed` / `assert_failed`) or not
(`done_unverified` after Jev's DONE; carry on after an auto sighting) → a pass outcome seen (`auto_done` →
WAIT, recheck next step) → invalid `operation` after the retry (`error`) → low-confidence streak →
freshness guard (stale → WAIT and re-observe; `max_stale` in a row → `unstable_page`) → DONE (→ WAIT,
recheck next step) / BLOCKED chosen → repeat detection (`stuck`) → execute → settle → next step.

## The results contract

`spec.effective_outcomes()` gives the runner the outcomes it works with: the declared ones, or, when none
are declared, `goal_reached` (requires `done_when`, verdict pass) and `never_<check>` (verdict bug, at
`never_true`) synthesized from the old-style fields (design §5.1). Every step `policy.build_questions` adds one
`outcome` Choice over the outcomes that have a `when` plus `none_yet` (asked only when at least one has a
`when`; a Choice *compares* mutually exclusive endings, where independent Nouls can all read 0.85 at once
or one can sit at 0.78 for steps), a `blocked_reason` Choice (always, phrased without a conditional), and a
`stuck_reason` Choice after an action with `page_changed: false`. `policy.seen_outcomes` decides what the
page shows: probability ≥ `outcome_true` (for a `when`) and every `requires` check ≥ its threshold.

A pass sighting (or Jev's DONE) is a `pending` confirmation: the step is a WAIT (`settle_ms`, then settle),
the next observation decides. Confirmed → `run_test.check_assertions` evaluates the `assert` block in code
on the final page (`url_matches` glob, `text_contains` on `body.innerText`, `field_value` by label,
`element_present` / `element_absent` by role and name substring over a whole-document observation, not the
viewport table) → `passed`, or `assert_failed` with the actual values (masked). Not confirmed →
`done_unverified` after DONE, `outcome_unconfirmed` and carry on after an auto sighting. A non-pass outcome
ends the run at first sighting with its picture forced (today's `fail_fast` asymmetry: a vanishing error
toast is still an error). Preference when several are seen on one page: non-pass over pass, declaration
order. When the budget ends, the final look is one more terminal step (`final_look: true`, asked only the
check and outcome questions): it confirms a sighting or a DONE made on the last step, ends a non-pass
outcome under the same `fail_fast` rule, and records a pass first seen there as `pending_outcome` under
`budget_exhausted` (no recheck happened, so it is not a pass; the next run gets one more step). Every
runner-inserted WAIT (pending confirmation, low confidence, stale decision) goes through one `park()`
helper; only the stale one skips the `settle_ms` pause, because the page is already moving and the
event-based settle is what waits for it to stop.

After a seen outcome one adjudication request (`policy.build_adjudication`) sends the terminal page's visible
text as up to 200 numbered lines with the outcome's statement (`observe.LINES_JS`: one line per block, the
lines in the viewport first, the same visibility rules as the observation, masked like it); `evidence_line`
selects the line that states it (or `none`) and `evidence_present` re-judges the statement. Code copies the
selected line verbatim into `result.evidence.line`: Jev cannot quote text, so selection is how a quote is
produced. A failed adjudication (transport, a non-JSON body, a malformed answer) is recorded, never fatal.

`run_test.build_result` writes `result.json` (references/trace-format.md): outcome, verdict, note,
probability, confidence, seen_at_step, confirmed, `path_confidence` (the weakest executed decision),
evidence, assertions, story, and for `undetermined` a `reason` with the typed answers of the terminal step
and `policy.suggested_verdict`'s table lookup (`stuck_reason` for `stuck`, `blocked_reason` for `blocked` /
`stuck` / `low_confidence` / `budget_exhausted`, else the status row: for `done_unverified`, `assert_failed`,
`unstable_page` and `error` the step's `blocked_reason` is about progress, not the verdict). `trace.outcome` /
`trace.verdict` repeat the headline and `trace.result` the whole file, so a trace alone is enough.

**Freshness guard.** Jev decides on an observation, but the page may move on while it decides. Before
executing, `observe.fingerprint()` re-reads what the observation recorded, without re-tagging: url, title,
the first 500 chars of visible text, and for every tagged node `[connected, visible, value, checked,
disabled, hash of its form/dialog/row/item text]`. `compare_fingerprint()` checks only the target node
(plus url) for CLICK / TYPE_TEXT / SELECT, and everything for DONE / BLOCKED / PRESS_ENTER; SCROLL and WAIT
never go stale. The same JS helpers produce the tuples at both times. Identity and meaning, not geometry:
animations move boxes without changing what a control means, and Playwright's actionability checks resolve
geometry and hit-testing at click time anyway. A stale decision executes nothing (`step.stale` has the
reason, `executed` is a WAIT), is not an action and is not shown to Jev as one; mutations are never retried.

Repeat detection keys on `(page signature, operation, target, value_key)`; a WAIT is never counted (choosing
it again on a page that still says "Loading..." is right for as long as the page loads: a 5 s loader ended
`stuck` after 1.5 s before this rule), so a page that never finishes loading ends with the budget, and
`result.reason.stuck_reason` then carries the last `still_loading`. The signature hashes URL, title,
the element table and the first 500 chars of visible text, so a page that changes only far below the fold
can look "unchanged"; that is intentional, since Jev could not see the change either.

## Extending

- **New operation** (e.g. `GO_BACK`, `HOVER`): add its description to `OPERATION_DESCRIPTIONS`, decide when
  it is offered in `build_questions`, execute it in `run_test.execute`. If it needs a target, add a
  `<op>_target` Choice and map it in `resolve_target`.
- **iframes**: `observe.py` only sees the main frame. To include frames, run `OBSERVE_JS` per
  `page.frames` and prefix indices with a frame id; the locator in `execute` must then be built from the
  matching `frame.locator(...)`.
- **Richer state**: add fields to `build_state`. The state is an object with a descriptive name for every
  part (`goal`, `hints`, `step {n, max}`, `page {url, title}`, `elements` as records with `index`, `role`,
  `label`, `value`, `checked`, `context` and the `operations` each element can be the target of,
  `truncated_elements`, `visible_text`, `available_data_values` as `{key, value}` with secrets masked, and
  `recent_actions`: the last 10 history entries `{step, operation, target, value_key, ok, page_changed}`).
  `page_changed` compares the page signature the action was decided on with the next observation, so Jev
  can see that its own click did nothing. `policy.element_operations` is the single place that decides which
  elements are targets, for both the state and the target questions. Keep the state small; Jev's answers get
  *less* reliable when it is padded with irrelevant text.
- **Score questions**: not used in the loop today. They fit "how far along is the flow" style rubrics; add
  them to `build_questions` and record them in the step like `checks`.
- **Bigger option sets**: if the API rejects a Choice with too many criteria, lower
  `observation.max_elements`, or split `click_target` by role (links vs buttons) and ask both speculatively.

## Known limits

Main frame only; no file uploads, drag-and-drop, canvas, or hover-only menus; no shadow DOM piercing
beyond what `querySelectorAll` reaches; one tab (new tabs opened by the page are not followed). All of
these are also outside jev-ultrafast's current scope. Put such steps in `setup` with plain Playwright when
they are preconditions rather than the thing under test.

## Observer: three passes, viewport-first text

The table keeps up to `observation.max_elements` (default 200; a Choice takes at most 255 options) sorted
top-to-bottom, left-to-right; the rest is reported as `truncated_elements` and cannot be chosen. The
`visible_text` Jev sees is **viewport-first**: a TreeWalker over the text nodes collects those that
intersect the viewport in document order, then the rest of the page, cut to `max_text_chars` (default
4000). `body.innerText` from the top let a long header and navigation crowd out the toast the checks were
looking for. The fingerprint's text head is the first 500 chars of the same text, computed by the same
helper, and `signature()` hashes the same 500 chars.

Pass 1 collects semantic controls (tags, ARIA roles, `[onclick]`, focusable `tabindex`). A form control
at `opacity: 0` is **kept** if it still has a real box: that is the antd/MUI/Bootstrap "hidden input under
a styled box" pattern, and the input is the thing to click. The occlusion test accepts the control's own
styled box (its label, or a sibling in the same wrapper) as non-occluding. Pass 2 offers a `<label>` as
the checkbox/radio it controls when the input itself is parked offscreen. Pass 3 walks the body (capped at
8,000 nodes) for elements whose computed `cursor` is `pointer`, keeping only the outermost of each pointer
chain (cursor inherits) and skipping anything nested in a pass-1 control; this surfaces React-style
clickables that carry no role (an avatar menu, a card, a table row). A `<label>` whose control is already
in the table is skipped here: it adds nothing but a tempting no-op click (measured: with the structured
state Jev clicked "Username" before typing into it). Anonymous controls get a `context`
(the text of their row / list item / label) so `checkbox ""` in a table reads
`checkbox "" in "SKU-1005 Gadget 6-pack Acme Ltd"`. Pass 4 does the same for **identical labels**: a group of
elements sharing role and name with no context (one "Add to cart" per product card, one "Edit" per entry,
when the containers are plain `div`s) climbs its ancestors level by level and takes the first level whose
texts tell every member apart, so the table reads `button "Add to cart" in "Sauce Labs Bolt T-Shirt …"`
instead of six times `button "Add to cart"` (measured on such a grid: target probabilities 0.47 / 0.21 /
0.18, three refused decisions, `low_confidence`, and a story a human could not read either). A shared price
bar is not enough, the card with its title is; a group that nothing distinguishes gets no context. Each
element records `via: "semantic" | "label" | "cursor"`.

Executing a click on a control that something sits on top of dispatches the click on the control itself
(`executed.dispatched`), because a forced pointer click lands on the styled box and is swallowed; other
intercepted clicks still fall back to `force=True` (`executed.forced`).

Known blind spots: canvas content (maps, charts) has no elements at all; a clickable element with no
role, no handler attribute and no pointer cursor. Both need a `setup` step.

## Settle: event-based, capped

`run_test.settle()` runs after every action, setup step and the initial navigation. It is not a fixed
pause: `domcontentloaded` (short timeout, ignored on failure), then a page-side promise that resolves once
two animation frames have passed **and** the DOM has had no mutation for `browser.quiet_ms` (a
`MutationObserver` on the document), capped at `browser.settle_ms`. After TYPE_TEXT into a
`combobox`/`searchbox` (explicit roles, `<input type=search>` and `<input list>`) it also waits, up to
200 ms, for a visible `[role=option]` that was not already showing when the wait began, so Jev is not asked
for a decision before the autocomplete suggestions arrive and a listbox elsewhere on the page (or the
previous query's suggestions) cannot end the wait early. If the evaluate throws because the document
navigated meanwhile, it is retried once on the new document. The result lands on the step as
`settle: {ended: quiet | options | options_timeout | cap | navigated, ms}`: a run full of `cap` endings
means the page never goes quiet (animations, polling) and the cap is what you are paying; raise
`quiet_ms` only if observations come back before the app has rendered. The WAIT operation sleeps
`settle_ms` and then settles normally.

## Rules

`scripts/rules.py` holds standing rules Jev can get with every question as structured `instructions`
(spec `"rules": true`): `operation` carries `{"goal", "rules": NEXT_ACTION}`, the target questions
`{"goal", "operation", "rules": [NEXT_ACTION, TARGET]}`, `type_value` `{"goal", "operation": "TYPE_TEXT",
"rules": [NEXT_ACTION, VALUE]}`, and each check Noul `{"statement", "rules": CHECK}`. The wording is adapted
from jev-ultrafast for a loop with prepared values (TYPE_TEXT means picking one of `available_data_values`;
a missing value means BLOCKED, never an unrelated value), and the untrusted-page-text guard is in both
`NEXT_ACTION` and `CHECK`.

**They are off by default because the measurement said so.** On the demo login page three of the four
wordings tried (full, light, only the two guard sentences) lowered the `operation` decision's median
confidence from 0.95 to 0.50–0.57; the fourth (without the BLOCKED sentences) kept 0.97 on `smoke-login` but
took two extra no-op steps and broke the bad-password spec (`low_confidence` 2/3, `budget_exhausted` 1/3).
In every variant the bad-password spec hesitated between TYPE_TEXT and BLOCKED, because the page's own
text hints at the right password, and the CHECK rule pulled a borderline check under its threshold. Without
rules the same runs pass at 0.94–0.99. The per-variant numbers are in
`docs/superpowers/measurements/2026-09-22-track1-ab-*.json`. Turn them on per spec when an app shows the
failure modes they address (repeated no-op actions, page text steering Jev) and measure with `bench.py`.

The target questions name their premise ("If the next operation is CLICK, …"); the implicit phrasing was
measured too and tied, so the premise stays named, as in jev-ultrafast.

## Answer validation

Jev's answers are data from a network service and the runner acts on them, so nothing is trusted before
it is checked. `build_questions` returns in `meta["offered"]` the keys each Choice question offered, and
`policy.validate_choice` accepts an answer only if `choice` is one of them, every probability key is one
of them, the values are finite in [0, 1] and sum to 1 (± 0.02), `confidence` is finite in [0, 1], and the
chosen key carries the top probability (within 1e-6). Missing fields are invalid; a bool is not a number.
`resolve_target` runs that check before it turns a choice into an element index, so `int()` never sees an
unvalidated string, and `type_value` is checked against the spec's `data` keys the same way.

An invalid or missing `operation` answer is not a decision: the loop re-sends the same state and
questions once (Jev calls are read-only, so this cannot double-act) and reads checks and operation from
the second response; a second failure ends the run as `error`. Invalid target or `type_value` answers are
not retried: the reason is recorded in `step.invalid_answer` and the action fails safely through the
missing-target path. Noul checks whose value is not a finite number in [0, 1] are dropped from
`step.checks`; the absent key is the signal. `read_choice` without `offered` keeps a lenient, shape-only
parse for reading traces and ad-hoc tools; the loop always passes `offered`.

## Confidence gate and DONE confirmation

Jev's `confidence` is the signal that makes the loop safe to run unattended, so the runner treats it as
data, not decoration. The gate takes the weakest of the operation, target and `type_value` confidences;
below `min_confidence` the decision is **not executed**, the step is recorded as a WAIT with a reason, and
the streak counter advances. This came from a real run where Jev split 0.68/0.32 over which value to type
into a Password field and the old runner typed the wrong one. Two consequences: a low-confidence DONE is
never terminal (a real run stopped at 0.36 mid-reload), and an undecided answer on an unchanged page ends
the run after `max_low_confidence_steps` with a status that tells Claude exactly what to fix.

A *confident* DONE with `done_when` unsatisfied gets one settle-and-recheck (a `settle_ms` pause, then
`settle()`) before the verdict. Reloads and redirects are often still in flight when Jev declares
victory; the recheck turned a 3-of-4 flaky spec into a stable one without touching the spec.
