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
   matches the chosen operation. Two decisions, one network call (~100–500 ms).
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
| `scripts/observe.py` | The injected JS that builds the element table; `render_table`, `signature` |
| `scripts/policy.py` | State + question construction, strict answer validation, target resolution |
| `scripts/jev_client.py` | Stdlib HTTP client for `POST /v1/systemone`: one persistent connection per run (reconnects and retries once if the socket was dropped; Jev calls are read-only), 429/5xx backoff, usage counters; honours `https_proxy` / `no_proxy` like urllib |
| `scripts/run_test.py` | The loop, setup steps, action execution, stop conditions, trace writing |
| `scripts/summarize_trace.py` | Summary table and `--step N` dump |
| `scripts/selftest.py` | Offline end-to-end test with a local page and a rule-based fake Jev |

`run_test.run(spec, jev, out_dir)` accepts any object with `system_one(state, questions)` and
`usage_summary()`, which is how the self-test swaps Jev for a fake. Keep that seam when refactoring.

## Stop conditions (in the order they are evaluated each step)

time budget → observe → ask Jev (re-ask once if the `operation` answer fails validation) → `never`
violated (fail_fast) → `done_when` satisfied (`auto_done`) → invalid `operation` after the retry (`error`) →
DONE / BLOCKED chosen → repeat detection (`stuck`) → low-confidence streak → execute → settle → next step.

Repeat detection keys on `(page signature, operation, target, value_key)`. The signature hashes URL, title,
the element table and the first 500 chars of visible text, so a page that changes only far below the fold
can look "unchanged"; that is intentional, since Jev could not see the change either.

## Extending

- **New operation** (e.g. `GO_BACK`, `HOVER`): add its description to `OPERATION_DESCRIPTIONS`, decide when
  it is offered in `build_questions`, execute it in `run_test.execute`. If it needs a target, add a
  `<op>_target` Choice and map it in `resolve_target`.
- **iframes**: `observe.py` only sees the main frame. To include frames, run `OBSERVE_JS` per
  `page.frames` and prefix indices with a frame id; the locator in `execute` must then be built from the
  matching `frame.locator(...)`.
- **Richer state**: add fields to `build_state`. Keep it small; Jev's answers get *less* reliable when the
  state is padded with irrelevant text, and the element table already carries most of the signal.
- **Score questions**: not used in the loop today. They fit "how far along is the flow" style rubrics; add
  them to `build_questions` and record them in the step like `checks`.
- **Bigger option sets**: if the API rejects a Choice with too many criteria, lower
  `observation.max_elements`, or split `click_target` by role (links vs buttons) and ask both speculatively.

## Known limits

Main frame only; no file uploads, drag-and-drop, canvas, or hover-only menus; no shadow DOM piercing
beyond what `querySelectorAll` reaches; one tab (new tabs opened by the page are not followed). All of
these are also outside jev-ultrafast's current scope. Put such steps in `setup` with plain Playwright when
they are preconditions rather than the thing under test.

## Observer: three passes

Pass 1 collects semantic controls (tags, ARIA roles, `[onclick]`, focusable `tabindex`). A form control
at `opacity: 0` is **kept** if it still has a real box: that is the antd/MUI/Bootstrap "hidden input under
a styled box" pattern, and the input is the thing to click. The occlusion test accepts the control's own
styled box (its label, or a sibling in the same wrapper) as non-occluding. Pass 2 offers a `<label>` as
the checkbox/radio it controls when the input itself is parked offscreen. Pass 3 walks the body (capped at
8,000 nodes) for elements whose computed `cursor` is `pointer`, keeping only the outermost of each pointer
chain (cursor inherits) and skipping anything nested in a pass-1 control; this surfaces React-style
clickables that carry no role (an avatar menu, a card, a table row). Anonymous controls get a `context`
(the text of their row / list item / label) so `checkbox ""` in a table reads
`checkbox "" in "1000-05-1100L Residual 1100L Nile Bakery"`. Each element records
`via: "semantic" | "label" | "cursor"`.

Executing a click on a control that something sits on top of dispatches the click on the control itself
(`executed.dispatched`), because a forced pointer click lands on the styled box and is swallowed; other
intercepted clicks still fall back to `force=True` (`executed.forced`).

Known blind spots: canvas content (maps, charts) has no elements at all; a clickable element with no
role, no handler attribute and no pointer cursor. Both need a `setup` step.

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

A *confident* DONE with `done_when` unsatisfied gets one settle-and-recheck (`settle()` plus
`2 × settle_ms`) before the verdict. Reloads and redirects are often still in flight when Jev declares
victory; the recheck turned a 3-of-4 flaky spec into a stable one without touching the spec.
