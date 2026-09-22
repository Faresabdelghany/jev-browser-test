---
name: jev-browser-test
description: Goal-driven end-to-end browser testing where Claude writes the test spec and judges the result, TypeSafe's Jev decision model picks every click/type/scroll from a numbered element table (jev-ultrafast style), and Playwright executes. Use this whenever the user wants to test, verify, smoke-test, regression-test or explore a web UI flow (login, signup, checkout, search, forms, CRUD screens, admin panels) with Jev or TypeSafe, mentions jev-ultrafast or browser-use with Jev, asks for "fast/cheap AI browser tests", wants E2E tests that survive selector or layout changes, or needs fuzzy UI assertions like "the error message tells the user their card was declined". Also use it to triage an existing run (a trace.json or runs/ folder) into pass / product bug / test issue / flaky. Do not use it for unit tests, API tests, or flows with fully stable selectors where plain Playwright already works.
---

# Jev browser test

Claude is the brain, Jev is the hands, Playwright is the body.

- **Claude (you)** writes the test *spec* before the run and judges the *trace* after it. You never sit
  inside the step loop, so a 30-step flow costs you two turns of thinking, not thirty.
- **Jev** (TypeSafe's System One model) makes one typed decision per step: which operation, which numbered
  element, which prepared value. Measured on the demo login (`scripts/bench.py`, 5 repeats): ~0.3 s per
  decision on the warm connection (~0.8 s for the first request of a run), one request carrying the
  operation, targets and all checks, ~1.3k tokens per step; the browser's execute-and-settle is ~0.15 s
  per action, so a 3-action flow is ~5 s of which ~2 s is the site's own page load. Jev cannot invent an
  action that is not on the page because it only ever chooses from options the runner offers.
- **Playwright** turns the live page into a numbered element table and executes the chosen action.

Only a result comes back to you: `result.json` names exactly **one of the outcomes your spec declared**
(with the verdict you attached to it when you wrote the spec, and the line of the page that proves it) or
`undetermined` with a typed reason (`blocked`, `stuck`, low confidence, a page that would not hold still, a
budget running out) and a suggested verdict. The runner is deterministic given Jev's answers, which is what
makes the trace behind the result usable as evidence.

The loop this skill exists for: **ticket or flow → Claude writes the spec → Jev runs it → Claude judges →
if BUG, Claude fixes the code → the same spec re-runs green → PR.** Steps 1–4 below get you to the
verdict; step 5 is the half that produces value. Do not stop at the verdict when a repo is available.

## When Jev earns its place

Use plain Playwright (or a `setup` step) for anything with a stable selector that is *not* what you are
testing: login, dismissing a known banner, seeding data. Jev adds latency there and no value. Jev earns
its place where a human would have to look at the screen and decide:

- the flow is described as a goal, not a script ("create an order for Acme Ltd and save it");
- the UI changes often, so selector-based tests keep breaking;
- the assertion is fuzzy ("a success toast confirms the save", "the error explains the card was declined");
- you want to explore a screen for breakage without knowing its structure in advance.

Mixing is the normal case: deterministic `setup`, then a Jev-driven goal, then Noul checks as assertions.

## Workflow

### 0. Environment (once per machine)

```bash
pip install -r scripts/requirements.txt && python -m playwright install chromium
python scripts/selftest.py            # offline: local page + fake Jev, proves the loop works, no credit spent
export TYPESAFE_API_KEY=...           # https://console.typesafe.ai/keys ; or put it in ./.env, the runner loads it
```

The key must be an environment variable (or in a `.env` in the working directory, which the runner loads itself). Never write it into a spec
file or a command you echo back. If the `typesafe-ai` plugin skill is installed, it is the reference for
anything about the API itself; this skill only needs `POST /v1/systemone` with Choice and Noul questions.

### 1. Write the spec

Read `references/spec-format.md` the first time, then write `specs/<id>.json`. What you are really writing:

- **goal** — what you would tell a tester in one breath, ending with the visible outcome.
- **data** — every string the flow might need to type. Jev chooses *which* value to type; it never writes
  text. A value that is missing surfaces as `BLOCKED` and comes back to you. Credentials go through
  `${ENV_VAR}` and `secrets`, and preferably through `setup` so they never reach Jev at all.
- **outcomes** — the endings you will accept back, each a statement about the visible page and the
  verdict you give if it is seen: the acceptance criteria as the `pass` outcome, the wrong behaviour you
  are testing for (or the ticket reports) as `bug`, a CAPTCHA or approval step as `needs_human`. Every
  step Jev picks one of them (or `none_yet`); a pass is re-checked after a settle, any other verdict ends
  the run at first sighting. A negative test declares the rejection as its `pass` and the success as the
  `bug`, with a `note` saying so. This is the whole point: the run comes back as *one of your outcomes*.
- **assert** — exact expectations checked in code on the final page before a pass counts: the URL glob,
  a text the page must contain, a field's value, an element that must (not) be there. Free and non-model.
- **checks** — atomic statements about what is *visible* ("The cart shows 1 item"), one fact each; Jev
  returns a probability for each on every step. They are the progress signals that show *where* a run
  diverged, and an outcome's `requires` can lean on them.
- **done_when / never** — shorthand for a `pass` outcome (`goal_reached`) and `bug` outcomes
  (`never_<check>`) when you do not spell out `outcomes`. Older specs keep working unchanged.
- **setup** — deterministic Playwright steps for preconditions.

Validate: `python scripts/spec.py specs/<id>.json`. Ask the user only for what you cannot infer from the
repo or conversation (start URL, test account, the app's own wording for success), and state the
assumptions you made inline instead of stopping.

### 2. Run

```bash
python scripts/run_test.py specs/<id>.json                 # -> runs/<id>/<timestamp>/trace.json + steps/*.png
python scripts/run_test.py specs/<id>.json --headed        # watch it, when debugging locally
```

Exit 0 = the run ended in an outcome with verdict `pass`, 1 = any other outcome or `undetermined`, 2 = spec
or environment problem (fix that first; it is never a bug). Launch it and do nothing until it returns: the
runner confirms a pass, stops at the first sighting of anything else, and writes the verdict for you.
Runs are cheap: a 20-step flow is roughly 20 Jev calls at a fraction of a cent, so rerun freely, but read
the result before rerunning, or you throw away the evidence of why it failed.

### 3. Read the result, then the trace

```bash
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --result  # result.json: outcome, verdict, evidence
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json           # one line per step + flags
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --step 7  # full detail for one step
```

`result.json` is the file to read first: `outcome` (one of your names, or `undetermined`), `verdict`,
`evidence.line` (the page's own words, selected by Jev and copied verbatim), `path_confidence` (the
weakest decision on the way), `assertions`, `story`, and for `undetermined` the `reason` with a typed cause
and a `suggested_verdict`. Open the step table only for `undetermined` or to sanity-check a surprising
outcome. Then look at the pictures. With the default `screenshots: "key"` the terminal step and every flagged step
(`outcome_seen`, `pending_outcome`, `outcome_unconfirmed`, `never_violated`, `low_confidence`, `stale`,
`repeat_count ≥ 2`) have a `steps/NNN.png` of the page Jev
decided on (taken after its answer, before the action), a failed action leaves `NNN-failed.png`, and
`steps/final.png` shows where the run ended. The step *before* a divergence usually has no picture: its
element table and probabilities are in `--step N`, and `--screenshots all` gives every step a picture on a
rerun. `references/trace-format.md` explains every field and status. The single most important reading
rule: the checks recorded in step *n* describe the page **before** action *n*; action *n*'s effect shows in
step *n+1*.

### 4. Judge and report

Follow `references/verdict-rubric.md`. Exactly one verdict per run: **PASS**, **BUG**, **TEST_ISSUE**,
**FLAKY**, or **NEEDS_HUMAN**. When the result names one of your outcomes, the verdict is the one you
declared: sanity-check it against `evidence.line` and the screenshot, and if the label does not fit what
you see, the spec mislabelled it (fix the `when` or the `verdict`, rerun, say so). When the result is
`undetermined`, start from `reason.suggested_verdict` and apply the rubric: a red run is a bug only when the
action was reasonable (`path_confidence` above `min_confidence`, a sensible element on a sensible page) and
the next page shows the app misbehaving; it is a test issue when the spec caused it: missing data value,
unreachable outcome, banner that belonged in `setup`, ambiguous goal. Fix the spec and rerun (at most twice)
before reporting a test issue. Never call a single run flaky; rerun and compare.

Report with the template in the rubric: verdict, one-line flow, result numbers, the story in 2–4 sentences,
the evidence (step number, action, confidence, check value, screenshot path), what was expected, and the next
step. If the verdict is BUG and the user has an issue tracker connected, offer to file it with that block.

### 5. Close the loop: fix, re-run, ship

The verdict is not the end of the job; it is the hand-off to the part only Claude can do. The whole
point of putting Jev in the loop is that a BUG comes back to a brain that can fix it, and the spec that
found it becomes the regression test that proves the fix.

When the verdict is **BUG** and the app's repository is available to you:

1. **Locate.** Use the trace as your reproduction: the URL, the element Jev clicked (`target.label`), the
   check that failed or the `never` that fired, and the visible error text in `visible_text`. Grep the repo
   for the error string, the route, the component name in the screenshot. You are looking for the code
   path a user hits when they do what Jev did.
2. **Fix it** the way you would fix any bug in that codebase: its conventions, its tests, any review skill
   the user has installed. Keep the change scoped to the defect the trace shows. Never change the app to
   make a wrong spec pass; if the spec is wrong, that is a TEST_ISSUE and the fix goes in `specs/`.
3. **Re-run the same spec** against the fixed build (local dev server, preview deploy). The run that was
   red must now be green with the same actions. If the fix needed a spec change too, say so; a spec that
   had to be loosened to pass is a warning sign, not a fix.
4. **Report and ship.** The fix summary, the failing trace, the passing trace, and the before/after
   summary tables are the evidence for the PR and the ticket update. Offer to open the PR and update the
   ticket; do not do either without asking.

When the verdict is **TEST_ISSUE**, the fix is in the spec (at most two revisions, then NEEDS_HUMAN).
When it is **FLAKY**, the fix is usually a `wait_for` in `setup` or a check anchored on better text.
When it is **NEEDS_HUMAN**, stop and ask the specific question the rubric tells you to ask.

### Starting from a ticket

If the user hands you a Linear/Jira issue or a bug report instead of a flow, write the spec from it:

- **goal** = the user story or the reproduction steps, in one breath, ending at the visible outcome.
- the acceptance criteria as the **`pass` outcome** (its `when` in the app's own words) with the exact
  expectations in **`assert`**; one **check** per criterion when there are several, and `requires` them;
- the reported wrong behaviour as a **`bug` outcome** (for a bug ticket) so the run fails for the right
  reason and comes back with the error text as its evidence line.

A bug ticket's spec should come back **BUG before the fix and PASS after** — that is the definition of
done for the fix, and the spec stays in `specs/` as the regression test for that ticket. For a feature
ticket, the spec is the acceptance test: write it from the criteria before the code exists, expect the
`bug` outcome or `undetermined` (`blocked`) until the feature lands, and PASS when it does.

## Triage-only mode

If the user hands you an existing `trace.json` or `runs/` folder, skip to steps 3–4. Do not rerun anything
unless the rubric says to (suspected flake, or after a spec fix you made).

## Suites: anything longer than one spec

For several flows, or to know whether one flow is stable, write one spec per flow in `specs/` and let the
suite runner do the waiting:

```bash
python scripts/run_suite.py specs/*.json --repeat 3 --workers 4      # -> runs/suite/<ts>/results.json + results.md
```

Launch it with the Bash tool's `run_in_background` and **do nothing until the completion notification**:
no polling, no reading partial output, no thinking about the flow while it runs. Then read
`results.json` (or `results.md`). Per spec it gives the outcome distribution across the repeats, the
agreement rate, medians, and a suite verdict: unanimous → that outcome's verdict; any disagreement →
**`flaky`**, computed, never diagnosed from one run. Exit 0 iff every spec is unanimously `pass`. Open a
trace only for a spec that is `undetermined` or `flaky`; a unanimous declared outcome needs at most a glance
at its `evidence_line`. Two specs × 5 repeats with 4 workers finish in well under a minute on the demo site.

For a human reader (a PR, a ticket), `python scripts/report.py runs/<id>/<ts>` writes a single static
`report.html` beside the trace: the result, the step table with the operation and target probabilities,
checks, outcome answers, flags, and the screenshots inline. No server, no external resources. Given a suite
directory (`python scripts/report.py runs/suite/<ts>`) it writes one per run; the paths in `results.json`
are relative to that directory, so it still works after the directory has been moved.

Keep specs independent (each has its own `setup`); shared state between specs is the fastest way to
manufacture flakiness. Store `runs/` outside version control.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TYPESAFE_API_KEY is not set` | Export the key or put it in `.env` in the directory you run from; the installed TypeSafe plugin does not provide one |
| exit 2 with "Spec problems" | Read the list; usually a `done_when` naming an unknown check, a check written as a question, or a missing `${ENV}` |
| `error` with `setup[i] failed` | The selector in a setup step did not match; fix it or move that step into the goal |
| `blocked` right after a text field appears | Add the needed value to `data` (`reason.blocked_reason` says `missing_data_value`) |
| `assert_failed` | A pass outcome was confirmed but an assertion did not hold: `reason.failed_assertions` has the actual values. Decide whether the assertion or the app is wrong; never loosen it silently |
| The outcome that came back does not match what the screenshot shows | The spec mislabelled it: fix that outcome's `when` or `verdict` (one line), rerun, and say so in the report |
| Two outcomes hover at 0.4–0.5 while the page clearly shows one of them | Their `when` statements are both true of that page; reword them so they are distinguishable on sight (name a string unique to each) |
| `low_confidence` with `type_value` split between two keys | Rename `data` keys to the field labels the app shows; Jev refused to guess which value went where (nothing was typed) |
| A `never` check sits at 0.7–0.8 for several steps | The statement half-matches the page; reuse the app's exact wording instead of lowering `never_true` |
| `stuck` on the same button | Look at the screenshot: dead control (bug) or a modal Jev cannot see past (add a note or setup step) |
| `stuck` with confidence ≈ `min_confidence` and flat target probabilities | Jev is saying "the thing I need is not in the table". Check the element table for that step: if the control is missing, it is a non-semantic clickable the observer skipped (the `cursor: pointer` pass catches most; a `div` with no cursor hint needs a `setup` click or an ARIA role in the app). Verdict TEST_ISSUE, not BUG — but note the missing role for accessibility |
| `low_confidence` with the target split over several elements that carry the **same label** (`[8] button "Add to cart"`, `[9] button "Add to cart"`, …) | Jev cannot tell identical controls apart and refuses to guess. The observer describes such controls by the card, row or entry that distinguishes them (`button "Add to cart" in "Bolt T-Shirt …"`); if the table still shows bare duplicates, their containers carry no distinguishing text: say in `notes` which one by position ("the third Add to cart button"), or script that click in `setup` |
| `stuck` clicking a table row *confidently* | The row was the best thing on offer: the real control (a selection checkbox, an inline action) is missing from the table. Hidden-input checkboxes are now observed with their row text; if a control is still absent, script that one step in `setup`. Canvas content (maps) is never observable |
| `budget_exhausted` with `reason.stuck_reason: still_loading` | The page was still loading when the budget ran out (Jev kept choosing WAIT, which never counts as `stuck`). Rerun once; if it repeats, raise `budget.max_steps` / `max_seconds` for a slow page, or suspect the app: a loader that never completes is a bug |
| `unstable_page` | The page never held still: every decision went stale before it could be executed (`step.stale` says what moved each time). Environment, not a bug: raise `browser.quiet_ms` / `settle_ms`, or add a `setup` `wait_for` for the thing that keeps changing |
| Setup is most of the wall-clock | Replace `wait {ms}` with `wait_for {selector}` / `wait_for {url}` |
| Choice rejected as too large | Lower `observation.max_elements` |
| Page needs an existing login session | Save a Playwright `storage_state` once and point `browser.storage_state` at it. For SSO or hardware-token logins, run inside a browser you are already logged into: start Chrome with `--remote-debugging-port=9222` and pass `--cdp-url http://127.0.0.1:9222` (or set `browser.cdp_url`); `storage_state` is ignored when attached. Recipe in `references/spec-format.md`, "Attach to a running browser" |
| Elements inside iframes are missing | Main frame only for now; see `references/runner-design.md` to extend |

## Files

- `scripts/run_test.py` — the loop (one spec → `result.json` + `trace.json`); `scripts/run_suite.py` — many
  specs × repeats on a worker pool → `results.json` + `results.md`; `scripts/report.py` — one run → static
  `report.html`; `scripts/spec.py` — validation; `scripts/summarize_trace.py` — reading runs;
  `scripts/selftest.py` — offline check; `scripts/unit_tests.py` — unit tests for the pure parts;
  `scripts/bench.py` — repeat a spec N times and report medians; `scripts/observe.py`, `scripts/policy.py`,
  `scripts/rules.py`, `scripts/jev_client.py` — the pieces (see `references/runner-design.md` before
  modifying them).
- `references/spec-format.md`, `references/trace-format.md`, `references/verdict-rubric.md`,
  `references/runner-design.md`.
- `assets/spec.example.json` — a realistic spec with login in `setup` and a Jev-driven goal.
