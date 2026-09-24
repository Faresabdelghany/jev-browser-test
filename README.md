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

This repository *is* the skill: `SKILL.md` at its root, `scripts/`, `references/`, `specs/`. Install it the way
you install any Claude Code skill:

```bash
# personal skill, every project on this machine
git clone https://github.com/Faresabdelghany/jev-browser-test ~/.claude/skills/jev-browser-test

# project skill, committed with the repository you are testing
git clone https://github.com/Faresabdelghany/jev-browser-test .claude/skills/jev-browser-test

# plugin, from inside Claude Code (single-skill plugin: .claude-plugin/ at the root)
/plugin marketplace add Faresabdelghany/jev-browser-test
/plugin install jev-browser-test@jev-browser-test
```

Claude.ai and Claude Desktop take the same folder zipped as a `.skill` file (`python -m scripts.package_skill`
from the skill-creator, or zip the folder without `.venv/` and `runs/`). Then, once per machine, give the skill
its own Python with Playwright:

```bash
cd ~/.claude/skills/jev-browser-test        # wherever it landed
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/selftest.py          # offline: no key, no network, ~45 s, must end SELFTEST OK
export TYPESAFE_API_KEY=...                   # from https://console.typesafe.ai/keys
```

`SKILL.md` tells Claude to use that interpreter (`${CLAUDE_SKILL_DIR}/.venv/bin/python`) and pre-approves it for
the skill's scripts. The runner reads the key from the environment, or from a `.env` file in the directory it is
started from (already-exported variables win; `.env` is git-ignored). Never put real keys or passwords in a spec
(the demo site's public credential below is the one exception): use `${ENV_VAR}` in `data` and list the key under
`secrets`; better, do the login itself in `setup` so the credential never reaches Jev at all.

Runs are headless unless asked otherwise. `--headed` / `--headless` on `run_test.py` and `run_suite.py` decide for
one command; `JEV_HEADED=1` in the same `.env` opens a window on every run until removed; the spec's
`browser.headless` comes last. In Claude Code, `/jev-browser-test headed ...` or `/jev-browser-test headless ...`
picks the mode for the conversation, and "show me the browser" in a request does the same. The runner prints
`browser: headed` or `browser: headless (...)` as it starts and records the mode in `trace.browser.headless`.

## Use

```bash
.venv/bin/python scripts/spec.py specs/smoke-login.json                 # validate, no browser
.venv/bin/python scripts/run_test.py specs/smoke-login.json --headed    # run one spec, watching -> runs/<id>/<ts>/result.json (--headless: in the background)
.venv/bin/python scripts/summarize_trace.py runs/smoke-login/<ts> --result        # one run directory: result.json first
.venv/bin/python scripts/run_suite.py specs/*.json --repeat 3           # many specs x repeats -> results.json + results.md, flaky computed
.venv/bin/python scripts/report.py runs/smoke-login/<ts>                # one run -> a self-contained report.html
.venv/bin/python scripts/report.py runs/suite/<ts>                     # a whole suite -> one report.html per run
```

Specs and runs live in the project you are testing (`specs/`, `runs/`); the scripts stay in the skill, so from a
project the commands read `~/.claude/skills/jev-browser-test/.venv/bin/python ~/.claude/skills/jev-browser-test/scripts/run_test.py specs/<id>.json`.
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
assertions, how the pass was confirmed (`confirmed_by`: the assertions holding on the sighting page, or a
settle-and-recheck), and the story of the actions. Exit code 0 = an outcome with verdict `pass` (or, for a spec
with `expect`, the declared result), 1 = anything else, 2 = never a verdict: a spec or environment problem, a
start URL that did not load, a setup step that failed. `SKILL.md` tells Claude how to write specs and how to act on a result
(PASS / BUG / TEST_ISSUE / FLAKY / NEEDS_HUMAN); `references/` has the spec format, trace and result
format, rubric and runner design.

## Examples

`specs/examples/` holds eighteen specs against public sites: the nine the real-application trial ran
(`docs/superpowers/plans/2026-09-22-handoff-after-real-app.md`), one more, and eight added on 2026-09-24 to reach
flows the first ten did not (`docs/superpowers/plans/2026-09-24-handoff-after-more-examples.md`; they found four
runner defects, fixed in `4bd7429` and the commit after `14ecee9`). Their latest suite run, at `14ecee9` with 3
repeats each on 2 workers, is `docs/superpowers/measurements/2026-09-24-examples-suite-eighteen.md` (359 Jev
requests over 54 runs, 228 s on 2 workers; the ten older specs read as at `0a8727c`).

| spec | site | flow | it exercises | at `14ecee9`, 3 repeats |
|---|---|---|---|---|
| `shop-checkout` | saucedemo.com, `standard_user` | login in `setup`, add a named product from six cards with identical "Add to cart" buttons, cart, a three-field form, overview, finish | identical labels told apart by their card, a multi-page path, three `data` values | pass 3/3, 10 requests, "Checkout: Complete!" |
| `shop-add-second-item` | saucedemo.com | add the second card's product, open the cart | a wrong pick shows up as an outcome; the product name is the evidence line | pass 3/3, 4 requests |
| `shop-checkout-problem-account` | saucedemo.com, `problem_user` | the checkout with the account the site documents as broken: a form field drops its input | a declared `bug` outcome with the app's own error as its evidence line | bug 3/3, "Error: Last Name is required" |
| `shop-checkout-error-account` | saucedemo.com, `error_user` | the checkout with the account whose Finish button does nothing | `stuck_reason: control_had_no_effect` after a no-op click (flag `NO-EFFECT`), then BLOCKED with a suggested verdict; an **`expect`** spec: the documented breakage is its declared result | **expected** 3/3 (undetermined/blocked/control_had_no_effect, as declared), 10 requests |
| `wiki-search` | en.wikipedia.org | type a term into the search box, the suggestions open, reach the article | a real autocomplete (`settle` ends on `options`), a very long page | pass 3/3, 4 requests, 34,470 input tokens a run |
| `todo-add-filter` | demo.playwright.dev/todomvc | add two todos, complete one, open the Active filter | TYPE_TEXT then PRESS_ENTER, two values into one field, hidden checkboxes under styled boxes, hash routing, a two-sentence outcome statement | pass 3/3, 8 requests, "1 item left" |
| `load-wait` | the-internet.herokuapp.com/dynamic_loading/1 | press Start, a loader runs for 5 s, a text appears | Jev choosing WAIT on a page with a timer; each WAIT ends the moment the page changes | pass 3/3, 7 requests, "Hello World!" |
| `notify-random` | the-internet.herokuapp.com/notification_message_rendered | click once; the notification is a random success or a random failure | the computed `flaky` verdict, each run keeping its own declared verdict; `text_in` on the notification element (`#flash`), because the page's own copy contains both messages and a page-wide `text_contains` could never fail | flaky (pass 2, bug 1), 3 requests |
| `modal-close` | the-internet.herokuapp.com/entry_ad | close the modal that opens on load | an overlay that hides the page; an absence as the pass statement | pass 3/3, 4 requests |
| `menu-random` | the-internet.herokuapp.com/disappearing_elements | nothing to click: is every menu entry listed? | an outcome decided on the start page (one step, two requests); an entry the page drops at random | bug 3/3 this time (flaky, bug 2 / pass 1, at `0a8727c`): the page's own coin |
| `web-form-submit` | selenium.dev/selenium/web/web-form.html | a text input, a textarea, a native select, a checkbox, a radio, Submit | SELECT, a checkbox and a radio under `<label>`s, two typed values into different fields, the GET query asserted with `url_matches` | pass 3/3, 8 requests, "Form submitted" |
| `add-remove-elements` | the-internet.herokuapp.com/add_remove_elements/ | Add Element twice, then one of the two Delete buttons | the same button twice on a page that changes each time (not a repeat), two identical buttons, a count asserted exactly with `text_in` `equals` | pass 3/3, 5 requests, "Delete" |
| `dynamic-controls` | the-internet.herokuapp.com/dynamic_controls | Remove (a loader), then Enable (a loader) | WAIT after two asynchronous actions; undecided steps while a loader is visible, which the runner now waits out with backoff; `element_absent`; a pass outcome without `requires` (a check hovered at 0.79 while the Choice read 0.81) | pass 3/3, 10 requests, "It's gone!" |
| `forgot-password` | the-internet.herokuapp.com/forgot_password | type an e-mail, Retrieve password | the demo answers "Internal Server Error": a bug outcome whose evidence line is the server's own text, kept as an `expect` spec | expected 3/3 (server_error), 4 requests |
| `login-logout` | the-internet.herokuapp.com/login | Jev types the published username and password, logs in, logs out | a credential typed by Jev and masked through `secrets`, a two-page flow, `text_in` on `#flash` | pass 3/3, 6 requests, "You logged out of the secure area!" |
| `table-sort-due` | the-internet.herokuapp.com/tables | click the Due header of Example 1 | headers with no affordance at all (no role, tabindex, onclick or pointer cursor): not in Jev's table, so the run ends undetermined by `low_confidence`, `stuck` or `blocked`; an `expect` on the outcome only; `text_in` on the cells because `text_order` would be fooled by the second table | expected 3/3 (undetermined; `low_confidence` 3/3 with the footer link named in `notes`), 4 requests |
| `hrm-add-employee` | opensource-demo.orangehrmlive.com, Admin / admin123 | login in `setup`, PIM, Add Employee, two names, Save | a slow admin single-page app: forms under loading overlays (`covered_controls`), a sidebar with its own Search box, NO-EFFECT while Save is in flight, `field_value` on the saved record, `settle_ms` 2500; on 2 workers two forms opened in the same second share the pre-filled Employee Id and the second Save is rejected (`employee_id_taken`, a race in the app): run it on one worker | pass 1/3 at `14ecee9` (two workers: the id collision and a confirmation look that landed on a loading overlay); **pass 3/3 at `9139e22` on one worker**, 10 requests, "Jevtest Runner" |
| `toolshop-search-cart` | practicesoftwaretesting.com | search, open a product from the results, add to cart, open the cart | a search box with its own button, card links, a toast and a header badge, `field_value` on the cart's quantity field | pass 3/3, 10 requests, "Proceed to checkout" |

The shop and HRM specs' credentials are the demo accounts the sites print on their own login pages. Run them all
with `scripts/run_suite.py specs/examples/*.json --repeat 3 --workers 2` (the-internet is a free Heroku app: a cold
start can add 25 s to a run's navigation, which the runner reports as such), one with `scripts/run_test.py
specs/examples/<id>.json --headed`, and `hrm-add-employee` on its own with `--workers 1`. Copy one as the starting point for your own application, and keep specs for
a private application under `specs/local/` (git-ignored).

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

The current runner (`7b93b47`, five repeats each from a clean export, medians; `docs/superpowers/measurements/`
"Speed levers"):

| spec | wall-clock | of which site load + launch | Jev requests | first / warm request | browser work | input tokens |
|---|---:|---:|---:|---:|---:|---:|
| `smoke-login` (3 actions, pass 5/5) | **5.0 s** (was 6.4) | 2.2 s | 5 (was 6) | 288 / 294 ms | 0.76 s (was 1.30) | 6.4k (was 7.8k) |
| `smoke-login-badpw` (wrong password, `bad_credentials` 5/5) | **5.0 s** (was 6.5) | 2.2 s | 5 (was 6) | 292 / 301 ms | 0.76 s (was 1.27) | 6.9k (was 8.6k) |
| `load-wait` (a 5 s loader, pass 5/5) | **8.9 s** (was 11.3) | 2.2 s | 7 (was 8) | 306 / 292 ms | 3.97 s (was 5.56) | 6.9k (was 8.1k) |

Taking the site's own load and the browser launch out, the runner's time on the login fell from 4.1 to 2.6 s
(−35%): the TypeSafe connection is opened while the browser launches (the first request used to cost ~760 ms),
a pass whose assertions already hold is confirmed in code instead of paused, re-observed and re-asked, the
evidence questions ride in the confirmation request when one is needed, and a WAIT ends the moment the page
changes. A probe showed the ~300 ms per request is the API's floor from here (HTTP/2 and the number of questions
per request change nothing), so the levers left are round trips and waiting, not the wire. The history of how the
runner got here follows.

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

The contract costs one confirmation step and one adjudication request per run, and the extra `outcome`
Choice per step is where the extra tokens go (the `blocked_reason` Choice rode on every step until block F
below; it is now asked only where its answer is read); what it buys is a run that comes back as one declared outcome
with the page's own line as evidence, and a negative test that is decided the moment its message appears
instead of hovering under a threshold.

Re-measured after the review fixes (`9c20838`, `2026-09-22-review-fixes-bench.json`, from a clean export of
that commit): the same results in 5/5 runs of both specs, 6.4 s and 6.3 s, the same 6 requests and the same
token counts, confidence 0.94 and 0.92; the suite of both specs × 5 repeats on 4 workers took 20.8 s, all
pass (`2026-09-22-review-fixes-suite.json`). `docs/superpowers/measurements/README.md` has the row-by-row
comparison.

Block F (2026-09-22, `b3996fa` → `1890405`, five levers each measured from a clean export of its commit,
`docs/superpowers/measurements/README.md` "Block F"): `blocked_reason` asked only where its answer is read,
shorter reason texts, the adjudication's page lines sent once, a WAIT backoff on unchanged pages and a
2,000-char text cap. `smoke-login` 8,932 → 7,753 input tokens per run (−13%), the wrong-password spec
9,774 → 8,580 (−12%), a 5 s loader 12,901 → 8,059 with 10 → 8 requests (+1.0 s wall-clock: the last
backed-off pause overshoots the loader), a long encyclopedia article 47,872 → 43,990 (−8%); the same
outcomes, evidence lines and sighting steps in every run.

## Layout

```
SKILL.md                    instructions Claude Code loads (the skill: this folder)
.claude-plugin/             plugin.json + marketplace.json: the same folder installable as a single-skill plugin
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
specs/                      the two smoke specs; specs/examples/ ten public-site specs (see Examples)
docs/superpowers/           design spec, plans, and the measurement files every number above comes from
```

Related: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) uses the same
observe → choose → act shape; this runner drops the text model from the loop and adds the spec/trace
contract so Claude can judge runs it never sat inside.
