---
name: jev-browser-test
description: Goal-driven end-to-end browser testing where Claude writes the test spec and judges the result, TypeSafe's Jev decision model picks every click/type/scroll from a numbered element table (jev-ultrafast style, one ~0.3 s request per decision), and Playwright executes. Use this whenever the user wants to test, verify, smoke-test, regression-test or explore a web UI flow (login, signup, checkout, search, forms, CRUD screens, admin panels) with Jev or TypeSafe, mentions jev-ultrafast or browser-use with Jev, asks for "fast/cheap AI browser tests", wants E2E tests that survive selector or layout changes, or needs fuzzy UI assertions like "the error message tells the user their card was declined". Also use it to triage an existing run (a result.json, trace.json or runs/ folder) into PASS / BUG / TEST_ISSUE / FLAKY, to reproduce a bug ticket as a rerunnable spec, or to ask whether a page is flaky. Do not use it for unit tests, API tests, or flows with fully stable selectors where plain Playwright already works.
argument-hint: "[headed|headless] what to test"
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

Scaffold it, then edit; do not author it by hand (measured on 2026-09-24: a first run that read this skill and the
format reference and wrote three specs by hand cost ~72k Claude tokens, against ~19k for driving the same two flows
step by step with a snapshot tool; a rerun of the finished specs cost ~6k):

```bash
python $SKILL/scripts/scaffold.py --url https://app.example.com/ \
  --goal 'Open PIM, add an employee with the given names and save, so that the Personal Details page shows the name Jevtest Runner${RUN_STAMP}' \
  --data first_name=Jevtest --data 'last_name=Runner${RUN_STAMP}' \
  --setup 'fill:input[name=username]=Admin' --setup 'fill:input[name=password]=${HRM_PASSWORD}' \
  --setup 'click:button[type=submit]' --setup 'wait_for_url:**/dashboard/**' \
  --bug "A red 'Required' message is shown under a field after Save" \
  --assert-url '**/viewPersonalDetails/**' --assert-in '.orangehrm-edit-employee-name|Jevtest' --slow --out specs/<id>.json
```

Single quotes around anything with `${...}` (the shell must not expand it: the runner does, at run time).

It writes a spec that already validates (goal, data, a `pass` outcome from the goal's "so that" clause, your `bug`
outcomes with `requires_action`, the standing `app_error`, your assertions and setup steps, `--slow` for a slow
single-page app), prints `spec.py`'s summary, and leaves nothing invented: no assertion unless you gave one, `${ENV}`
kept for run time. Then edit the twenty lines that matter, guided by the field notes below; open
`references/spec-format.md` only for a field the scaffold's `comment` does not explain.

- **goal** — what you would tell a tester in one breath, ending with the visible outcome.
- **data** — every string the flow might type. Jev chooses *which* value; a missing one surfaces as `BLOCKED`.
  Credentials go through `${ENV_VAR}` + `secrets`, and preferably through `setup` so they never reach Jev. A
  credential the site itself publishes (a demo account printed on its login page) may be written plainly. Any
  value the app **keeps** (a username, a last name, a title, an id) gets **`${RUN_STAMP}`** in it
  (`"username": "jev${RUN_STAMP}"`): the runner substitutes a fresh eight-character stamp every run and repeat,
  so nothing collides with what an earlier run created, and `result.run_stamp` says which value it was. Export
  `RUN_STAMP=<value>` to rerun a spec against, or clean up after, one particular run's data.
