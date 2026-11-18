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
git clone --depth 1 https://github.com/Faresabdelghany/jev-browser-test ~/.claude/skills/jev-browser-test

# or a project skill, committed with the repository you are testing
git clone --depth 1 https://github.com/Faresabdelghany/jev-browser-test .claude/skills/jev-browser-test

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

On Windows the interpreter is `.venv\Scripts\python.exe` (`python -m venv .venv` creates it); everything else is the
same, from Git Bash or PowerShell.

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
python scripts/run_suite.py specs/*.json --junit junit.xml # the same, plus a JUnit report for a CI dashboard
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

A spec can also declare, each in a line or two ([`references/spec-format.md`](references/spec-format.md) has them all):

| | |
|---|---|
| `teardown` | scripted steps after the verdict, whatever it was: delete what the run created |
| `setup` steps `upload`, `hover`, `drag`, `"frame"` | interactions scripted as preconditions; selectors reach into shadow DOM |
| `observation.frames` | iframes whose controls Jev may use: a card form, an embedded widget |
| `observation.shadow_dom` | on by default: Jev sees and uses the controls inside web components (`false` turns it off) |
| `files` | files Jev may attach to a file field, hidden ones included |
| `extra_operations: ["HOVER"]` | Jev may hover to open a menu that only shows on hover |
| `browser.device` | a phone or tablet: `"iPhone 13"`, `"Pixel 7"` (also `--device`) |
| `browser.follow_new_tabs` | carry on in the tab a click opens |
| `no_page_errors`, `no_failed_requests` | assertions on what the browser recorded: no uncaught exception, no 5xx, no failed request |

Every run also records the browser's own diagnostics (JavaScript exceptions, failed requests, 4xx and 5xx responses)
beside what the page showed, so a bug report can say what was behind a button that did nothing.

## Examples

`specs/examples/` holds twenty-two specs against public demo sites: a shop checkout (including the accounts the site
documents as broken), a search with a real autocomplete, a todo app, forms, loaders, a modal, a random notification,
and an admin single-page app under loading overlays. [`specs/examples/README.md`](specs/examples/README.md) says what
each one exercises and the result to expect. Run them all with:

```bash
python scripts/run_suite.py specs/examples/*.json --repeat 3 --workers 2   # the hrm-* specs on one worker
python scripts/run_suite.py specs/examples/*.json --replay                 # again, walking the paths the passes saved
```

Keep specs for a private application under `specs/local/` (git-ignored).

## Speed and cost

The demo login (three actions) takes about 5 s a run, of which 2 s is the site's own page load: 5 Jev requests of
~0.3 s and ~6k input tokens. Rerunning a finished spec costs Claude a few thousand tokens, against tens of thousands for
driving the same flow step by step with a snapshot tool. A rerun with `--replay` walks the path the last passing run
saved and asks Jev once, about the ending: the shop checkout goes from 10 requests and 5.2 s to 1 request and 3.5 s,
and the 22 examples from 190 requests to 53 (the rest are specs that do not end in a pass). Every number, and how it was measured, is in
[`docs/superpowers/measurements/README.md`](https://github.com/Faresabdelghany/jev-browser-test/blob/dev-docs/docs/superpowers/measurements/README.md) on the `dev-docs` branch.

## Layout

```
SKILL.md          the instructions Claude loads
scripts/          scaffold, run_test, run_suite, report, summarize_trace, spec, bench, ab, junit, selftest
                  (with selftest_capabilities), unit_tests; observe / policy / rules / replay / session / jev_client
                  are the runner's parts
references/       spec-format, trace-format, verdict-rubric, suites, troubleshooting, runner-design
specs/            two smoke specs; examples/ (public sites), compare/ (the Jev vs Playwright-CLI comparison)
```

## Development

```bash
python scripts/unit_tests.py     # standard library only, a few seconds
python scripts/selftest.py       # offline: local pages and a fake Jev, about a minute
```

CI runs both on every push and pull request. The design notes, session handoffs, measurement files and the skill's
evals live on the [`dev-docs`](https://github.com/Faresabdelghany/jev-browser-test/tree/dev-docs) branch, so that an
install carries only the skill; check it out beside the code with
`git fetch origin dev-docs && git worktree add dev origin/dev-docs -B dev-docs` (`dev/` is git-ignored here).
`.github/workflows/live.yml` runs a plan against the real Jev API on GitHub's runners when a `live/<name>` branch is
pushed (it needs the repository secret `TYPESAFE_API_KEY`) and publishes the results to the `live-results` branch;
`scripts/ab.py` compares a set of specs with and without a runner option, or (`--a-runner`) on two versions of the
runner.
To release, bump `version` in `.claude-plugin/plugin.json` and `marketplace.json` and add its section to
[`CHANGELOG.md`](CHANGELOG.md): merging to `main` tags `v<version>` and publishes the release.

## License

[MIT](LICENSE).

Related: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) uses the same observe → choose →
act loop; this runner drops the text model from the loop and adds the spec and result contract so Claude can judge
runs it never sat inside.
