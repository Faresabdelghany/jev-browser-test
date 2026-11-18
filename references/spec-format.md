# Spec format

A spec is the contract Claude writes before a run. It is a JSON file; `scripts/spec.py <file>` validates
it without opening a browser. Unknown fields are ignored; every optional field has a default.

## Minimal example

```json
{
  "id": "search-add-to-cart",
  "start_url": "https://shop.example.com/",
  "goal": "Search for 'blue hoodie', open the first result and add it to the cart.",
  "data": { "search_query": "blue hoodie" },
  "checks": {
    "cart_has_item": "The header or cart widget shows the cart contains at least one item",
    "error_visible": "An error message, stack trace or 'something went wrong' text is visible"
  },
  "done_when": ["cart_has_item"],
  "never": ["error_visible"]
}
```

## With the results contract

The same flow, saying which endings Claude will accept back and what must be exactly true at the end:

```json
{
  "id": "search-add-to-cart",
  "start_url": "https://shop.example.com/",
  "goal": "Search for 'blue hoodie', open the first result and add it to the cart.",
  "data": { "search_query": "blue hoodie" },
  "checks": {
    "cart_has_item": "The header or cart widget shows the cart contains at least one item",
    "error_visible": "An error message, stack trace or 'something went wrong' text is visible"
  },
  "outcomes": {
    "item_added":   { "when": "The cart widget shows one item and the product name",  "verdict": "pass" },
    "out_of_stock": { "when": "The product page says the item is out of stock or unavailable",
                      "verdict": "needs_human", "note": "stock is data, not code: check the catalogue" },
    "app_error":    { "when": "An error message, stack trace or 'something went wrong' text is visible",
                      "verdict": "bug" }
  },
  "assert": [
    { "url_matches": "**/cart*" },
    { "text_contains": "Blue Hoodie" },
    { "element_present": { "role": "button", "name": "Checkout" } },
    { "element_absent":  { "role": "alert" } }
  ]
}
```

- **`outcomes`** — the mutually exclusive endings, each a statement about the visible page (`when`, the same
  discipline as checks) and the verdict Claude will give if it is seen: `pass`, `bug`, `test_issue` or
  `needs_human`. Optional `requires` lists check names that must also be ≥ `check_true` (keeps a conjunction
  decomposed into atomic Nouls while the Choice does the discrimination); optional `note` is copied into the
  result for Claude. Every step Jev answers one Choice over the outcomes plus `none_yet`; an outcome is
  *seen* when its probability is ≥ `thresholds.outcome_true` and its `requires` hold. A **pass** must survive
  a settle-and-recheck and then every assertion; any **other verdict is terminal at first sighting** (a
  vanishing error toast is still an error). Write outcomes from the acceptance criteria (pass) and from the
  wrong behaviour you are testing for or the ticket reports (bug); a negative test (wrong password, invalid
  input) declares the rejection as its `pass` outcome and the success as the `bug`, with a `note` saying so.
  A `when` may name a **toast** ("A green toast says 'Successfully Saved'", "A red toast says 'Failed to Submit'"):
  toasts and ARIA live messages (`role=alert|status|log`, `aria-live`, or a class naming a toast / snackbar / growl /
  flash) are recorded the moment they appear, whether or not they are still on screen when the runner next looks,
  and Jev sees them in `state.announcements` (with the step they preceded, for three observations) and is told they
  count as shown; the evidence line then reads `live message: Successfully Saved`. Live: a Leave flow's decisive
  facts were exactly such toasts, gone before every observation.
  **`requires_action: true`** on an outcome defers it until at least one action has been executed: a statement
  such as "the list is still in its original order" or "the dropdown still shows Name (A to Z)" is true of the
  untouched start page too, and without the flag the run would end `bug` at step 1 with zero actions. The
  deferred sighting is recorded on the step (`outcome_deferred`, flag `DEFERRED:<name>`, a picture in key mode)
  and the run goes on. Use it on every bug outcome that describes "nothing happened"; leave it off when the
  outcome is legitimately decided on the start page (a menu entry missing on load).
  **`after`** names the action an outcome only means something after: `"after": {"click": "Search"}` defers it
  until an executed CLICK targeted a control whose label contains "Search" (case-insensitive; `type` for TYPE_TEXT,
  `select` for SELECT; several keys all have to have happened). Measured live: a Leave List's 'No Records Found'
  outcome fired on the unfiltered list before Search was clicked although the filter checks in its `requires` read
  0.82 and 0.88, because a check is a probability about the page, not a record of what was done. Deferred sightings
  are recorded like `requires_action`'s (`outcome_deferred`, flag `DEFERRED:<name>`).
- **`assert`** — exact expectations checked **in code** on the final observation, free and non-model, the
  "DONE is never proof" verifier: `url_matches` (Playwright's URL glob, the same dialect as `setup.wait_for.url`:
  `**` anything, `*` anything but `/`, `{a,b}` either, everything else literal, `?` included), `text_contains`
  (substring of the whole page text), `text_in` (`{selector, contains}` or `{selector, equals}`: the text
  **inside the elements a CSS selector matches**, which is how a notification is asserted on a page whose body
  copy also mentions its wording: a page-wide `text_contains "Action successful"` is true on every load of a page
  that lists that string as an example; `text_in {"selector": "#flash", "contains": "Action successful"}` is true
  only when the notification says it), `text_order` (a list of at least two strings that must appear in the page
  text in that order, each found after the previous one: the order of a sorted list, a table or a menu; anchor
  on strings that occur once), `field_value` (`{label, equals}`: a text field or select whose **accessible name**
  contains `label`, case-insensitive; the name comes from its `<label>`, `aria-label` or placeholder),
  `element_present` / `element_absent` (`{role, name?}`, `name` a case-insensitive substring). The element
  assertions look at the **whole document**, not only at the viewport-and-hit-tested table Jev chooses from,
  so a Logout link below the fold is present. Values are compared against the real page and the recorded
  `actual` is masked, so a `secrets` value can be asserted on. A failed assertion makes the run `undetermined`
  with reason `assert_failed` and the actual values, for Claude to decide whether the assertion or the app is wrong.
