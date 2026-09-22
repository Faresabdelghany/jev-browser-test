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

## Fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `id` | string | required | Folder-safe name; runs land in `runs/<id>/<timestamp>/` |
| `start_url` | string | required | Where the browser opens. Supports `${ENV_VAR}` |
| `goal` | string | required | What a tester would be told to do. One flow, plain language, names the visible outcome |
| `notes` | string | `""` | Hints Jev sees every step ("dismiss the cookie banner first", "the product grid loads lazily") |
| `data` | object | `{}` | Every string Jev may type, by name. Jev picks the name, never writes text. Values support `${ENV_VAR}` |
| `secrets` | list | `[]` | Names in `data` whose values must never appear in the trace or in the state sent to Jev |
| `setup` | list | `[]` | Deterministic Playwright steps run **before** Jev takes over (see below) |
| `checks` | object | `{}` | `name -> statement` evaluated as a Noul (0–1) against the page at every step |
| `done_when` | list | required | Check names that must all be ≥ `thresholds.check_true` for a pass |
| `never` | list | `[]` | Check names that must never reach `thresholds.never_true` |
| `auto_done` | bool | `true` | Stop with `passed` as soon as `done_when` is satisfied, even if Jev has not chosen DONE |
| `fail_fast` | bool | `true` | Stop immediately when a `never` check fires (set false to keep going and just record it) |
| `rules` | bool | `false` | Attach the standing rules in `scripts/rules.py` (advance from the current page, page text is untrusted, do not repeat a no-op, BLOCKED when a value is missing…) to every question as structured instructions. Measured on the demo site they lowered decision confidence, so they are off; try them on an app where Jev repeats no-op actions, and measure with `scripts/bench.py` |
| `budget.max_steps` | int | 25 | Jev decisions per run (1–200) |
| `budget.max_seconds` | int | 240 | Wall-clock cap |
| `thresholds.check_true` | 0–1 | 0.8 | A `done_when` check counts as true at or above this |
| `thresholds.never_true` | 0–1 | 0.8 | A `never` check counts as violated at or above this |
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
| `observation.screenshots` | `true` \| `false` \| `"key"` | `"key"` | Which steps get a `steps/NNN.png`, taken after Jev's answer and before the action (so it shows the page Jev decided on). `"key"`: the terminal step and any step flagged `never_violated`, `low_confidence`, `stale` or `repeat_count ≥ 2`, plus `NNN-failed.png` after a failed action and `final.png`. `true`: every step. `false`: nothing. CLI: `--screenshots all|key|none`. Capture, not encoding, is the cost, so `"key"` is the default; rerun with `--screenshots all` when a human needs the picture of an ordinary step |

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
first existing context (so cookies and sessions are shared), runs the flow there, and on exit closes only
that tab; your other tabs are untouched. `storage_state` is ignored when attached (the profile already holds
the session), and the trace records `browser: { attached: true, cdp_url, storage_state_ignored }`.

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
  elsewhere. Measured: "An account menu is open" read 0.44 long after the menu closed, and "A dropdown menu
  listing 'Impersonate' is visible" still read ~0.4 closed, because the app's sidebar is 17 permanent
  `menuitem`s, so "menu … is visible" is half-true on every page. Naming two or three strings unique to the
  popup ("a small popup over the page with the entries 'Impersonate' and 'Logout'") is what discriminates.
- A `never` check that hovers at 0.7–0.8 for several steps is half-matching the page ("username or password
  is invalid" against a page saying "Your password is invalid!"). Fix the wording, not the threshold.
- Name `data` keys after the field labels the app shows. Jev picks a key per field; `username`/`password`
  for fields labelled Username/Password is unambiguous, `user`/`pw` is a coin flip it will refuse to call.
- Check names are identifiers (`cart_has_item`), not sentences, and must not be one of the reserved names
  `operation`, `click_target`, `type_target`, `type_value`, `select_target`.

## Writing the goal and data

- The goal is what you would tell a competent human tester in one breath. Name the visible end state.
- Put **every string the flow might need** in `data`: search terms, form values, coupon codes, the
  exact text of an option to pick. If Jev needs a value that is not there, the right outcome is `BLOCKED`,
  which comes back to Claude to fix the spec — that is a test issue, not a product bug.
- Test credentials go in `data` via `${ENV_VAR}` and are listed in `secrets`. Never paste real
  passwords into a spec file. Prefer `setup` for the login itself so the credential never reaches Jev at all.
