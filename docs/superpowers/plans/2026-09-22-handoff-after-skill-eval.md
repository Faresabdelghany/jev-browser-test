# Handoff after the skill eval and the speed work (2026-09-22, evening)

Fares ran `/skill-creator eval the skill`, then said: fix all of it, the point of Jev is speed and results, take
browser-use/jev-ultrafast as the example, read the Jev docs, ship it as a standard Claude Code skill. This session did
that in five commits (`a09f89f`, `7b93b47`, `0a8727c`, `723d170`, and the docs commit after this file). Start with `git pull`.

## State of the repo

- 87 unit tests (`.venv/bin/python scripts/unit_tests.py`), selftest OK (33 run scenarios plus the observer, settle, CDP
  and dotenv checks, ~50 s). Both green at HEAD.
- The skill installs like any Claude Code skill: clone into `~/.claude/skills/jev-browser-test` or `.claude/skills/`, or as
  a single-skill plugin (`.claude-plugin/plugin.json` + `marketplace.json`, `/plugin marketplace add
  Faresabdelghany/jev-browser-test`). `SKILL.md` uses `${CLAUDE_SKILL_DIR}` and the skill's own `.venv`, pre-approved through
  `allowed-tools`; specs and runs live in the project under test. The skill-creator's validator says "Skill is valid".
- The venv has two extras not in `requirements.txt`: `pyyaml` (for the skill-creator's validator) and `httpx[http2]` (for
  the latency probe). Both harmless; `pip uninstall` them if the venv should mirror requirements exactly.
- Claude Desktop's copy of the skill is behind the repo by everything in this handoff; the export / re-import is Fares's.

## What changed, and why

**Eval iteration 1** (`~/Downloads/jev-browser-test-workspace/iteration-1/`, `findings.md`): three realistic prompts, with
and without the skill; pass rate 96% vs 83% where the whole gap was two verdict-label assertions; the skill arm cost
+50% tokens and made 18 / 2 / 37 browser runs; ten runner and doc gaps, two verified in code (the `notify-random` example's
vacuous `text_contains`, and a start-URL `goto` timeout counted as an outcome that flipped a unanimous spec to flaky).

**Speed** (`docs/superpowers/measurements/README.md`, "Speed levers"): the login flow 6.4 → 5.0 s wall, the runner's own
time 4.1 → 2.6 s (−35%), the loader 11.3 → 8.9 s, 6 → 5 requests, −17% tokens, identical outcomes 5/5. Levers: the
TypeSafe connection opened in a background thread while the browser launches (`JevClient.warm_up`), the evidence
questions riding in the confirmation request, a WAIT that ends when the page's fingerprint changes (`wait_for_change`),
and a pass confirmed at once in code when its assertions already hold (`confirm: "assert"`, default; `"recheck"` keeps the
old path). A probe of 40 identical requests showed HTTP/2 and the number of questions change nothing (~300 ms is the API's
floor from here), so the stdlib client stays. `references/runner-design.md` "Where the wall-clock goes" has the story.

**Runner fixes**: `requires_action` on outcomes (a "nothing changed" statement is true of the start page), the
`NO-EFFECT` flag and a key-mode picture after a no-effect action, `text_in` and `text_order` assertions, `expect` for
expected-red specs (suite verdict `expected`, exit 0 when matched), `browser.navigation_timeout_ms` (30 s) and
`result.reason.phase` for failures before the first observation (exit 2, kept out of the suite's distribution), suite
agreement on verdicts, `spec.py --help`, `final.png` as a copy of the terminal picture, the failed setup step kept.

**Docs**: SKILL.md rewritten (run once, read, then decide; suites of 3–5 repeats on ≤ 2 workers; triage-only rules: read
first, flake signals before any rerun, one rerun and one control at most, no source archaeology; every spec gets
assertions; a speed section; new troubleshooting rows). The four references updated for every new field and flag.

**Eval iteration 2** (`iteration-2/`, `benchmark.json`, `review.html`, live viewer on port 3117, `viewer.pid`): the same
three prompts on the new skill, assertions reworked toward what the skill promises; the baseline is iteration 1's
with-skill outputs re-graded under the same assertions. 100% (28/28) vs 89% (25/28); tokens −13%, wall −18%, browser
runs 3 / 2 / 11 vs 18 / 2 / 37 (+60 probes). The three misses of the old skill were exactly the targeted behaviours.
The new features were used unprompted (`requires_action`, `text_in`, `expect`, confirm-by-assertions, the flake checklist).

## Findings left as they are

- The eval agents ran while an examples suite ran (a 3.6 s browser launch in one run): the per-run seconds in the
  iteration-2 reports and in `2026-09-22-examples-suite-after-speed.md` are not runner measurements; the benches are.
- `stuck_reason` after a `NO-EFFECT` select answered `other` (0.61) rather than `control_had_no_effect`; a declared
  `requires_action` bug outcome was the dependable signal. The troubleshooting row still cites the reason.
- Check probabilities soften after a no-effect action on an identical page (Jev weighs `recent_actions`); the outcome
  Choice stayed decisive. Documented as a reading note only.
- The observer offers a wrapper `span` carrying a `<select>`'s whole option text next to the select itself (saucedemo's
  `.select_container`). Jev still picked the select at 1.00. A wrapper whose text equals its child control's text could be
  dropped in `observe.py`; not done.
- When Jev chooses DONE before a pass outcome is in sight, the runner takes the checking step and confirms there
  (`confirmed_by: recheck`, one request more). Correct and now documented; a DONE + all-assertions-hold fast path was
  considered and not built (the result must still name a seen outcome).
- Iteration-2's eval-1 agent called `expect` "restore the block": the fixture trace predates `expect`; no action needed.
- Persistent suite workers (one browser and one connection per worker instead of a subprocess per run) would save
  ~0.5 s per run in suites; not built.

## Numbers with their files

`docs/superpowers/measurements/2026-09-22-speed-before-bench.json` (`2956a93`), `-speed-levers-1-bench.json` (`a09f89f`),
`-speed-levers-2-bench.json` (`7b93b47`), `2026-09-22-examples-suite-after-speed.{json,md}` (`0a8727c`), all from clean
exports with `GIT_COMMIT` set and cited in the measurements README. The eval workspaces are outside the repo
(`~/Downloads/jev-browser-test-workspace/`); `evals/evals.json` and the triage fixture are committed.

## Suggested next steps (none required)

- Review `iteration-2/review.html` (or the live viewer) and leave feedback; iteration 3 would target whatever it says.
- Decide on the observer's wrapper-span rule and on persistent suite workers.
- Re-import the skill into Claude Desktop (`git archive HEAD` zipped as `jev-browser-test.skill`; the workspace holds one).
