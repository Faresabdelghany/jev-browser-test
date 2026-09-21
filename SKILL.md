---
name: jev-browser-test
description: Goal-driven end-to-end browser testing where Claude writes the test spec and judges the result, TypeSafe's Jev decision model picks every click/type/scroll from a numbered element table (jev-ultrafast style), and Playwright executes. Use this whenever the user wants to test, verify, smoke-test, regression-test or explore a web UI flow (login, signup, checkout, search, forms, CRUD screens, admin panels) with Jev or TypeSafe, mentions jev-ultrafast or browser-use with Jev, asks for "fast/cheap AI browser tests", wants E2E tests that survive selector or layout changes, or needs fuzzy UI assertions like "the error message tells the user their card was declined". Also use it to triage an existing run (a trace.json or runs/ folder) into pass / product bug / test issue / flaky. Do not use it for unit tests, API tests, or flows with fully stable selectors where plain Playwright already works.
---

# Jev browser test

Claude is the brain, Jev is the hands, Playwright is the body.

- **Claude (you)** writes the test *spec* before the run and judges the *trace* after it. You never sit
  inside the step loop, so a 30-step flow costs you two turns of thinking, not thirty.
- **Jev** (TypeSafe's System One model) makes one typed decision per step: which operation, which numbered
  element, which prepared value. Measured on a real app: ~0.7–1.8 s per decision (median ~0.9 s, one
  request carrying the operation, targets and all checks), ~1.8k tokens per step; Playwright's observe
  and act is the bigger cost at ~2.4 s. Jev cannot invent an action that is not on the page because it
  only ever chooses from options the runner offers.
- **Playwright** turns the live page into a numbered element table and executes the chosen action.

Only the outcomes come back to you: `passed`, `blocked`, a `never` check firing, low confidence, a stuck
loop, or a budget running out. The runner is deterministic given Jev's answers, which is what makes the
trace usable as evidence.

## When Jev earns its place

Use plain Playwright (or a `setup` step) for anything with a stable selector that is *not* what you are
testing: login, dismissing a known banner, seeding data. Jev adds latency there and no value. Jev earns
its place where a human would have to look at the screen and decide:

- the flow is described as a goal, not a script ("create a pickup order for Nile Bakery and save it");
- the UI changes often, so selector-based tests keep breaking;
- the assertion is fuzzy ("a success toast confirms the save", "the error explains the card was declined");
- you want to explore a screen for breakage without knowing its structure in advance.

Mixing is the normal case: deterministic `setup`, then a Jev-driven goal, then Noul checks as assertions.

## Workflow

### 0. Environment (once per machine)

```bash
pip install -r scripts/requirements.txt && python -m playwright install chromium
python scripts/selftest.py            # offline: local page + fake Jev, proves the loop works, no credit spent
export TYPESAFE_API_KEY=...           # https://console.typesafe.ai/keys ; the runner reads it from the env
```

The key must be an environment variable (or in a `.env` the user sources). Never write it into a spec
file or a command you echo back. If the `typesafe-ai` plugin skill is installed, it is the reference for
anything about the API itself; this skill only needs `POST /v1/systemone` with Choice and Noul questions.

### 1. Write the spec

Read `references/spec-format.md` the first time, then write `specs/<id>.json`. What you are really writing:

- **goal** — what you would tell a tester in one breath, ending with the visible outcome.
- **data** — every string the flow might need to type. Jev chooses *which* value to type; it never writes
  text. A value that is missing surfaces as `BLOCKED` and comes back to you. Credentials go through
  `${ENV_VAR}` and `secrets`, and preferably through `setup` so they never reach Jev at all.
- **checks** — atomic statements about what is *visible* ("The cart shows 1 item"), one fact each.
  These are the assertions; Jev returns a probability for each on every step.
- **done_when / never** — which checks define success, which ones mean "stop, something is wrong".
  Always include an error-visible style check in `never`.
- **setup** — deterministic Playwright steps for preconditions.

Validate: `python scripts/spec.py specs/<id>.json`. Ask the user only for what you cannot infer from the
repo or conversation (start URL, test account, the app's own wording for success), and state the
assumptions you made inline instead of stopping.

### 2. Run

```bash
python scripts/run_test.py specs/<id>.json                 # -> runs/<id>/<timestamp>/trace.json + steps/*.png
python scripts/run_test.py specs/<id>.json --headed        # watch it, when debugging locally
```

Exit 0 = passed, 1 = did not pass, 2 = spec or environment problem (fix that first; it is never a bug).
Runs are cheap: a 20-step flow is roughly 20 Jev calls at a fraction of a cent, so rerun freely, but
read the trace before rerunning, or you throw away the evidence of why it failed.

### 3. Read the trace

```bash
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json           # one line per step + flags
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --step 7  # full detail for one step
```

Then look at the screenshots for the step where the run diverged and at `steps/final.png` (use your
image viewing; the PNGs are what the page looked like before each decision). `references/trace-format.md`
explains every field and status. The single most important reading rule: the checks recorded in step *n*
describe the page **before** action *n*; action *n*'s effect shows in step *n+1*.

### 4. Judge and report

Follow `references/verdict-rubric.md`. Exactly one verdict per run: **PASS**, **BUG**, **TEST_ISSUE**,
**FLAKY**, or **NEEDS_HUMAN**. A red run is a bug only when the action was reasonable (confidence above
`min_confidence`, a sensible element on a sensible page) and the *next* page shows the app misbehaving.
A red run is a test issue when the spec caused it: missing data value, unreachable check, banner that
belonged in `setup`, ambiguous goal. Fix the spec and rerun (at most twice) before reporting a test issue.
Never call a single run flaky; rerun and compare.

Report with the template in the rubric: verdict, one-line flow, result numbers, the story in 2–4 sentences,
the evidence (step number, action, confidence, check value, screenshot path), what was expected, and the next
step. If the verdict is BUG and the user has an issue tracker connected, offer to file it with that block.

## Triage-only mode

If the user hands you an existing `trace.json` or `runs/` folder, skip to steps 3–4. Do not rerun anything
unless the rubric says to (suspected flake, or after a spec fix you made).

## Suites

For several flows, write one spec per flow in `specs/`, and a tiny shell loop or Makefile target that runs
them and collects exit codes. Keep specs independent (each has its own `setup`); shared state between specs
is the fastest way to manufacture flakiness. Store `runs/` outside version control.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TYPESAFE_API_KEY is not set` | Export the key or source the `.env`; the installed TypeSafe plugin does not provide one |
| exit 2 with "Spec problems" | Read the list; usually a `done_when` naming an unknown check, a check written as a question, or a missing `${ENV}` |
| `error` with `setup[i] failed` | The selector in a setup step did not match; fix it or move that step into the goal |
| `blocked` right after a text field appears | Add the needed value to `data` |
| `low_confidence` with `type_value` split between two keys | Rename `data` keys to the field labels the app shows; Jev refused to guess which value went where (nothing was typed) |
| A `never` check sits at 0.7–0.8 for several steps | The statement half-matches the page; reuse the app's exact wording instead of lowering `never_true` |
| `stuck` on the same button | Look at the screenshot: dead control (bug) or a modal Jev cannot see past (add a note or setup step) |
| `stuck` with confidence ≈ `min_confidence` and flat target probabilities | Jev is saying "the thing I need is not in the table". Check the element table for that step: if the control is missing, it is a non-semantic clickable the observer skipped (the `cursor: pointer` pass catches most; a `div` with no cursor hint needs a `setup` click or an ARIA role in the app). Verdict TEST_ISSUE, not BUG — but note the missing role for accessibility |
| `stuck` clicking a table row *confidently* | The row was the best thing on offer: the real control (a selection checkbox, an inline action) is missing from the table. Hidden-input checkboxes are now observed with their row text; if a control is still absent, script that one step in `setup`. Canvas content (maps) is never observable |
| Setup is most of the wall-clock | Replace `wait {ms}` with `wait_for {selector}` / `wait_for {url}` |
| Choice rejected as too large | Lower `observation.max_elements` |
| Page needs an existing login session | Save a Playwright `storage_state` once and point `browser.storage_state` at it |
| Elements inside iframes are missing | Main frame only for now; see `references/runner-design.md` to extend |

## Files

- `scripts/run_test.py` — the loop; `scripts/spec.py` — validation; `scripts/summarize_trace.py` — reading
  runs; `scripts/selftest.py` — offline check; `scripts/observe.py`, `scripts/policy.py`,
  `scripts/jev_client.py` — the pieces (see `references/runner-design.md` before modifying them).
- `references/spec-format.md`, `references/trace-format.md`, `references/verdict-rubric.md`,
  `references/runner-design.md`.
- `assets/spec.example.json` — a realistic spec with login in `setup` and a Jev-driven goal.
