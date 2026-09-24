# jev-browser-test

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill for goal-driven end-to-end browser tests.
Claude writes the test spec and judges the result, [TypeSafe's Jev](https://docs.typesafe.ai/introduction) picks
every click, keystroke and scroll from a numbered element table (one ~0.3 s request per decision), and Playwright
executes.

```
Claude  →  spec.json  →  runner loop (Jev decides, Playwright acts)  →  result.json  →  Claude judges
```

A spec is a goal in plain language plus the endings the run may reach, each with its verdict declared in advance.
A run comes back as exactly one of those endings, with the page's own words as evidence, so Claude can judge a run it
never sat inside. Jev never generates text: every string it types comes from the spec's `data`. A spec that found a
bug stays as its regression test.

## Install

This repository is the skill (`SKILL.md` at the root, `scripts/`, `references/`, `specs/`):

```bash
# personal skill, every project on this machine
git clone https://github.com/Faresabdelghany/jev-browser-test ~/.claude/skills/jev-browser-test

# or a project skill, committed with the repository you are testing
git clone https://github.com/Faresabdelghany/jev-browser-test .claude/skills/jev-browser-test

# or a plugin, from inside Claude Code
/plugin marketplace add Faresabdelghany/jev-browser-test
/plugin install jev-browser-test@jev-browser-test
```

Claude.ai and Claude Desktop take the same folder zipped as a `.skill` file. Then, once per machine, give the skill its
own Python with Playwright and a TypeSafe key:

```bash
cd ~/.claude/skills/jev-browser-test
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/selftest.py       # offline check, ~1 min, must end SELFTEST OK
export TYPESAFE_API_KEY=...                # https://console.typesafe.ai/keys, or a .env in the project
```

Keep real credentials out of specs: use `${ENV_VAR}` in `data`, list the key under `secrets`, or better, log in with
plain Playwright in `setup` so the credential never reaches Jev.

## Use

In Claude Code, ask for the test in plain words ("test the checkout of our shop with Jev", "is this page flaky?",
"triage this run folder"); `/jev-browser-test headed ...` shows the browser. The scripts behind it:

```bash
python scripts/scaffold.py --url URL --goal '... so that <the visible outcome>' --data key=value --out specs/<id>.json
python scripts/run_test.py specs/<id>.json                 # one run -> runs/<id>/<ts>/result.json + trace.json + screenshots
python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --result
python scripts/run_suite.py specs/*.json --repeat 3        # specs x repeats -> results.md with a computed flaky verdict
python scripts/report.py runs/<id>/<ts>                    # a self-contained report.html
```

`python` is the skill's `.venv/bin/python`; specs and runs live in the project you are testing. A spec:

```json
{
  "id": "smoke-login",
  "start_url": "https://the-internet.herokuapp.com/login",
  "goal": "Log in with the provided username and password, so that the Secure Area page is shown.",
  "data": { "username": "tomsmith", "password": "SuperSecretPassword!" },
  "outcomes": {
    "logged_in":       { "when": "The page heading says 'Secure Area' and a green flash message says 'You logged into a secure area!'", "verdict": "pass" },
    "bad_credentials": { "when": "A red flash message says the username or password is invalid", "verdict": "bug" }
  },
  "assert": [ { "url_matches": "**/secure" }, { "text_contains": "You logged into a secure area!" } ]
}
```

`result.json` names the outcome, its verdict, the line of the page that proves it, the assertions and the story of the
actions; `undetermined` comes with a typed reason and a suggested verdict. Exit code 0 is a pass, 1 anything else, 2 a
spec or environment problem. `SKILL.md` is what Claude follows (how to write a spec, run it, read the result, judge it
as PASS / BUG / TEST_ISSUE / FLAKY / NEEDS_HUMAN, and close the loop); `references/` has the spec format, the trace
format, the verdict rubric and the runner design.

## Examples

`specs/examples/` holds twenty-two specs against public demo sites: a shop checkout (including the accounts the site
documents as broken), a search with a real autocomplete, a todo app, forms, loaders, a modal, a random notification,
and an admin single-page app under loading overlays. [`specs/examples/README.md`](specs/examples/README.md) says what
each one exercises and the result to expect. Run them all with:

```bash
python scripts/run_suite.py specs/examples/*.json --repeat 3 --workers 2   # the hrm-* specs on one worker
```

Keep specs for a private application under `specs/local/` (git-ignored).

## Speed and cost

The demo login (three actions) takes about 5 s a run, of which 2 s is the site's own page load: 5 Jev requests of
~0.3 s and ~6k input tokens. Rerunning a finished spec costs Claude a few thousand tokens, against tens of thousands for
driving the same flow step by step with a snapshot tool. Every number, and how it was measured, is in
[`docs/superpowers/measurements/README.md`](docs/superpowers/measurements/README.md).

## Layout

```
SKILL.md          the instructions Claude loads
scripts/          scaffold, run_test, run_suite, report, summarize_trace, spec, bench, selftest, unit_tests;
                  observe / policy / rules / jev_client are the runner's parts
references/       spec-format, trace-format, verdict-rubric, suites, troubleshooting, runner-design
specs/            two smoke specs; examples/ (public sites), compare/ (the Jev vs Playwright-CLI comparison)
evals/            the skill's eval prompts and their input files
docs/superpowers/ design spec, plans and the measurement files
```

Related: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) uses the same observe → choose →
act loop; this runner drops the text model from the loop and adds the spec and result contract so Claude can judge
runs it never sat inside.
