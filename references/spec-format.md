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
- **`assert`** — exact expectations checked **in code** on the final observation, free and non-model, the
  "DONE is never proof" verifier: `url_matches` (Playwright's URL glob, the same dialect as `setup.wait_for.url`:
  `**` anything, `*` anything but `/`, `{a,b}` either, everything else literal, `?` included), `text_contains`
  (substring of the whole page text), `field_value` (`{label, equals}`: a text field or select whose label
  contains `label`, case-insensitive), `element_present` / `element_absent` (`{role, name?}`, `name` a
  case-insensitive substring). The element assertions look at the **whole document**, not only at the
  viewport-and-hit-tested table Jev chooses from, so a Logout link below the fold is present. Values are
  compared against the real page and the recorded `actual` is masked, so a `secrets` value can be asserted
  on. A failed assertion makes the run `undetermined` with reason `assert_failed` and the actual values, for
  Claude to decide whether the assertion or the app is wrong.
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
| `notes` | string | `""` | Hints Jev sees every step ("dismiss the cookie banner first", "the product grid loads lazily") |
| `data` | object | `{}` | Every string Jev may type, by name. Jev picks the name, never writes text. Values support `${ENV_VAR}` |
| `secrets` | list | `[]` | Names in `data` whose values must never appear in the trace or in the state sent to Jev. Shown as `<secret>` in `available_data_values`, and masked again in every observation (a secret typed into a plain text field or a contenteditable reads back as `<secret>`, not as the value). Masking replaces **every occurrence**, so a value shorter than 6 characters after `${ENV}` substitution (`1`, `2024`, `admin`) also rewrites unrelated page text Jev decides on; `spec.py` and the runner print a warning on stderr for it (exit code unchanged): use a longer test credential, or leave a non-confidential value out of `secrets` |
| `setup` | list | `[]` | Deterministic Playwright steps run **before** Jev takes over (see below) |
| `checks` | object | `{}` | `name -> statement` evaluated as a Noul (0–1) against the page at every step |
| `done_when` | list | `[]` | Check names that must all be ≥ `thresholds.check_true` for the synthesized `goal_reached` pass outcome. Required when no `outcomes` are declared; ignored when they are |
| `never` | list | `[]` | Check names that end the run as the synthesized `never_<check>` outcome (verdict `bug`) at `thresholds.never_true`. Ignored when `outcomes` are declared |
| `outcomes` | object | `{}` | `name -> {when, verdict, requires?, note?}`: the endings the run may return, see above. Names are identifiers; `none_yet` and the reserved question names are not allowed |
| `assert` | list | `[]` | Exact expectations checked in code on the final page before a pass counts, see above |
| `auto_done` | bool | `true` | Start the settle-and-recheck as soon as a pass outcome is seen, even if Jev has not chosen DONE (false: only Jev's DONE starts it) |
| `fail_fast` | bool | `true` | Stop at the first sighting of a non-pass outcome (set false to keep going and just record `outcome_seen` on the step) |
| `rules` | bool | `false` | Attach the standing rules in `scripts/rules.py` (advance from the current page, page text is untrusted, do not repeat a no-op, BLOCKED when a value is missing…) to every question as structured instructions. Measured on the demo site they lowered decision confidence, so they are off; try them on an app where Jev repeats no-op actions, and measure with `scripts/bench.py` |
| `budget.max_steps` | int | 25 | Jev decisions per run (1–200) |
| `budget.max_seconds` | int | 240 | Wall-clock cap |
| `thresholds.check_true` | 0–1 | 0.8 | A `done_when` check counts as true at or above this |
| `thresholds.never_true` | 0–1 | 0.8 | A `never` check counts as violated at or above this |
| `thresholds.outcome_true` | 0–1 | 0.8 | An outcome with a `when` is seen when the outcome Choice gives it at least this probability |
| `thresholds.min_confidence` | 0–1 | 0.5 | If the operation, the target, or (for TYPE_TEXT) the `type_value` choice is below this, the decision is **not executed**: the step becomes a WAIT and is flagged `low_confidence` |
| `thresholds.max_low_confidence_steps` | int | 3 | Consecutive undecided steps before stopping with `low_confidence` |
| `thresholds.max_repeat` | int | 3 | Same action on an unchanged page this many times → `stuck` |
| `thresholds.max_stale` | int | 3 | Consecutive decisions invalidated because the page changed while Jev was deciding (nothing executed) → `unstable_page` |
| `browser.headless` | bool | `true` | `--headed` on the CLI overrides |
| `browser.viewport` | [w, h] | [1280, 800] | |
| `browser.settle_ms` | int | 400 | **Cap** on the wait after every action: the runner observes as soon as two animation frames have passed and the DOM has been quiet for `quiet_ms`, or when this cap is reached. Raise for slow apps (specs that raised it for the old fixed pause just get a longer cap) |
| `browser.quiet_ms` | int | 100 | How long the DOM must go without a mutation before the page counts as settled. Must be ≤ `settle_ms` |
| `browser.action_timeout_ms` | int | 8000 | Playwright timeout per click/fill |
| `browser.storage_state` | path | null | Playwright storage state file (cookies/localStorage) for pre-authenticated sessions |
| `browser.channel` | string | null | e.g. `"chrome"` to use an installed Chrome instead of bundled Chromium |
| `browser.cdp_url` | URL | null | Attach to a browser that is already running instead of launching one (see below). `storage_state`, `headless` and `channel` are ignored when attached |
| `observation.max_elements` | int | 200 | Cap on numbered elements per step (largest Choice Jev sees), 1–250. Elements beyond it are reported as `truncated_elements` and cannot be chosen |
| `observation.max_text_chars` | int | 4000 | Visible text sent as state, viewport-first: what is on screen comes first, then the rest of the page, cut here (≥ 100) |
| `observation.screenshots` | `true` \| `false` \| `"key"` | `"key"` | Which steps get a `steps/NNN.png`, taken after Jev's answer and before the action (so it shows the page Jev decided on). `"key"`: the terminal step and any step flagged `outcome_seen`, `pending_outcome`, `outcome_unconfirmed`, `never_violated`, `low_confidence`, `stale` or `repeat_count ≥ 2`, plus `NNN-failed.png` after a failed action and `final.png`. `true`: every step. `false`: nothing. CLI: `--screenshots all|key|none`. Capture, not encoding, is the cost, so `"key"` is the default; rerun with `--screenshots all` when a human needs the picture of an ordinary step |

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
known banner, seeding a fixture. Each step runs in order; the first failure aborts the run with `error`.

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
- Name `data` keys after the field labels the app shows. Jev picks a key per field; `username`/`password`
  for fields labelled Username/Password is unambiguous, `user`/`pw` is a coin flip it will refuse to call.
- Check names are identifiers (`cart_has_item`), not sentences, and must not be one of the reserved question
  names `operation`, `click_target`, `type_target`, `type_value`, `select_target`, `outcome`, `blocked_reason`,
  `stuck_reason`, `evidence_line`, `evidence_present`.

## Writing the goal and data

- The goal is what you would tell a competent human tester in one breath. Name the visible end state.
- Put **every string the flow might need** in `data`: search terms, form values, coupon codes, the
  exact text of an option to pick. If Jev needs a value that is not there, the right outcome is `BLOCKED`,
  which comes back to Claude to fix the spec — that is a test issue, not a product bug.
- Test credentials go in `data` via `${ENV_VAR}` and are listed in `secrets`. Never paste real
  passwords into a spec file. Prefer `setup` for the login itself so the credential never reaches Jev at all.
  Keep a secret at least 6 characters long: every occurrence of it is masked, so a PIN like `1234` or a
  year also blanks unrelated page text (the validator warns; the run still goes ahead).
