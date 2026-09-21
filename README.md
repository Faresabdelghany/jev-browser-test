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

The runner reads the key from the environment. Never put keys or passwords in a spec: use `${ENV_VAR}`
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
`done_unverified`, `budget_exhausted`), 2 = spec/environment problem. `SKILL.md` tells Claude how to
write specs and how to turn a trace into a verdict (PASS / BUG / TEST_ISSUE / FLAKY / NEEDS_HUMAN);
`references/` has the spec format, trace format, rubric and runner design.

## What it does with Jev's confidence

The runner never acts on a guess. A decision below `thresholds.min_confidence` on the operation, the
target or which value to type is not executed: the step becomes a wait, Jev is asked again, and three
undecided answers on an unchanged page end the run as `low_confidence`. A confident DONE with unsatisfied
checks gets one settle-and-recheck before the verdict. Both rules came from real runs: Jev split 0.68/0.32
over which value to type into a password field, and once declared DONE at 0.36 mid-reload.

## Measured (real app, Chromium, Sept 2026)

- Jev decision: median ~0.9 s (0.7–1.8 s), one request per step carrying all questions, ~1.8k tokens
- Playwright observe + act: median ~1.3–2.4 s — the browser is the bottleneck, not the model
- A 5-step login → impersonate flow: 20–35 s, 5–7 requests, a fraction of a cent
- Oracle discrimination: a true check read 0.86–0.92, the same check reworded to a false statement 0.01

## Layout

```
SKILL.md                    instructions Claude Code loads
scripts/run_test.py         the loop
scripts/observe.py          page → numbered element table (semantic, label-proxy and cursor:pointer passes)
scripts/policy.py           state + questions for Jev, answer parsing
scripts/jev_client.py       stdlib HTTP client for POST /v1/systemone
scripts/spec.py             defaults, ${ENV} substitution, validation
scripts/summarize_trace.py  one line per step, --step N for a full dump
scripts/selftest.py         offline: fake Jev, local pages, 8 scenarios
references/                 spec-format, trace-format, verdict-rubric, runner-design
specs/                      example specs
```

Related: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) uses the same
observe → choose → act shape; this runner drops the text model from the loop and adds the spec/trace
contract so Claude can judge runs it never sat inside.
