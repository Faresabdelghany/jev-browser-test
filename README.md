# jev-browser-test

Goal-driven end-to-end browser testing for [Claude Code](https://docs.claude.com/en/docs/claude-code):
Claude writes the test spec and judges the result, [TypeSafe's Jev](https://docs.typesafe.ai/introduction)
picks every click/type/scroll from a numbered element table, and Playwright executes.

```
Claude (slow brain)  →  spec.json  →  runner loop  →  result.json (+ trace, screenshots)  →  Claude (acts on it)
                                          ↕
                            Jev: one typed decision per step
                            Playwright: observe + act
```

The loop: **ticket or flow → Claude writes the spec, including the outcomes it will accept back → Jev
runs it → the runner returns exactly one of those outcomes with its evidence → if BUG, Claude fixes the
code → the same spec re-runs green → PR.** The spec that found a bug stays as its regression test.

Jev never generates text. Each step the runner sends it the page state and a fixed set of typed
questions — which operation, which element, which prepared value, and every check in the spec as a
true/false probability — and gets structured answers with confidence. Claude pre-supplies every string
in `spec.data`; Jev only chooses *which* one to type, so there is no text model in the loop at all.

## Install

Copy the folder to `~/.claude/skills/jev-browser-test` (Claude Code picks it up as a skill), then:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python scripts/selftest.py          # offline: no key, no network, must end SELFTEST OK
export TYPESAFE_API_KEY=...                   # from https://console.typesafe.ai/keys
```

The runner reads the key from the environment, or from a `.env` file in the directory you start it
from (already-exported variables win; `.env` is git-ignored). Never put real keys or passwords in a spec (the demo
site's public credential below is the one exception): use `${ENV_VAR}` in `data` and list the key under
`secrets`; better, do the login itself in `setup` so the credential never reaches Jev at all.

## Use

```bash
.venv/bin/python scripts/spec.py specs/smoke-login.json                 # validate, no browser
.venv/bin/python scripts/run_test.py specs/smoke-login.json --headed    # run one spec -> runs/<id>/<ts>/result.json
.venv/bin/python scripts/summarize_trace.py runs/smoke-login/<ts> --result        # one run directory: result.json first
.venv/bin/python scripts/run_suite.py specs/*.json --repeat 3           # many specs x repeats -> results.json + results.md, flaky computed
.venv/bin/python scripts/report.py runs/smoke-login/<ts>                # one run -> a self-contained report.html
.venv/bin/python scripts/report.py runs/suite/<ts>                     # a whole suite -> one report.html per run
```

A spec is a goal in plain language, the endings the run may return (each a statement about the visible
page with a pre-declared verdict), and exact expectations checked in code at the end:

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

The run writes `result.json`: `outcome` (one of the declared names, or `undetermined` with a typed reason
and a suggested verdict), `verdict`, the page line that states it (selected by Jev, copied verbatim), the
assertions, and the story of the actions. Exit code 0 = an outcome with verdict `pass`, 1 = anything
else, 2 = spec/environment problem. `SKILL.md` tells Claude how to write specs and how to act on a result
(PASS / BUG / TEST_ISSUE / FLAKY / NEEDS_HUMAN); `references/` has the spec format, trace and result
format, rubric and runner design.

## What it does with Jev's confidence

The runner never acts on a guess. A decision below `thresholds.min_confidence` on the operation, the
target or which value to type is not executed: the step becomes a wait, Jev is asked again, and three
undecided answers on an unchanged page end the run as `low_confidence`. A pass outcome (or a confident
DONE) gets one settle-and-recheck and then the `assert` block before it counts; any other declared outcome
is terminal at first sighting. Both gates came from real runs: Jev split 0.68/0.32 over which value to
type into a password field, and once declared DONE at 0.36 mid-reload. The outcomes are asked as one
Choice, not as independent true/false checks, because a Choice compares the endings: the bad-password
message that read 0.73–0.84 as a lone check (and ended runs `low_confidence` after three hesitant steps) is
chosen as `bad_credentials` the first step it is on screen.

## Measured (the-internet.herokuapp.com login, Chromium, `jev-1.13.0`, Sept 2026)

Two rounds, each five repeats before and after with `scripts/bench.py`, medians. First the
jev-ultrafast-style loop work (`docs/superpowers/measurements/2026-09-21-track1-{baseline,after}.json`):

| `smoke-login` (3 actions, passed 5/5 both times) | before | after |
|---|---:|---:|
| wall-clock per run | 8.9 s | 5.2 s (−42%) |
| Jev request, warm connection | 770 ms | 307 ms |
| browser work per action (execute + settle) | 646 ms | 147 ms |
| decision confidence | 0.94 | 0.95 |
| input tokens per run | 3.9k | 5.1k |

The two per-step rows are medians pooled over every step of the five runs (`jev_warm_ms_all_steps` and
`browser_per_action_ms_all_steps` in the JSON; the first request of a run, which pays for the TCP + TLS
handshake, is reported separately as `jev_first_ms`, 832 → 766 ms). Of the remaining 5.2 s about 2.0 s is
the initial page load of the remote site and 0.15 s the browser launch (`trace.timing`, medians
`navigation_ms` 1,979 and `launch_ms` 152). One connection per run instead of one per request is where the Jev time went;
observing as soon as the DOM is quiet instead of a fixed pause is where the browser time went. The
structured state costs about a third more input tokens. Things that were tried and measured worse are in
`docs/superpowers/measurements/` too (the standing rules text, see `references/runner-design.md`).

Then the results contract (`2026-09-22-track2-{before,after}.json`), which is what the runner does today:

| | before | after |
|---|---:|---:|
| `smoke-login` | passed 5/5, 4.8 s, 4 requests, 5.1k tokens | `logged_in` (pass) 5/5 confirmed with 3/3 assertions, 6.0 s, 6 requests, 8.9k tokens |
| `smoke-login-badpw` (wrong password on purpose) | `never_violated` 2/5, `low_confidence` 3/5, 6.4 s, confidence 0.41 | `bad_credentials` (pass) 5/5, seen the first step the message is on screen, 6.1 s, confidence 0.93 |

The contract costs one confirmation step and one adjudication request per run, and the two extra Choices
per step are where the extra tokens go; what it buys is a run that comes back as one declared outcome
with the page's own line as evidence, and a negative test that is decided the moment its message appears
instead of hovering under a threshold.

Re-measured after the review fixes (`9c20838`, `2026-09-22-review-fixes-bench.json`, from a clean export of
that commit): the same results in 5/5 runs of both specs, 6.4 s and 6.3 s, the same 6 requests and the same
token counts, confidence 0.94 and 0.92; the suite of both specs × 5 repeats on 4 workers took 20.8 s, all
pass (`2026-09-22-review-fixes-suite.json`). `docs/superpowers/measurements/README.md` has the row-by-row
comparison.

## Layout

```
SKILL.md                    instructions Claude Code loads
scripts/run_test.py         the loop
scripts/observe.py          page → numbered element table + freshness fingerprint (semantic, label-proxy and cursor:pointer passes)
scripts/policy.py           state + questions for Jev, answer validation and parsing
scripts/rules.py            optional standing rules attached to every question ("rules": true)
scripts/jev_client.py       stdlib HTTP client for POST /v1/systemone, one connection per run
scripts/spec.py             defaults, ${ENV} substitution, validation
scripts/summarize_trace.py  one line per step, --step N for a full dump, --result for result.json
scripts/run_suite.py        specs x repeats on a worker pool -> results.json / results.md with agreement and a flaky verdict
scripts/report.py           one run -> a single static report.html (steps, probabilities, checks, screenshots inline)
scripts/bench.py            run a spec N times; medians of wall, Jev, browser, tokens, confidence
scripts/selftest.py         offline: fake Jev, local pages, one case per terminal status and guard
scripts/unit_tests.py       stdlib unittest for the pure parts (client, validation, criteria, bench)
references/                 spec-format, trace-format, verdict-rubric, runner-design
specs/                      example specs
docs/superpowers/           design spec, plans, and the measurement files every number above comes from
```

Related: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) uses the same
observe → choose → act shape; this runner drops the text model from the loop and adds the spec/trace
contract so Claude can judge runs it never sat inside.