- **`expect`** — for a spec whose *correct* result is not a pass: a demo account documented as broken, a known
  defect kept as a regression test until it is fixed. `{"outcome": "form_error"}` or `{"outcome": "undetermined",
  "status": "blocked", "stuck_reason": "control_had_no_effect"}` (any of `outcome`, `status`, `verdict`,
  `blocked_reason`, `stuck_reason`, `suggested_verdict`) declares the ending the run should reach. The runner
  still reports the real outcome; `result.expected` says whether it matched, the exit code is 0 when it did,
  and `run_suite.py` gives the spec the verdict **`expected`** (green in `all_pass`) when every repeat matched,
  so an expected-red spec can sit in a suite gate and go red only when the behaviour changes. Do not use it to
  paper over a failing test: a bug you want fixed stays red without `expect` (red before the fix, green after).
- **Compatibility.** Without `outcomes`, the runner synthesizes `goal_reached` (verdict `pass`, requires
  `done_when`) and one `never_<check>` per `never` check (verdict `bug`, at `never_true`), so an old spec
  keeps its meaning and gains a `result.json`; a fired `never` check now ends with status `outcome` and
  `outcome: never_<check>`. With `outcomes` declared they are the whole contract: `done_when` and `never`
  are ignored (a lone `never` Noul would otherwise race the outcome Choice at its own threshold and could end
  a negative test as `bug`), and `outcomes` must then include a `pass` verdict. `checks` stay as **progress**
  signals (where did the run diverge).

## Fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `id` | string | required | Folder-safe name; runs land in `runs/<id>/<timestamp>/` |
| `start_url` | string | required | Where the browser opens. Supports `${ENV_VAR}` |
| `goal` | string | required | What a tester would be told to do. One flow, plain language, names the visible outcome |
| `notes` | string | `""` | Hints Jev sees every step ("dismiss the cookie banner first", "the product grid loads lazily"). Keep them about the page and the flow: a sentence about the test itself ("this spec is expected to be red") is read by Jev as a hint about the page and measurably lowers its confidence in the right decision |
| `comment` | string | none | Free text for humans (why the spec exists, what it documents). Never sent to Jev, kept in the trace's copy of the spec |
| `data` | object | `{}` | Every string Jev may type, by name. Jev picks the name, never writes text. Values support `${ENV_VAR}`, `${RUN_STAMP}` and `${DATE...}` |
| `${RUN_STAMP}` | placeholder | fresh per run | Anywhere in the spec (`data`, `goal`, `notes`, outcome `when`s, `assert`, `setup` values): one value per run, eight lowercase letters and digits (the epoch second in base 36 plus two random characters), so data the application keeps is unique across runs, repeats and parallel workers without anyone exporting a variable. `RUN_STAMP` in the environment wins over a fresh one (export it to rerun, or clean up after, one run's data). Recorded as `result.run_stamp` and `trace.spec.run_stamp`; `null` when the spec never mentions it |
| `${DATE...}` | placeholder | the day of the run | Anywhere in the spec, like `${RUN_STAMP}`: a date counted from the day of the run, written the way the application wants it, so a spec that types a date does not go red the day a literal one has passed. `${DATE}` is today as `yyyy-mm-dd`. After `DATE` come **terms**, applied left to right: `+30d` / `-7d` (days later / earlier), `+wed` / `-wed` (`mon` … `sun`: on to the next, or back to the last, such weekday; a day that already is one stays), `+workday` / `-workday` (on to the next, or back to the last, working day of the spec's `calendar`). Then an optional **`:format`**: `yyyy` `yy`, `mm` `m`, `dd` `d`, `mmmm` `mmm` (December, Dec), `dddd` `ddd` (Wednesday, Wed), every other character kept. `${DATE+2d+workday:yyyy-dd-mm}`, `${DATE+1d:dd/mm/yyyy}`, `${DATE+30d+wed:dddd d mmmm yyyy}`. A placeholder that cannot be read is a spec problem (exit 2), never text for the page; `${DATE_FROM}` and other names stay environment variables. `RUN_DATE=yyyy-mm-dd` in the environment is the day they count from (to rerun with an earlier run's dates). `spec.py` prints what each one becomes today; the trace has `spec.run_date` and `spec.dates` |
| `calendar` | object | Monday to Friday, no holidays | What `+workday` / `-workday` call a working day: `workweek`, the days people work (`["sun", "mon", "tue", "wed", "thu"]`), and `holidays`, the days the application under test treats as non-working, each `"mm-dd"` (every year) or `"yyyy-mm-dd"` (that year only). Copy the application's own list: a leave or booking form refuses a holiday the way it refuses a Sunday. Read by the date placeholders only, never sent to Jev |
| `secrets` | list | `[]` | Names in `data` whose values must never appear in the trace or in the state sent to Jev. Shown as `<secret>` in `available_data_values`, and masked again in every observation (a secret typed into a plain text field or a contenteditable reads back as `<secret>`, not as the value). Masking replaces **every occurrence**, so a value shorter than 6 characters after `${ENV}` substitution (`1`, `2024`, `admin`) also rewrites unrelated page text Jev decides on; `spec.py` and the runner print a warning on stderr for it (exit code unchanged): use a longer test credential, or leave a non-confidential value out of `secrets` |
| `files` | object | `{}` | Files Jev may attach, by name: `{"cv": "fixtures/cv.pdf"}` (paths relative to the directory you run from; `${ENV_VAR}` allowed). Declaring any offers the operation `UPLOAD_FILE` wherever the page has a file field, one the page hides behind a button included: Jev picks the field and the name, the runner sets the file, and only the file's name reaches Jev. A missing file is exit 2 |
| `extra_operations` | list | `[]` | Operations beyond the standing set, offered only when listed. `["HOVER"]`: Jev may move the pointer over a link, button, tab or menu item to open a menu that only shows on hover, then click what it reveals. Off by default because every operation offered is one more choice on every step; `--hover` on `run_test.py` adds it for a run |
| `setup` | list | `[]` | Deterministic Playwright steps run **before** Jev takes over (see below) |
| `teardown` | list | `[]` | Deterministic steps run **after the verdict**, whatever it was: delete the record the flow created, log out (the same actions as `setup`, see below). Best effort: a failing step is reported in `result.teardown` and never changes the outcome, the verdict or the exit code |
| `checks` | object | `{}` | `name -> statement` evaluated as a Noul (0–1) against the page at every step |
| `done_when` | list | `[]` | Check names that must all be ≥ `thresholds.check_true` for the synthesized `goal_reached` pass outcome. Required when no `outcomes` are declared; ignored when they are |
| `never` | list | `[]` | Check names that end the run as the synthesized `never_<check>` outcome (verdict `bug`) at `thresholds.never_true`. Ignored when `outcomes` are declared |
| `outcomes` | object | `{}` | `name -> {when, verdict, requires?, requires_action?, after?, note?}`: the endings the run may return, see above. Names are identifiers; `none_yet` and the reserved question names are not allowed |
| `assert` | list | `[]` | Exact expectations checked in code on the final page before a pass counts, see above (`url_matches`, `text_contains`, `text_in`, `text_order`, `field_value`, `element_present`, `element_absent`), and two that read what the browser recorded during the run instead: `{"no_page_errors": true}` (no uncaught JavaScript exception) and `{"no_failed_requests": true}` (no request failed outright, no 5xx response), see "Browser diagnostics" below |
| `expect` | object | none | The result an expected-red spec should end in (`outcome`, `status`, `verdict`, `blocked_reason`, `stuck_reason`, `suggested_verdict`), see above. Exit 0 and suite verdict `expected` when it matches |
| `auto_done` | bool | `true` | Start the confirmation as soon as a pass outcome is seen, even if Jev has not chosen DONE (false: only Jev's DONE starts it) |
| `confirm` | `"assert"` \| `"recheck"` | `"assert"` | How a pass sighting is confirmed. `"assert"`: when the spec has an `assert` block and every assertion already holds on the page the pass was seen on, that is the confirmation, at once and in code (`result.confirmed_by: "assertions"`; the evidence line then costs one request). Otherwise, and always with `"recheck"`, the runner pauses `settle_ms`, observes again and asks Jev once more, with the evidence questions riding in that request (`confirmed_by: "recheck"`). Measured on the demo login `"assert"` saves ~0.5 s a pass; use `"recheck"` for a flow that can show a late error after its success, or write an assertion on the stable state. A success toast that vanishes is not a reason: toasts are captured as `announcements` as they appear and stay in Jev's state for three observations, so an outcome anchored on one survives the recheck |
| `evidence` | `"always"` \| `"failures"` | `"always"` | When the evidence line is asked. `"always"`: for every declared outcome. `"failures"`: not for a pass whose assertions all hold; the assertions, each with the value found, are then the proof, `result.evidence.line` is null with `evidence.skipped` saying why, and the run makes one Jev request fewer (one of five on the demo login). A pass with no assertions, a pass whose assertions fail and every outcome that is not a pass still get their line. `--evidence failures` on `run_test.py` sets it for a run: meant for a regression suite that is green most days, not for a ticket, which wants the page's own words |
| `batch_fields` | bool | `false` | One request per form. On a page with two or more empty text fields, the request that decides the next action also asks, per field, which data value belongs in it (or none); after a TYPE_TEXT the runner types the other fields Jev assigned at `thresholds.batch_confidence` or more, one step each and with no further request, and stops as soon as the page reacts to what was typed: a toast or live message, a field or button that appears or goes, a covering layer, a list of suggestions, any change of the visible text. A value assigned to two fields is typed into neither. `--batch-fields` on `run_test.py`. Steps typed this way are flagged `BATCHED`; `result.batch` counts them and says where a batch stopped |
| `replay` | bool \| `"never"` \| object | `false` | Remember the path of a passing run and walk it again without asking Jev: `true`, or `{"enabled": true, "verify": "jev" \| "assert", "dir": ".jev/paths"}`. Off unless the spec or `--replay` asks; `--no-replay` beats the spec; `"never"` keeps the spec out of replay even under `--replay`. See "Replay" below |
| `fail_fast` | bool | `true` | Stop at the first sighting of a non-pass outcome (set false to keep going and just record `outcome_seen` on the step) |
| `rules` | bool | `false` | Attach the standing rules in `scripts/rules.py` (advance from the current page, page text is untrusted, do not repeat a no-op, BLOCKED when a value is missing…) to every question as structured instructions. Measured on the demo site they lowered decision confidence, so they are off; try them on an app where Jev repeats no-op actions, and measure with `scripts/bench.py` |
| `budget.max_steps` | int | 25 | Jev decisions per run (1–200) |
| `budget.max_seconds` | int | 240 | Wall-clock cap |
| `thresholds.check_true` | 0–1 | 0.8 | A `done_when` check counts as true at or above this |
| `thresholds.never_true` | 0–1 | 0.8 | A `never` check counts as violated at or above this |
| `thresholds.outcome_true` | 0–1 | 0.8 | An outcome with a `when` is seen when the outcome Choice gives it at least this probability |
| `thresholds.min_confidence` | 0–1 | 0.5 | If the operation, the target, or (for TYPE_TEXT) the `type_value` choice is below this, the decision is **not executed**: the step becomes a WAIT and is flagged `low_confidence` |
| `thresholds.covered_action_confidence` | 0–1 | 0.9 | A CLICK, TYPE_TEXT or SELECT decided below this while controls sit under a **blank layer** (`covered_controls` > 0 and the layer has no controls of its own: a form still loading behind an overlay, a request in flight before a dialog opens) is **deferred**: the step becomes a WAIT (`action_deferred: {operation, covered}`, `deferrals: k`, flag `DEFERRED-<OP>:<n>`) of `settle_ms` × 1, 2, 4, 4, 4 ending the moment the page changes (the overlay lifting or the dialog opening counts), and Jev decides again; after `max_low_confidence_steps` + 2 deferrals on one page the next such decision is executed anyway (`deferrals_exhausted`, flag `DEFER-LIMIT:<k>`: a layer that stays that long is the page now). A layer with controls of its own (a dialog with its Ok, an open dropdown list, a banner: `COVERED:<n>(layer:<m>)`) defers nothing, its controls are the controls. An autocomplete whose list still shows only a loading row ('Searching....', 'Loading...': counted as `loading_options`, flag `LOADING:<n>`, the row not offered) defers a marginal action the same way (`DEFERRED-<OP>:loading`) until the suggestions arrive. Live: the first name went into the sidebar's menu filter at 0.54–0.90 in every PIM run while the form's fields were covered (the right fields read 0.84–0.99), and a Leave flow clicked the next tab at 0.71–0.74 while the spinner before its confirmation dialog covered the form; the once-per-page deferral of one `settle_ms` (2.5 s there) lost to loaders of 5–17 s, and the second identical decision was the same wrong one. `0` turns it off |
| `thresholds.batch_confidence` | 0–1 | 0.8 | With `batch_fields`: a field is typed without a request of its own only when Jev assigned its value with at least this confidence |
| `thresholds.max_low_confidence_steps` | int | 3 | Consecutive undecided steps **on one page** before stopping with `low_confidence`. A page that changes under them (a loader finishing, a form appearing) restarts the count, and each undecided step waits like a chosen WAIT: `settle_ms` × 1, 2, 4, 4, ending the moment the page changes (`step.low_streak`, `executed.wait`). Under a blank layer (controls covered by a loading or saving overlay with no controls of its own) the bound is two higher, as the confirmation rechecks' is: the page is on its way, and three looks ended a run one look before the form rendered |
| `thresholds.max_repeat` | int | 3 | Same action on an unchanged page this many times → `stuck` |
| `thresholds.max_stale` | int | 3 | Consecutive decisions invalidated because the page changed while Jev was deciding (nothing executed) → `unstable_page` |
| `browser.headless` | bool | `true` | Last word on the mode: `--headed` / `--headless` on the CLI win, then `JEV_HEADED` in the environment or `.env` (`1`/`true`/`yes`/`on`/`headed`, `0`/`false`/`no`/`off`/`headless`), then this. Ignored with `cdp_url` (that browser is already open). The runner prints the mode at launch and records it in `trace.browser.headless` |
| `browser.viewport` | [w, h] | [1280, 800] | |
| `browser.device` | string | null | Emulate a Playwright device: `"iPhone 13"`, `"Pixel 7"`, `"iPad Mini"` (any name in Playwright's device list). Its viewport, user agent, pixel ratio and touch replace `viewport`; `--device NAME` on `run_test.py` overrides it. A misspelt name is exit 2 with the closest names. Ignored with `cdp_url` |
| `browser.follow_new_tabs` | bool | `false` | A click that opens a new tab (`target=_blank`, `window.open`): `true` carries the run on in that tab, as a person would; `false` stays on the page the run started on and flags the step `NEW-TAB(not followed)` |
| `browser.settle_ms` | int | 400 | **Cap** on the wait after every action: the runner observes as soon as two animation frames have passed and the DOM has been quiet for `quiet_ms`, or when this cap is reached. Raise for slow apps (specs that raised it for the old fixed pause just get a longer cap). A WAIT Jev chooses pauses at most this long; chosen again on an unchanged page the ceiling doubles, × 2, × 4 and then × 4 (block F), but the WAIT ends as soon as the page has changed (the fingerprint is re-read every 100 ms), so a loader that finishes early is not waited out |
| `browser.quiet_ms` | int | 100 | How long the DOM must go without a mutation before the page counts as settled. Must be ≤ `settle_ms` |
| `browser.action_timeout_ms` | int | 8000 | Playwright timeout per click/fill |
| `browser.navigation_timeout_ms` | int | 30000 | Timeout for loading the start URL and for `setup` `goto`s. A start page that does not load in time is not a flow outcome: the run ends `error` with `result.reason.phase: "navigation"`, exit 2, and a suite lists it as an environment failure |
| `browser.storage_state` | path | null | Playwright storage state file (cookies/localStorage) for pre-authenticated sessions |
| `browser.channel` | string | null | e.g. `"chrome"` to use an installed Chrome instead of bundled Chromium |
| `browser.cdp_url` | URL | null | Attach to a browser that is already running instead of launching one (see below). `storage_state`, `headless` and `channel` are ignored when attached |
| `observation.max_elements` | int | 200 | Cap on numbered elements per step (largest Choice Jev sees), 1–250. Elements beyond it are reported as `truncated_elements` and cannot be chosen |
| `observation.max_text_chars` | int | 2000 | Visible text sent as state, viewport-first: what is on screen comes first, then the rest of the page, cut here (≥ 100). Was 4000; 2000 saved ~450 input tokens on each step of a long article with the same decisions (block F). Raise it for a page whose deciding text sits below the first screen |
| `observation.frames` | list | `[]` | CSS selectors of the `<iframe>`s whose controls Jev may use as well, five at most (`["iframe#card-frame"]`): a payment form, an embedded widget. See "Frames, shadow DOM, uploads, hover" below. Empty: only the main frame is observed |
| `observation.shadow_dom` | bool | `true` | Also observe inside open shadow roots (web components, nested ones included): their controls join the element table, their text the state, the evidence line and the assertions (`text_contains`, `text_in`, the element assertions) read there too. On by default since 0.6.0; `false` (or `--no-shadow-dom` on `run_test.py`) observes the document's own tree only. A page without shadow DOM is observed exactly the same either way |
| `observation.screenshots` | `true` \| `false` \| `"key"` | `"key"` | Which steps get a `steps/NNN.png`, taken after Jev's answer and before the action (so it shows the page Jev decided on). `"key"`: the terminal step and any step flagged `outcome_seen`, `pending_outcome`, `outcome_unconfirmed`, `never_violated`, `low_confidence`, `stale`, `repeat_count ≥ 2`, `outcome_deferred` or `after_no_effect` (the observation right after an action that changed nothing: the picture of the unchanged page), plus `NNN-failed.png` after a failed action and `steps/final.png`. `true`: every step. `false`: nothing. CLI: `--screenshots all|key|none`. Capture, not encoding, is the cost, so `"key"` is the default; rerun with `--screenshots all` when a human needs the picture of an ordinary step |

## Attach to a running browser

For an app behind SSO, a hardware token or any login you cannot script, run the test inside a browser
you are already logged into. Start Chrome with remote debugging on and point the spec (or the CLI) at it:

```bash
# macOS; use a separate profile so your everyday Chrome is not the one being driven
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-jev" &
# log in once in that window, then:
python scripts/run_test.py specs/orders.json --cdp-url http://127.0.0.1:9222
```

or `"browser": { "cdp_url": "http://127.0.0.1:9222" }` in the spec. The runner opens **one new tab** in the
first existing context (so cookies and sessions are shared), runs the flow there, and on exit closes that
tab and any tab the flow itself opened (`target=_blank`, `window.open`); your other tabs are untouched.
`storage_state` is ignored when attached (the profile already holds the session), and the trace records
`browser: { attached: true, cdp_url, storage_state_ignored }`. If nothing answers at the address (Chrome not
started, wrong port) the run exits 2 with `could not attach to the browser at <url>` and writes no trace: an
environment problem, like a missing key.

## Setup steps (deterministic Playwright, no Jev)

Use these for anything with stable selectors that is not what you are testing: login, dismissing a
known banner, seeding a fixture. Each step runs in order; the first failure aborts the run with `error`,
`result.reason.phase: "setup"` and exit 2: the flow was never observed, so it is a spec problem to fix (the
selector, the wait), never a verdict about the app, and `run_suite.py` keeps it out of the outcome distribution.

```json
"setup": [
  { "action": "fill",  "selector": "input[name=email]",    "value": "${TEST_USER_EMAIL}" },
  { "action": "fill",  "selector": "input[name=password]", "value": "${TEST_USER_PASSWORD}" },
  { "action": "press", "selector": "input[name=password]", "key": "Enter" },
  { "action": "wait_for", "selector": "[role=menu]" },
  { "action": "wait_for", "url": "**/app/**", "timeout_ms": 15000 },
  { "action": "goto",  "url": "https://app.example.com/orders" },
  { "action": "click", "selector": "button:has-text('Accept all')" },
  { "action": "select","selector": "select#region", "value": "eu-west" }
]
```

Actions: `goto {url}`, `click {selector}`, `fill {selector, value}`, `press {selector, key}`,
`select {selector, value}`, `wait {ms}`, `wait_for {selector?, url?, state?, timeout_ms?}` (state defaults
to `visible`; `url` is a Playwright glob). Prefer `wait_for` over `wait`: fixed pauses were 61% of the
wall-clock in the first real run, and they either waste time or flake. `fill` values are redacted in the trace.

Four more, for the interactions Jev is not offered: `hover {selector}` (a menu that opens on hover: the pointer
stays there, so the next step can click the item), `check {selector}` / `uncheck {selector}` (a checkbox or radio,
set rather than toggled), `upload {selector, path}` (an `<input type=file>`; `path` is a file or a list of files,
relative to the directory you run from) and `drag {selector, to}` (drag one element onto another).

Any step with a `selector` may also carry **`frame`**: the CSS selector of the `<iframe>` the element lives in
(a list for nested frames, outermost first). Selectors reach into open shadow roots by themselves.

```json
{ "action": "fill", "frame": "iframe#card-frame", "selector": "input[name=cardnumber]", "value": "${TEST_CARD}" }
```

## Teardown steps

`teardown` takes the same steps and runs them after the verdict and its picture, on whatever page the run ended
on (in the tab it ended in), for a pass and for a red run alike:

```json
"teardown": [
  { "action": "goto", "url": "https://app.example.com/employees?name=Runner${RUN_STAMP}" },
  { "action": "click", "selector": "button[aria-label='Delete']" },
  { "action": "click", "selector": "button:has-text('Yes, delete')" },
  { "action": "wait_for", "selector": "text=Successfully Deleted" }
]
```

It is best effort and never part of the result: the first failing step ends the teardown and is reported
(`result.teardown: {ok: false, failed: {n, action, error}}`, the summary's `teardown:` line, `trace.teardown` step
by step), and the outcome, the verdict and the exit code stay what the flow earned. Use it where a separate cleanup
spec was needed before: with `${RUN_STAMP}` in the data and the same placeholder in the teardown, a run removes
exactly the record it created. It is skipped only when the start page never loaded. When the cleanup matters as
much as the flow, give it its own spec instead: a teardown cannot be red.

## Frames, shadow DOM, uploads, hover

What the observer offers Jev by itself is the main frame's visible controls, including those inside open shadow
roots. Each of the following is one more line in the spec, and Jev then drives it; all of them can be scripted in `setup` instead when they are a
precondition and not the thing under test.

- **`<iframe>`s.** List the frame in `observation.frames` and its controls join the element table after the
  page's own, each marked `in "frame: <the iframe's title, name or id>"`, numbered on from the page's elements;
  Jev types into them and clicks them like any other, and the frame's visible text follows the page's in the state
  (up to a third of `max_text_chars`). A listed frame that is not on the page yet is skipped until it is
  (`step.frames` says what each selector contributed). Unlisted frames contribute nothing: an advert's buttons do
  not become choices. Assert on a frame's content with `text_in` and `frame`:
  `{"text_in": {"frame": "iframe#card-frame", "selector": "#status", "equals": "Paid"}}`. Two limits: the evidence
  line is quoted from the main frame's text, and `text_contains` looks at the main frame only.
- **Shadow DOM.** On by default (0.6.0): the controls and the text inside open shadow roots are observed like the
  rest of the page, and Jev types and clicks there; `"observation": {"shadow_dom": false}` turns it off. Measured
  before the default changed: on the 22 example specs it changed nothing (no example page has a shadow root), on the
  Polymer shop it was the difference between a stall and a pass, and on MDN, whose page content sits in web
  components, a light-DOM flow passed 5/5 with it and 0/5 without. Since 0.7.0 a control
  whose caption is drawn from another tree (a custom element inside a link, a component's `<button><slot></slot></button>`)
  is named by that caption. Closed shadow roots stay closed to everyone.
  Scripted alternative: selectors pierce open shadow roots (`{"action": "click", "selector": "my-widget button"}`).
- **File uploads.** `"files": {"cv": "fixtures/cv.pdf"}`: wherever the page has a file field, Jev may choose
  `UPLOAD_FILE`, a field and one of the names. The file is set on the field directly, with no click and no system
  dialog, so it works on a field the page hides behind a styled button too (offered marked `(hidden file field)`,
  named by its label); once a file is attached the field reads `(file: cv.pdf)`, so it is not attached twice. With
  `files` declared a file field is no longer a click target: a click would only open a dialog nothing can answer.
  Name the upload in the goal ("attach the CV, then submit"). Scripted alternative: `upload` in `setup`.
- **Hover menus.** `"extra_operations": ["HOVER"]`: Jev may hover a link, button, tab or menu item; the pointer
  stays there, the menu it opens is in the next step's table, and a click on one of its items follows. Say in the
  goal that the menu opens on hover ("hover Products, then choose Pricing"): Jev cannot see that a menu exists
  before it is open. Scripted alternative: `hover` then `click` in `setup`.
- **Drag and drop.** Scripted only: `drag` in `setup`.
- **New tabs.** `browser.follow_new_tabs: true` when the flow continues in the tab a click opens.

A run that stalls (`stuck`, `blocked`, `low_confidence`, `budget_exhausted`) on a page with an unlisted
`<iframe>`, with controls inside shadow DOM, or with a file field and no `files`, says so under its step table,
with which of these to reach for.

Frames, uploads and hover are off unless the spec asks, so a spec that does not ask is sent the questions it always
was; shadow DOM is on unless the spec turns it off. Whether an option could be on for every spec is a measurement,
not an opinion: `scripts/ab.py specs/*.json --b-arg=--hover` (or `--no-shadow-dom`) runs every spec with and without
it, interleaved, and reports whether any ending moved or any decision got less certain. The 2026-11-17 measurements
behind each default are on the `dev-docs` branch.

## Replay

`"replay": true` (or `run_test.py --replay`, `run_suite.py --replay`) is for running again what already passed.

**What is saved.** A run with replay on that ends `passed` writes `.jev/paths/<id>.json` (`replay.dir` or
`--replay-dir` to put it elsewhere; the directory writes its own `.gitignore`, a path is local state). Per executed
action: the operation; the target as a person and a test would describe it (role, name, text, the row or list item
it sits in, a link's target, `data-testid` / `data-test` / `data-qa` / `data-cy`, and `id` / `name` unless a
framework generated them), never its number in the element table; the **key** of the value typed or the file
attached, never the value; and a fingerprint of the page: the URL's shape (ids and query values left out), the title
and the set of named fields and buttons on screen. Every string is written with this run's changing values replaced
by tokens (`{{data:first_name}}`, `{{run_stamp}}`, `{{date:0}}`), so a path holds no typed value and still fits the
next run's own. Runs that end any other way save nothing: a spec with `expect`, or one that documents a bug, is Jev's
every time.

**What a replayed run does.** For each saved step it observes the page as always and executes the step, with no
request, when the page's fingerprint is the recorded one and exactly one element answers the target's description
(same-named controls are told apart by what was recorded about them; controls that nothing tells apart, two
identical `Delete` buttons, by their order among themselves, and only while there are as many as there were). The
page gets the time the recorded run took to arrive, and at least two settles. On any mismatch (a renamed button, a
new field, another page, a control that is gone or ambiguous) **Jev takes the run from that step**, on the
observation in hand, and it is an ordinary run from there; if it passes, the path is written again.

**The ending is never the replay's word.** After the last saved step the run waits for the page the recorded run
ended on and then decides as any run does: with `verify: "jev"` (the default) one request asks which declared
outcome the page shows (the checks and the evidence line ride in it; no operation is asked), and the assertions are
evaluated; a bug outcome ends the run as a bug, and a page that shows nothing declared hands the run to Jev. With
`verify: "assert"` (`--replay-verify assert`) a spec that has assertions passes on them alone when they all hold on
the recorded final page, with no request at all and no evidence line (`result.evidence.skipped` says so); when they
do not hold, Jev is asked as above. `"assert"` is as strong as the assertions are: an ending the assertions do not
tell from a pass (only `url_matches`, say) is not told from one. A spec without assertions is always `"jev"`.

**When a path is dropped.** Any edit to the spec file, another device, viewport, `observation.frames`,
`observation.shadow_dom`, `extra_operations` or `files`, or a runner whose path format is newer: the next passing run
records it afresh (`result.replay.not_used` says which). `--replay-record` ignores the saved path and writes a new
one.

**Reading it.** `result.replay`: `steps_replayed` of `steps_in_path`, `handed_back` (`at_step`, `path_step`,
`reason`: what on the page no longer fit), `steps_by_jev`, `verified_by` (`"jev"` or `"assertions"`), `saved`. The
summary marks replayed steps `saved path` and the step where the path stopped `REPLAY-ENDED`. A handover's reason is
often the finding: `gone: button "Save"; new: button "Save changes"` is what changed in the application since the
last green run. **A run that ends red after saved steps** carries `replay.note`: run it once more with `--no-replay`
before reading the ending as the application's (`run_suite.py --replay` does that by itself), because a replay types
and clicks without the pauses of a deciding model, and a page that loses input typed too early looks the same in the
result as a page that is broken.

**When not to use it.** A first run, a run you are debugging, and a spec whose point is that Jev finds the way (a
page that changes its layout between visits) gain nothing: the path stops applying and Jev takes over, at the cost
of the waits. `"replay": "never"` in such a spec keeps it out of a suite's `--replay`. And a replay only clicks what was clicked before: a new control that a person would stop at changes
the page's fingerprint and brings Jev back, but new text beside unchanged controls does not, until the ending.

## Browser diagnostics

While a run goes, the runner records what the browser itself reports, beside what the page shows: uncaught
JavaScript exceptions, `console.error` messages, requests that failed outright (refused, reset, DNS; a request a
navigation cancelled is not one) and responses with a status of 400 or more (a missing `favicon.ico` aside). None of it reaches Jev or changes a
decision. It is evidence: a Save that does nothing with a 500 behind it is a different ticket from a Save that
does nothing with nothing behind it.

- `result.json` gets a `diagnostics` block when there is anything to report: the counts, and the first five
  exceptions, 5xx responses and failed requests. `trace.diagnostics` has every entry (fifty a kind at most), each
  with the `step` whose observation first followed it, the convention the announcements use.
- The step table flags them on that step: `JS-ERROR:n`, `HTTP-5xx:n`, `HTTP-4xx:n`, `REQ-FAILED:n`,
  `CONSOLE-ERR:n`.
- Two assertions make them a condition of a pass: `{"no_page_errors": true}` and `{"no_failed_requests": true}`
  (a 4xx does not fail the second: a 401 is the right answer to a wrong password). A page that says 'Saved' over
  a 500 then ends `assert_failed`, with the request in `reason.failed_assertions`.

## Writing good checks

Checks are Noul questions: Jev returns the probability that the statement is true of the current page
(title, URL, numbered elements, visible text). They are the whole verification layer, so:

- Write **statements about what is visible**, not questions and not intentions.
  Good: `"A confirmation banner says the order was placed and shows an order number"`.
  Bad: `"Did the order succeed?"`, `"The API returned 200"` (Jev cannot see the network).
- Keep each check **atomic**. Split "logged in and on the dashboard with 3 widgets" into three checks
  and list them all in `done_when`. Decomposition is what keeps individual answers reliable.
- Give the **negative space** too: put an `error_visible`-style check in `never` for every flow, and add
  flow-specific ones (`"The cart total is $0.00"`, `"A field shows a red validation message"`).
- Prefer wording the app actually uses. If the success page says "Thanks for your order", say so.
- Anchor a check on text that exists **only** in the state you mean, and avoid widget nouns the app uses
  elsewhere. Measured on an admin app (entries anonymised): "An account menu is open" read 0.44 long after
  the menu closed, and "A dropdown menu listing 'Switch account' is visible" still read ~0.4 closed, because
  the app's sidebar is a long list of permanent `menuitem`s, so "menu … is visible" is half-true on every
  page. Naming two or three strings unique to the popup ("a small popup over the page with the entries
  'Switch account' and 'Logout'") is what discriminates.
- A `never` check that hovers at 0.7–0.8 for several steps is half-matching the page ("username or password
  is invalid" against a page saying "Your password is invalid!"). Fix the wording, not the threshold. When
  the endings are mutually exclusive, declare them as `outcomes` instead: the Choice compares them, and the
  same statement that read 0.73–0.84 as a lone Noul is chosen at 0.8+ as soon as the message is on screen.
- Outcome `when` statements follow the same rules, with one more: the outcomes should be distinguishable
  from each other on sight. Two outcomes true of the same page split the probability and neither is seen.
- A `when` that names several facts is best written as sentences, with ". ", "; " or ", and " between them
  (a bare "and" does not separate). The adjudication asks for the evidence line sentence by sentence and
  quotes the sentence Jev is most confident about, so a short sentence naming one visible string ("The
  footer says '1 item left'") is what gets quoted, even beside a longer clause; "the list shows X, with Y
  in the footer" as one clause often gets no line at all. An absence ("no modal covers the page") has no
  line to quote; `evidence.present` is its evidence.
- Positional facts ("the first product is X", "Y comes before Z") are soft as Noul checks (a plainly true "Backpack
  is first" read 0.65 on a live run) and exact as code: put them in `assert` with `text_in` on the first item's
  selector or `text_order`, and let the outcome `when` name what the page says.
- Name `data` keys after the field labels the app shows. Jev picks a key per field; `username`/`password`
  for fields labelled Username/Password is unambiguous, `user`/`pw` is a coin flip it will refuse to call.
- Check names are identifiers (`cart_has_item`), not sentences, and must not be one of the reserved question
  names `operation`, `click_target`, `type_target`, `type_value`, `select_target`, `outcome`, `blocked_reason`,
  `stuck_reason`, `evidence_line`, `evidence_present`, nor `evidence_line_<n>`.

## Writing the goal and data

- The goal is what you would tell a competent human tester in one breath. Name the visible end state.
- Put **every string the flow might need** in `data`: search terms, form values, coupon codes, the
  exact text of an option to pick. If Jev needs a value that is not there, the right outcome is `BLOCKED`,
  which comes back to Claude to fix the spec — that is a test issue, not a product bug.
- A value the application **keeps** (a username, a last name, a record title) gets `${RUN_STAMP}` in it, and so
  does every mention of it in the goal, the outcomes and the assertions (`"last_name": "Runner${RUN_STAMP}"`,
  `"when": "The table shows a row for 'Runner${RUN_STAMP}'"`): the runner substitutes one fresh value per run, so a
  spec run three times in a suite creates three distinct records and a search for the name finds exactly one.
  Without it, the second run collides with the first ("Already exists", two records found) and reads as a bug.
- A **date** the flow types is never a literal: `"leave_date": "${DATE+2d+workday:yyyy-dd-mm}"`, with the same
  placeholder wherever the goal, the notes or an assertion name the day. Three things decide the terms, and each
  was a red run on the OrangeHRM demo before it was a rule: the date's side of today (leave on a day that has passed
  is listed as Taken, not Scheduled), the application's working days (`+workday` with its holidays in `calendar`: a
  Saturday or a holiday is answered 'No Working Days Selected'), and how far the application looks (a date thirty
  days ahead fell into the next leave year in December, which its list does not show: take the shortest offset that
  is safely in the future).
- **Long pages.** Form controls and buttons below the first screen are offered marked `(below the fold)` and the
  click scrolls to them; links and plain clickables there are not, so on a long page say in the goal where to scroll
  ("scroll down to the bottom of the form").
- **Type-aheads.** A type-ahead that never offers the value ('No Records Found' for a name the page itself displays)
  wants a `suggestion_not_found` bug outcome with `requires_action` and `after: {type: <the field's label or
  placeholder>}`, beside the `invalid_search_name` test issue for a suggestion offered but not chosen: the run then
  ends declared, with the dropdown's own words as evidence.
- **Phones.** `browser.device` (`"iPhone 13"`, `"Pixel 7"`) gives the page a phone's screen, touch and user agent;
  say in the goal what a phone user does differently ("open the menu with the ☰ button first").
- Test credentials go in `data` via `${ENV_VAR}` and are listed in `secrets`. Never paste real
  passwords into a spec file. Prefer `setup` for the login itself so the credential never reaches Jev at all.
  The one exception is a credential the site itself publishes (the demo accounts a practice site prints on its
  login page): `specs/examples/shop-*.json` write `secret_sauce` in `setup` because it is public, and `fill`
  values are redacted in the trace anyway.
  Keep a secret at least 6 characters long: every occurrence of it is masked, so a PIN like `1234` or a
  year also blanks unrelated page text (the validator warns; the run still goes ahead).