- **outcomes** — the endings you accept back: the acceptance criteria as `pass`, the wrong behaviour you test for
  (or the ticket reports) as `bug`, a CAPTCHA or approval step as `needs_human`. A negative test declares the
  rejection as `pass` and the success as `bug`, with a `note`. Write each `when` as **one visible fact per
  sentence** (". " between sentences): that is what gets quoted as the evidence line. Put **`requires_action:
  true`** on any bug outcome that describes "nothing happened" (the list is still unsorted, the dialog is still
  open): such a statement is true of the untouched start page too, and the flag defers it until an action ran.
  When the ending only means something after a particular action, say which with **`after`**: `"after": {"click":
  "Search"}` holds a 'No Records Found' outcome until a click on Search has been executed (also `type`, `select`;
  several keys all have to hold), where `requires` on the filter checks was too weak.
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
python $SKILL/scripts/run_test.py specs/<id>.json --headed   # a window opens: when the user wants to watch
```

**Browser mode: the user chooses, you pass it on.** Invocation arguments: `$ARGUMENTS`. When their first word is
`headed` or `headless` (`/jev-browser-test headed test the login`), that is the mode for the rest of the
conversation and the remaining words are the request. Otherwise read the request itself: "show me", "watch",
"open the browser", "I want to see it" mean `--headed`; "in the background", "hide the browser" mean
`--headless`; nothing said means headless, the default. Pass the same flag to `run_suite.py` (a headed suite
with `--workers 1`: one window at a time). `JEV_HEADED=1` in the user's `.env` is a standing preference the
runner reads by itself; a flag beats it, and both beat the spec's `browser.headless`. The runner prints
`browser: headed` or `browser: headless (...)` on stderr as it launches and keeps the mode in
`trace.browser.headless`, so a window that no run announced is not this runner's. The first time you run in a
conversation, name the mode in one clause ("headless; say *headed* to watch"); never ask which.

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
verbatim; `live message: Successfully Saved` when it quotes a toast that had already faded), `confirmed_by`
(`assertions` or `recheck`), `path_confidence`, `assertions`, `announcements` (every toast and ARIA live message
the page showed during the run, with the step it preceded: what the app said about each action, kept even when it
was gone before the runner looked), `story`, and for `undetermined` the `reason` with its typed cause and
`suggested_verdict`; `expected` for a spec with `expect`.
`confirmed_by: recheck` on a spec that has assertions means the pass was not yet in sight when Jev chose DONE
(the outcome read below 0.8), so the runner took the checking step and saw it there: correct, one request more.
Open the step table only for `undetermined` or a surprising outcome. Flags worth knowing: `NO-EFFECT` (an
action landed and the page did not change: the classic dead control; the next step's picture shows it),
`DEFERRED:<outcome>` (true of the page, but its `requires_action` / `after` condition has not happened yet: not
counted), `COVERED:<n>` (controls on screen but under another layer, so not offered; plain, the layer is blank and the
form is still loading; `(layer:<m>)`, the layer has controls of its own, a dialog or an open list), `DEFERRED-<OP>:<n>` (a
marginal click or typing under a blank layer turned into a wait, again with backoff while the layer stays, five on one
page; `DEFER-LIMIT:5` when it then went ahead), `ANNOUNCED:"…"` (a toast or
live message appeared between the previous observation and this one; Jev saw it in its state for this and the next
two steps, faded or not), `SLOW-NAV:<s>` (the click landed; the page it asked for answered after the action timeout: a
slow host, not a failure), `RECHECK:<n>` / `ASSERT-PENDING:<n>` (a pass in sight on a page still busy, looked at again),
`LOW-CONF`, `STALE`, `EVIDENCE-ASKED`. With the
default `screenshots: "key"` the terminal step, every flagged step and the step after a no-effect action have a
`steps/NNN.png`; `--screenshots all` pictures every step on a rerun. The one reading rule: the checks recorded
in step *n* describe the page **before** action *n*; action *n*'s effect shows in step *n+1*. After a no-effect
action the check values in step *n+1* can drift toward what the action should have done (Jev sees the action in
its history); the element table, the page signature and the `NO-EFFECT` flag are the hard facts there.

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
**BUG before the fix and PASS after**, and stays in `specs/` as the regression test. Say how to rerun it. Two
habits make the first run the evidence run: `--screenshots all` (a ticket wants the picture of every step, and a
rerun for pictures is a wasted run), and a **control** with a known-good account or the flow's healthy sibling,
which shows in one run that the spec is sound and the defect is the app's.

## Triage-only mode

Handed a run folder (`result.json`, `trace.json`, screenshots), the answer is in it: skip to steps 3–4.

1. Read `result.json`, the step table, the pictures. **Do not launch a browser first.** Two things the typed
   reason does not tell you. After `control_had_no_effect`, read **every** `NO-EFFECT` flag in the table: the
   reason names the last dead control, and the first one is often earlier and changes the ticket (a Finish that
   does nothing behind an Add to cart that did nothing: the order was empty). And compare the spec as run
   (`trace.spec`) with the spec on disk or the skill's example of it: a missing `expect`, a changed outcome or
   `when` means the red may already be known, and the fix is in the spec, not the app.
2. "Is it flaky?" is answered from the trace's flake signatures: `STALE` steps, `executed.ok: false`, `RETRIED`,
   `usage.reconnects`, a `reason.phase`, an `error` status. None present, plus a confident declared outcome or a
   typed reason with a suggestion → deterministic evidence; say so and do not rerun. Rerun once only when a
   signature is present, the user asks, or after a spec fix you made; a rerun for pictures (`--screenshots all`)
   is that one rerun, so make it after the spec fix, not before it.
3. To separate TEST_ISSUE from BUG cheaply, run a **control**: the same spec with a known-good account, or the
   sibling spec known to pass. One run, ~10 Jev calls. Prefer it to reading the app's source, which was not asked
   for and rarely changes the verdict.
4. One triage = one reading, at most one rerun and one control. Report how many runs you made.

## Suites: anything longer than one spec

```bash
python $SKILL/scripts/run_suite.py specs/*.json --repeat 3 --workers 2   # -> runs/suite/<ts>/results.json + results.md
```

Launch it with the Bash tool's `run_in_background` and do nothing until the completion notification; then read
`results.md` (one suite verdict per spec: `pass`, `expected`, `bug`, ..., or the computed `flaky`). Open a trace only
for a spec that is `undetermined` or `flaky`. `references/suites.md` says how to read agreement and flakiness, which
kind of flaky it is (environment or an app that varies by design), and how to get a `report.html` for a human.

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

`references/troubleshooting.md` has the symptom table (read it when a run does not end the way the spec says). The
three you meet first: exit 2 is a spec or environment problem, never a bug (the message says which); a bug outcome
that fires before anything happened wants `requires_action: true` or `after` on it; `low_confidence` over two data
keys or two same-named elements wants keys named like the app's labels, or a `notes` sentence saying which one.

## Files

- `scripts/scaffold.py` (URL + goal + data → a valid spec to edit), `run_test.py` (one spec → `result.json` +
  `trace.json`), `run_suite.py` (specs × repeats → `results.json` + `results.md`), `report.py` (a run →
  `report.html`), `spec.py` (validation), `summarize_trace.py`, `selftest.py` (offline check), `unit_tests.py`,
  `bench.py` (N repeats, medians), and the pieces `observe.py`, `policy.py`, `rules.py`, `jev_client.py` (read
  `references/runner-design.md` before changing them).
- `references/spec-format.md` (every field), `troubleshooting.md` (symptom → fix), `suites.md` (agreement, flakiness,
  reports), `trace-format.md`, `verdict-rubric.md`, `runner-design.md`.
- `specs/smoke-login.json`, `specs/smoke-login-badpw.json` (the demo-site smoke specs); `specs/examples/*.json`,
  twenty-two specs against public sites: a shop checkout in four variants (two with the accounts the site documents as
  broken, one of them an `expect` spec), an encyclopedia search with a real autocomplete, a todo app, a 5 s loader,
  a random notification (`text_in` on the notification), a modal on load, a menu that drops an entry at random, a
  static web form (select, checkbox, radio, the GET query asserted), add/remove elements (a count asserted with
  `text_in` `equals`), two asynchronous controls with loaders, a forgot-password form that answers with a server
  error (expected-red), a Jev-typed login and logout, an admin panel's own login typed by Jev, sortable table headers with no affordance (an expected
  TEST_ISSUE: what a control Jev cannot see looks like), an admin panel's Add Employee behind loading overlays
  (`covered_controls`, `settle_ms` raised for a slow demo), a shop's search-to-cart, and three more admin-panel flows
  (a user with a role and a password, a leave assignment confirmed by toasts, an employee added then found in a list)
  that keep their data unique with `${RUN_STAMP}`. Copy one as the starting point for your own app. README.md
  "Examples" has the table.
- `assets/spec.example.json` — a realistic spec with login in `setup` and a Jev-driven goal.
