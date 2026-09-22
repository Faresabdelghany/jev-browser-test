---
name: jev-browser-test
description: Goal-driven end-to-end browser testing where Claude writes the test spec and judges the result, TypeSafe's Jev decision model picks every click/type/scroll from a numbered element table (jev-ultrafast style, one ~0.3 s request per decision), and Playwright executes. Use this whenever the user wants to test, verify, smoke-test, regression-test or explore a web UI flow (login, signup, checkout, search, forms, CRUD screens, admin panels) with Jev or TypeSafe, mentions jev-ultrafast or browser-use with Jev, asks for "fast/cheap AI browser tests", wants E2E tests that survive selector or layout changes, or needs fuzzy UI assertions like "the error message tells the user their card was declined". Also use it to triage an existing run (a result.json, trace.json or runs/ folder) into PASS / BUG / TEST_ISSUE / FLAKY, to reproduce a bug ticket as a rerunnable spec, or to ask whether a page is flaky. Do not use it for unit tests, API tests, or flows with fully stable selectors where plain Playwright already works.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/.venv/bin/python ${CLAUDE_SKILL_DIR}/scripts/*)
---

# Jev browser test

Claude is the brain, Jev is the hands, Playwright is the body.

- **Claude (you)** writes the test *spec* before the run and judges the *result* after it. You never sit inside
  the step loop, so a 30-step flow costs you two turns of thinking, not thirty.
