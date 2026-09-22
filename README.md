# jev-browser-test

Goal-driven end-to-end browser testing for [Claude Code](https://docs.claude.com/en/docs/claude-code):
Claude writes the test spec and judges the result, [TypeSafe's Jev](https://docs.typesafe.ai/introduction)
picks every click/type/scroll from a numbered element table, and Playwright executes.

```
Claude (slow brain)  →  spec.json  →  runner loop  →  trace.json + screenshots  →  Claude (verdict)
                                          ↕
                            Jev: one typed decision per step
                            Playwright: observe + act
```

The loop: **ticket or flow → Claude writes the spec → Jev runs it → Claude judges → if BUG, Claude fixes
the code → the same spec re-runs green → PR.** The spec that found a bug stays as its regression test.

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
from (already-exported variables win; `.env` is git-ignored). Never put keys or passwords in a spec: use `${ENV_VAR}`
in `data` and list the key under `secrets`; better, do the login itself in `setup` so the credential
never reaches Jev at all.

## Use

```bash
.venv/bin/python scripts/spec.py specs/smoke-login.json                 # validate, no browser
.venv/bin/python scripts/run_test.py specs/smoke-login.json --headed    # run
.venv/bin/python scripts/summarize_trace.py runs/smoke-login/*/trace.json
```

A spec is a goal in plain language plus checks that are statements about what is visible:

```json
{
  "id": "smoke-login",
  "start_url": "https://the-internet.herokuapp.com/login",
  "goal": "Log in with the provided username and password, so that the Secure Area page is shown.",
  "data": { "username": "tomsmith", "password": "SuperSecretPassword!" },
  "checks": {
    "logged_in": "A green flash message says 'You logged into a secure area!'",
    "login_error": "A red flash message says the username or password is invalid"
  },
  "done_when": ["logged_in"],
  "never": ["login_error"]
}
```

Exit code 0 = passed, 1 = failed (`never_violated`, `stuck`, `blocked`, `low_confidence`,
`done_unverified`, `budget_exhausted`, `unstable_page`, `error`), 2 = spec/environment problem. `SKILL.md` tells Claude how to
write specs and how to turn a trace into a verdict (PASS / BUG / TEST_ISSUE / FLAKY / NEEDS_HUMAN);
`references/` has the spec format, trace format, rubric and runner design.

## What it does with Jev's confidence

The runner never acts on a guess. A decision below `thresholds.min_confidence` on the operation, the
target or which value to type is not executed: the step becomes a wait, Jev is asked again, and three
undecided answers on an unchanged page end the run as `low_confidence`. A confident DONE with unsatisfied
checks gets one settle-and-recheck before the verdict. Both rules came from real runs: Jev split 0.68/0.32
over which value to type into a password field, and once declared DONE at 0.36 mid-reload.

## Measured (the-internet.herokuapp.com login, Chromium, `jev-1.13.0`, Sept 2026)

Five repeats before and after the jev-ultrafast-style loop work, `scripts/bench.py`, medians
(`docs/superpowers/measurements/2026-09-21-track1-{baseline,after}.json`):

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

## Layout

```
SKILL.md                    instructions Claude Code loads
scripts/run_test.py         the loop
scripts/observe.py          page → numbered element table + freshness fingerprint (semantic, label-proxy and cursor:pointer passes)
scripts/policy.py           state + questions for Jev, answer validation and parsing
scripts/rules.py            optional standing rules attached to every question ("rules": true)
scripts/jev_client.py       stdlib HTTP client for POST /v1/systemone, one connection per run
scripts/spec.py             defaults, ${ENV} substitution, validation
scripts/summarize_trace.py  one line per step, --step N for a full dump
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
