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

## Review of iteration 2 (2026-09-24) and the decision on iteration 3

Fares delegated the review. The three with-skill outputs were read in full (reports, the agents' `user_notes.md`, the
corrected spec) against the grades and against the skill at `b14d587`; the reviews are in `iteration-2/feedback.json`
(`status: complete`). Outputs: nothing to change; the verdicts, evidence blocks, controls and rerunnable specs are what
each prompt asked for. Of the agents' friction notes, every runner and doc gap they named was already fixed in
`b14d587` except these, fixed in the same commit as this section (docs plus one script line, 88 unit tests, selftest OK):

- Triage: after `control_had_no_effect`, read every `NO-EFFECT` flag; the reason names the last dead control and the
  first one is often earlier (eval 1: an empty order behind a Finish that did nothing). SKILL.md triage-only mode
  step 1, rubric triage step 1 and its flags list.
- Triage: compare the spec as run (`trace.spec`) with the spec on disk or the skill's example (eval 1: the overnight
  spec lacked the `expect` block the example carries). Same places.
- A rerun for pictures (`--screenshots all`) is the one rerun; combine it with the spec fix. SKILL.md and rubric.
- The report template has an `**Evidence:**` line for `undetermined` runs (no line to quote) and the `**Fix:**` line
  is marked "BUG with the repository available".
- Check values can drift after a no-effect action (Jev sees the action in its history); the element table, the page
  signature and the flag are the hard facts. SKILL.md step 3.
- `steps/final.png` named as such in the rubric, spec-format and trace-format.
- `summarize_trace.py --step N` prints a sentence instead of an empty heading when the step carries no element table.

**No iteration 3.** The three prompts are at ceiling (28/28 with the skill, both arms graded identically), the
old skill's three misses were exactly the targeted behaviours, and the residual notes were clarifications no
assertion would discriminate on; a rerun would cost ~400k tokens for the same numbers. A further iteration would need
new, harder prompts (a multi-page flow with a modal, a private app behind `storage_state`, a spec the agent must
write from a vague one-line request), which is a scope decision for Fares, not a follow-up of this review.

Left as they were, on purpose: the observer's wrapper-span duplicate (Jev picked the select at 1.00), persistent suite
workers (~0.5 s per run), `allowed-tools` limited to the skill's own scripts (a probe or `cp` prompts once; widening
the pattern would be the surprise), `stuck_reason` answering `other` after a no-effect select (the declared
`requires_action` outcome is the dependable signal, and the troubleshooting row says so).

## Suggested next steps (none required)

- Re-import the skill into Claude Desktop (`git archive HEAD` zipped as `jev-browser-test.skill`; the workspace holds
  `jev-browser-test-b14d587.skill`, one commit behind this file).
- Use the skill on a real application from the smoke specs; harder eval prompts only if that use turns up misses.