- **Jev** (TypeSafe's System One model) makes one typed decision per step from options the runner offers: which
  operation, which numbered element, which prepared value, plus the spec's checks and outcomes, all in **one
  request** (~0.3 s warm; the connection is opened while the browser launches, so the first request is warm too).
  Jev cannot invent an action that is not on the page and never writes text: every string comes from `data`.
- **Playwright** turns the live page into a numbered element table in one browser call and executes the action;
  the runner observes again as soon as the DOM is quiet (~0.15 s per action).

Measured on the demo login (3 actions): ~6 s a run, of which ~2 s is the site's own page load and ~0.2 s the
browser launch; the rest is 5 Jev requests and the browser work. `references/runner-design.md` has where every
millisecond goes and which levers are left.

Only a result comes back to you: `result.json` names exactly **one of the outcomes your spec declared** (with the
verdict you attached when you wrote it and the line of the page that proves it) or `undetermined` with a typed
reason and a suggested verdict. The runner is deterministic given Jev's answers, which makes the trace usable as
evidence.

The loop: **ticket or flow → Claude writes the spec → Jev runs it → Claude judges → if BUG, Claude fixes the code
→ the same spec re-runs green → PR.** Steps 1–4 get you to the verdict; step 5 produces the value.

## When Jev earns its place

Use plain Playwright (a `setup` step) for anything with a stable selector that is *not* what you are testing:
login, dismissing a known banner, seeding data. Jev adds latency there and no value. Jev earns its place where a
human would have to look at the screen and decide: the flow is a goal, not a script; the UI changes often; the
assertion is fuzzy ("a success toast confirms the save"); you are exploring a screen for breakage. Mixing is the
normal case: deterministic `setup`, then a Jev-driven goal, then code assertions on the final page.

## Workflow

`$SKILL` below is this skill's directory (`${CLAUDE_SKILL_DIR}` in Claude Code). Specs and runs live in the
project you are testing (`specs/`, `runs/`), the scripts stay in the skill.

### 0. Environment (once per machine)

```bash
python3 -m venv $SKILL/.venv && $SKILL/.venv/bin/pip install -r $SKILL/scripts/requirements.txt
$SKILL/.venv/bin/python -m playwright install chromium
$SKILL/.venv/bin/python $SKILL/scripts/selftest.py     # offline: local pages + a fake Jev, ~45 s, must end SELFTEST OK
export TYPESAFE_API_KEY=...   # https://console.typesafe.ai/keys, or a .env in the directory you run from
```

Use that interpreter for every command below (`python` stands for it). Never install into the system Python,
never echo the key back, never write it into a spec.

### 1. Write the spec

Read `references/spec-format.md` the first time, then write `specs/<id>.json`:

- **goal** — what you would tell a tester in one breath, ending with the visible outcome.
- **data** — every string the flow might type. Jev chooses *which* value; a missing one surfaces as `BLOCKED`.
  Credentials go through `${ENV_VAR}` + `secrets`, and preferably through `setup` so they never reach Jev. A
  credential the site itself publishes (a demo account printed on its login page) may be written plainly.
- **outcomes** — the endings you accept back: the acceptance criteria as `pass`, the wrong behaviour you test for
  (or the ticket reports) as `bug`, a CAPTCHA or approval step as `needs_human`. A negative test declares the
  rejection as `pass` and the success as `bug`, with a `note`. Write each `when` as **one visible fact per
  sentence** (". " between sentences): that is what gets quoted as the evidence line. Put **`requires_action:
  true`** on any bug outcome that describes "nothing happened" (the list is still unsorted, the dialog is still
  open): such a statement is true of the untouched start page too, and the flag defers it until an action ran.
- **assert** — exact checks in code on the final page, free and non-model: `url_matches`, `text_contains`,
  `text_in` (text inside a CSS-selected element: the notification, the badge, never the whole page when the
  page's copy mentions the same words), `text_order` (a sorted list), `field_value`, `element_present/absent`.
  Give every spec at least one: with assertions a pass sighting is **confirmed at once in code** (`confirm:
  "assert"`, the default) instead of a pause, a second look and another request.
- **checks** — atomic progress statements, one fact each; an outcome's `requires` can lean on them.
- **setup** — deterministic Playwright steps for preconditions. Prefer `wait_for` to `wait`.
- **expect** — only for a spec whose *correct* result is red (a demo account documented as broken): the ending
  it should reach. It is green when it matches and red when the behaviour changes. Never use it to hide a bug.

Validate: `python $SKILL/scripts/spec.py specs/<id>.json`. Ask the user only for what you cannot infer (start
URL, test account, the app's wording for success) and state your assumptions inline instead of stopping.

### 2. Run

```bash
python $SKILL/scripts/run_test.py specs/<id>.json            # -> runs/<id>/<ts>/result.json + trace.json + steps/*.png
python $SKILL/scripts/run_test.py specs/<id>.json --headed   # watch it, when debugging locally
```

Exit 0 = a pass (or, with `expect`, the declared result); 1 = any other outcome or `undetermined`; 2 = never a
verdict: a spec problem, a missing key, a browser that would not launch, a start URL that did not load, a setup
step that failed (`result.reason.phase`). Fix a 2 first; it is never a bug.

**Run once, read, then decide.** One run answers "does this flow work". Rerun only after you read the result: a
rerun that passes tells you nothing about why the first one failed. A suite (below) answers "is it stable" with
3–5 repeats. Never fire dozens of runs at a page to answer one question, and use at most 2 workers against a
shared demo host: its load timeouts are then your flakiness, not the page's.

### 3. Read the result, then the trace

```bash
python $SKILL/scripts/summarize_trace.py runs/<id>/<ts>/trace.json --result   # result.json: outcome, verdict, evidence
python $SKILL/scripts/summarize_trace.py runs/<id>/<ts>/trace.json            # one line per step + flags
python $SKILL/scripts/summarize_trace.py runs/<id>/<ts>/trace.json --step 7   # everything about one step
```

`result.json` first: `outcome`, `verdict`, `evidence.line` (the page's own words, chosen by Jev and copied
verbatim), `confirmed_by` (`assertions` or `recheck`), `path_confidence`, `assertions`, `story`, and for
`undetermined` the `reason` with its typed cause and `suggested_verdict`; `expected` for a spec with `expect`.
Open the step table only for `undetermined` or a surprising outcome. Flags worth knowing: `NO-EFFECT` (an
action landed and the page did not change: the classic dead control; the next step's picture shows it),
`DEFERRED:<outcome>` (true before any action, not counted), `LOW-CONF`, `STALE`, `EVIDENCE-ASKED`. With the
default `screenshots: "key"` the terminal step, every flagged step and the step after a no-effect action have a
`steps/NNN.png`; `--screenshots all` pictures every step on a rerun. The one reading rule: the checks recorded
in step *n* describe the page **before** action *n*; action *n*'s effect shows in step *n+1*.

### 4. Judge and report

Follow `references/verdict-rubric.md`. Exactly one verdict per run: **PASS**, **BUG**, **TEST_ISSUE**, **FLAKY**
or **NEEDS_HUMAN**. A declared outcome carries its verdict: sanity-check it against `evidence.line` and the
screenshot, and if the label does not fit what you see, the spec mislabelled it (fix `when` or `verdict`, rerun,
say so). For `undetermined`, start from `reason.suggested_verdict`: a red run is a bug only when the action was
reasonable and the next page shows the app misbehaving; it is a test issue when the spec caused it (missing data,
unreachable outcome, a banner that belonged in `setup`). Fix the spec and rerun at most twice before reporting a
test issue. Never call a single run flaky.

Report with the rubric's template: verdict, flow, result numbers (runs made, Jev calls, seconds), the story in
2–4 sentences, the evidence (step, action, confidence, the quoted line, the screenshot path), what was expected,
the next step. Say how many browser runs you made. If the verdict is BUG and an issue tracker is connected, offer
to file it; do not file without asking.

### 5. Close the loop: fix, re-run, ship

When the verdict is **BUG** and the app's repository is available: locate the code path from the trace (the URL,
the element Jev clicked, the failed check, the visible error text), fix it the way that codebase is fixed, re-run
the **same spec** against the fixed build (red must turn green with the same actions), and offer the fix, both
traces and the summary tables as the PR and ticket evidence. Never change the app to make a wrong spec pass, and
never loosen a spec to get green: that is a TEST_ISSUE wearing a BUG's clothes. **TEST_ISSUE**: the fix is in the
spec (two revisions, then NEEDS_HUMAN). **FLAKY**: a `wait_for` in `setup`, a longer `navigation_timeout_ms`, or
an outcome anchored on better text. **NEEDS_HUMAN**: stop and ask the specific question.

### Starting from a ticket

Write the spec from the ticket: the reproduction steps as the **goal**, the acceptance criteria as the **`pass`
outcome** (in the app's own words) with the exact expectations in **`assert`**, the reported wrong behaviour as
the **`bug` outcome** (with `requires_action` when it describes a missing effect). A bug ticket's spec comes back
**BUG before the fix and PASS after**, and stays in `specs/` as the regression test. Say how to rerun it.

## Triage-only mode

Handed a run folder (`result.json`, `trace.json`, screenshots), the answer is in it: skip to steps 3–4.

1. Read `result.json`, the step table, the pictures. **Do not launch a browser first.**
2. "Is it flaky?" is answered from the trace's flake signatures: `STALE` steps, `executed.ok: false`, `RETRIED`,
   `usage.reconnects`, a `reason.phase`, an `error` status. None present, plus a confident declared outcome or a
   typed reason with a suggestion → deterministic evidence; say so and do not rerun. Rerun once only when a
   signature is present, the user asks, or after a spec fix you made.
3. To separate TEST_ISSUE from BUG cheaply, run a **control**: the same spec with a known-good account, or the
   sibling spec known to pass. One run, ~10 Jev calls. Prefer it to reading the app's source, which was not asked
   for and rarely changes the verdict.
4. One triage = one reading, at most one rerun and one control. Report how many runs you made.

## Suites: anything longer than one spec

```bash
python $SKILL/scripts/run_suite.py specs/*.json --repeat 3 --workers 2   # -> runs/suite/<ts>/results.json + results.md
```

Launch it with the Bash tool's `run_in_background` and **do nothing until the completion notification**. Then
read `results.md`: per spec the outcome distribution, the **agreement on verdicts** (two legitimate pass endings
agree), medians, and a suite verdict: one verdict everywhere → it; a spec with `expect` whose every run matched →
`expected` (green); any disagreement → **`flaky`**, computed, never diagnosed from one run. A start URL that never
loaded or a setup step that failed is listed as an environment/setup failure and kept out of the distribution.
Exit 0 iff every spec is `pass` or `expected`. Open a trace only for a spec that is `undetermined` or `flaky`.

When a suite reads `flaky`, say which kind: **environment** (load timeouts, stale pages, error runs) or **an app
that varies by design** (every run a confident declared outcome, different evidence lines: a random notification,
an A/B page). The second is not noise to retry away: if the spec asserts one ending of a legitimate variation, fix
the spec (`text_in` on the element accepting either message, or an either/or pass outcome); if the product's
contract forbids the variation, it is a BUG with a measured rate.

For a human reader (a PR, a ticket), `python $SKILL/scripts/report.py runs/<id>/<ts>` writes a self-contained
`report.html` beside the trace (step table, probabilities, checks, screenshots inline); given a suite directory
it writes one per run. Keep specs independent (each has its own `setup`). Keep `runs/` out of version control.

## What makes a run fast (and what does not)

The runner already does what jev-ultrafast does: one request per decision, one browser call per snapshot, no
screenshots in the loop, event-based settles, a pre-connected keep-alive client, WAITs that end the moment the
page changes. A probe showed the ~0.3 s per request is the API's floor (HTTP/2 and the number of questions per
request change nothing), so what *you* control is the number of round trips and the waiting:

- Put login and known banners in `setup`: each is one Jev request saved and no chance of a wrong pick.
- Give the spec assertions: a pass then confirms itself in code, saving a pause, an observation and a request.
- Name the visible end state in the goal and the outcomes; a vague goal buys WAITs and wandering steps.
- Use `wait_for {selector|url}` instead of `wait {ms}` in `setup`.
- Do not add repeats to be sure: one run is evidence, three to five measure stability, more is load on the host.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TYPESAFE_API_KEY is not set` | Export the key or put it in `.env` in the directory you run from |
| exit 2 with "Spec problems" | Read the list: a `done_when` naming an unknown check, a check written as a question, a missing `${ENV}`, an `assert` of the wrong shape |
| exit 2, `reason.phase: navigation` (`Page.goto: Timeout`) | The start URL did not load within `browser.navigation_timeout_ms` (30 s): a slow or unreachable host, or too many parallel workers on a shared one. Environment, never a bug: rerun sequentially, raise the timeout |
| exit 2, `reason.phase: setup` (`setup[i] failed`) | The selector or `wait_for` in a setup step did not match; fix it or move that step into the goal |
| `blocked` right after a text field appears (`blocked_reason: missing_data_value`) | Add the needed value to `data` |
| `blocked` / `stuck` after a click flagged `NO-EFFECT` (`stuck_reason: control_had_no_effect`, suggested BUG) | A dead control, the classic product bug. The next step's picture shows the unchanged page; confirm the click landed on the right control in `--step N` |
| A bug outcome fires at step 1 with zero actions | Its `when` is true of the start page ("the list is still unsorted"). Set `requires_action: true` on it |
| `assert_failed` | A pass was seen but an assertion did not hold: `reason.failed_assertions` has the actual values. Decide whether the assertion or the app is wrong; never loosen it silently |
| An assertion on a message passes on every load | `text_contains` searches the whole page and the page's copy mentions the words. Use `text_in` with the element's selector |
| The outcome that came back does not match what the screenshot shows | The spec mislabelled it: fix that outcome's `when` or `verdict`, rerun, say so |
| Two outcomes hover at 0.4–0.5 while the page clearly shows one | Both `when`s are true of that page; reword them with a string unique to each |
| `evidence.line` is null although the outcome is right | The `when` mixes several facts or history in one sentence. One plain page fact per sentence, history in its own sentence; an absence has no line to quote, `evidence.present` is its evidence |
| `low_confidence` with `type_value` split between two keys | Rename `data` keys to the field labels the app shows |
| `low_confidence` over several elements with the same label | The observer names them by their card or row; if the table still shows bare duplicates, say which one in `notes` ("the third Add to cart") or script that click in `setup` |
| `stuck` with confidence ≈ `min_confidence` and flat target probabilities | The control Jev needs is not in the table (a div with no role or cursor hint): a `setup` click or an ARIA role in the app. TEST_ISSUE, note the accessibility gap |
| `budget_exhausted` with `stuck_reason: still_loading` | The page was still loading when the budget ran out. Rerun once; then raise `budget`, or suspect a loader that never completes |
| `unstable_page` | The page never held still (`step.stale` says what moved). Raise `browser.quiet_ms` / `settle_ms` or `wait_for` the thing that keeps changing in `setup` |
| A suite reads `flaky` but every run is a clean declared outcome | The app varies by design; see Suites. A spec with two legitimate pass endings agrees on verdicts, so declare both as `pass` outcomes |
| An expected-red spec keeps a nightly gate red | Declare its ending in `expect`; the suite then reads it `expected` and goes red only when the behaviour changes |
| Choice rejected as too large | Lower `observation.max_elements` |
| Page needs an existing login session | `browser.storage_state`, or attach to a logged-in Chrome (`--cdp-url http://127.0.0.1:9222`); recipe in `references/spec-format.md` |
| Elements inside iframes are missing | Main frame only for now; `references/runner-design.md` says how to extend |

## Files

- `scripts/run_test.py` (one spec → `result.json` + `trace.json`), `run_suite.py` (specs × repeats → `results.json`
  + `results.md`), `report.py` (a run → `report.html`), `spec.py` (validation), `summarize_trace.py`, `selftest.py`
  (offline check), `unit_tests.py`, `bench.py` (N repeats, medians), and the pieces `observe.py`, `policy.py`,
  `rules.py`, `jev_client.py` (read `references/runner-design.md` before changing them).
- `references/spec-format.md`, `trace-format.md`, `verdict-rubric.md`, `runner-design.md`.
- `specs/smoke-login.json`, `specs/smoke-login-badpw.json` (the demo-site smoke specs); `specs/examples/*.json`,
  ten specs against public sites: a shop checkout in four variants (two with the accounts the site documents as
  broken, one of them an `expect` spec), an encyclopedia search with a real autocomplete, a todo app, a 5 s loader,
  a random notification (`text_in` on the notification), a modal on load, a menu that drops an entry at random.
  Copy one as the starting point for your own app. README.md "Examples" has the table.
- `assets/spec.example.json` — a realistic spec with login in `setup` and a Jev-driven goal.
