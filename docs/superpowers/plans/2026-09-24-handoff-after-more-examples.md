# Handoff after the eight new examples and the runner fixes they forced (2026-09-24, night)

Fares asked to "test something else and make more tests to make sure that everything is working well". This session
wrote eight specs against public sites the first ten examples did not cover, ran them, fixed what they broke, and
measured. Earlier the same night it closed the skill-eval review (`534da71`) and pointed Claude Code's installed skill
at the repo (`~/.claude/skills/jev-browser-test` is a symlink to `~/Downloads/jev-browser-test`). Start with `git pull`.

## State of the repo

- 90 unit tests (`.venv/bin/python scripts/unit_tests.py`), selftest OK (36 run scenarios plus the observer, covered
  form, settle, CDP and dotenv checks, ~60 s). Both green at HEAD. The worktree used tonight is
  `~/.warp/worktrees/jev-browser-test/badlands-saguaro` (same commits as `main`; its `.env`, `specs/local/` and `runs/`
  are ignored copies).
- `specs/examples/` holds eighteen specs (README "Examples" table). `specs/local/` in the worktree holds the same eight
  new ones, kept for private-app specs; nothing private was written.
- Commits: `534da71` (review of eval iteration 2), `4bd7429` (three runner fixes + tests), `14ecee9` (the eight specs),
  then this file's commit (the repeated confirmation look, the table spec's `expect`, the HRM collision outcome,
  README, measurements) and the follow-up measurement commit after it.

## What the eight specs found, in one line each

| spec | site | ended | what it taught |
|---|---|---|---|
| `web-form-submit` | selenium.dev web form | pass 3/3 | SELECT, checkbox, radio, two typed values, the GET query asserted: nothing to fix |
| `add-remove-elements` | the-internet | pass 3/3 | identical buttons and a count: `text_in` `equals` on the container is the exact check |
| `dynamic-controls` | the-internet | pass 3/3 after two fixes | undecided steps used to burn the streak in ~2 s under a 5 s loader (runner fix 1); a `requires` on a check hovering at 0.79 held back a pass the Choice read at 0.81 (spec: no `requires`) |
| `forgot-password` | the-internet | expected 3/3 | the demo answers "Internal Server Error": a real defect kept as an `expect` spec |
| `login-logout` | the-internet | pass 3/3 | a Jev-typed, masked credential and a two-page flow: nothing to fix |
| `table-sort-due` | the-internet | expected 3/3 (follow-up) | headers with no affordance at all: not in Jev's table; the ending flips between `low_confidence` and `stuck` on borderline confidence, so `expect` names the outcome only |
| `hrm-add-employee` | OrangeHRM demo | pass 2/3 at the fix commit, the third a declared race | forms under loading overlays (runner fix 2: `covered_controls`), a Save that navigates late (fixes 3 and 4), a pre-filled Employee Id two workers share (`employee_id_taken`; run on one worker) |
| `toolshop-search-cart` | practicesoftwaretesting.com | pass 3/3 | search box + button, card links, toast, badge, `field_value` on the cart: nothing to fix |

## The four runner fixes

1. **Undecided steps** (`low_confidence` on the operation, target or value) wait like a chosen WAIT, `settle_ms` × 1,
   2, 4, ending the moment the page changes, and the streak restarts when the page signature changes
   (`step.low_streak`, `executed.wait`). Selftest 4f (never-reached pass: streaks 1,2 then 1,2,3) and 4g (the pass
   comes into view during the waits). `4bd7429`.
2. **`covered_controls`**: the observer counts controls on screen under another layer and Jev sees the count in its
   state (`covered_controls`; trace `covered_controls`, flag `COVERED:n`). Live: TYPE_TEXT into the sidebar Search fell
   from 0.91 to 0.38 and was refused. Selftest `covered_check` (a form under a 700 ms overlay). `4bd7429`.
3. **Observation vs navigation**: `run_test.observe_after_navigation` retries an observation that raised "Execution
   context was destroyed", twice at most, `trace.observation_retries`. Unit-tested with a fake page. `4bd7429`.
4. **The confirmation looks again while the page moves**: a pass sighting or DONE gets its settle-and-recheck; if that
   look finds the page changed since the sighting and no pass visible, it parks again (`settle_ms` × 2, × 4, ending on
   change) up to `CONFIRM_RECHECKS_MAX` = 2 (`step.recheck_again`). Selftest 4h (a two-stage loader, `?stage=`). This
   file's commit.

Docs updated for all four: SKILL.md (flags, two troubleshooting rows, the Files list), spec-format
(`max_low_confidence_steps`), trace-format (`covered_controls`, `low_streak`, `recheck_again`, `observation_retries`,
`done_unverified` meaning), runner-design (park, state, the two new paragraphs).

## Numbers with their files

`docs/superpowers/measurements/2026-09-24-bench-smoke-login.json` (5 × smoke login at `14ecee9`: same 5 requests and
browser work as `7b93b47`, +1 s of API latency and page load tonight), `2026-09-24-examples-suite-eighteen.{json,md}`
(18 × 3 at `14ecee9`: 359 requests, 54 runs; 12 pass, 2 expected, 2 bug, 2 flaky with the causes above),
`2026-09-24-follow-up-hrm-table.{json,md}` (the two flaky specs at the fix commit). The measurements README has the
section "More examples (2026-09-24)".

## Findings left as they are

- The-internet.herokuapp.com cold-starts (23–26 s of navigation) show up as wall-clock, never as verdicts; the README
  says so and keeps 2 workers.
- `menu-random` read bug 3/3 tonight (flaky bug 2 / pass 1 before): the page's own coin.
- The HRM demo's Employee Id race is the app's; the spec declares it and asks for one worker rather than working
  around it (a typed unique id would collide on the next repeat).
- The table headers' missing affordance is the page's; the observer does not guess at jQuery-bound handlers.
- `allowed-tools` stays limited to the skill's own scripts; the peek script used tonight lived in the scratchpad.
- Not built: the observer's wrapper-span rule, persistent suite workers, a DONE-on-covered-page heuristic.

## Suggested next steps

- Re-import the skill into Claude Desktop from a fresh `git archive HEAD` zip (the workspace holds one per commit).
- Use the skill on WasteHero from the smoke specs (`specs/local/`, a staging URL and a test account are the inputs).
- If the eval loop is reopened, new harder prompts (an admin CRUD behind `storage_state`, a spec written from a
  one-line request) rather than the three at ceiling.
