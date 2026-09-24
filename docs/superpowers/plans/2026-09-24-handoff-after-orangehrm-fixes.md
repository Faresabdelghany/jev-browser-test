# Handoff after the OrangeHRM runs' six items (2026-09-24, morning)

The comparison of 04:04–04:12 (`docs/superpowers/measurements/2026-09-24-claude-cost-comparison.md`) and the four
OrangeHRM specs written that night pointed at six things; Fares asked for all six, implemented and tested "till you get
the best results and 100% accuracy". This session did them in the recommended order (2, 4, 3, 1, 5, 6), each test-first
with unit tests and offline selftest scenarios, each its own commit, and ended with the three new specs run three
times each on one worker from a clean export. Start with `git pull` (main was fast-forwarded to this branch).

## State of the repo

- Unit tests: 119 (`.venv/bin/python scripts/unit_tests.py`, ~2 s). Selftest: OK (`scripts/selftest.py`, ~65 s; four
  new scenarios 4i–4l, the covered fingerprint and the tab-wrapper observer assertions). Both green at HEAD.
- `specs/examples/` holds twenty-two specs (README "Examples"); `specs/compare/` the comparison's three; `specs/local/`
  (ignored) has `hrm-toast-probe.json`, the live check of the toast capture.
- The worktree `~/.warp/worktrees/jev-browser-test/badlands-saguaro` is where this ran; `~/Downloads/jev-browser-test`
  is `main` and what `~/.claude/skills/jev-browser-test` points at.

## The six items and their commits

1. **Cut the first-run Claude cost** (`c221f4a`). `scripts/scaffold.py`: a spec that validates from `--url`, `--goal`
   and `--data key=value`, plus `--pass`, `--bug` (with `requires_action`), `--needs-human`, `--assert-url/-text/-in`,
   `--setup fill:|click:|press:|select:|wait_for:|wait_for_url:|goto:` (CSS brackets respected), `--secret` plus
   credential-like keys, `--slow`, `--stdout`, `--force`; nothing invented (no assertion unless given, `${ENV}` kept
   for run time). `SKILL.md` starts spec writing from it; its troubleshooting table and suites section moved to
   `references/troubleshooting.md` and `references/suites.md` behind short pointers: 292 lines / ~6.9k tokens →
   270 lines / ~5.4k tokens. Four unit tests.
2. **A built-in run stamp** (`e0a1ba1`). `${RUN_STAMP}` anywhere in a spec becomes one fresh value per run (the epoch
   second in base 36 plus two random characters, eight lowercase alphanumerics); `RUN_STAMP` in the environment wins
   (rerun against, or clean up after, one run's data); recorded as `result.run_stamp` / `trace.spec.run_stamp`. The
   skill says to use it for any data the app keeps. Five unit tests.
3. **Toasts as evidence** (`6e1216e`, glyph strip in `c221f4a`). `observe.ANNOUNCE_INIT_JS`, a context init script
   (runs in every document, survives navigations), reports each toast / ARIA live message once as it appears through a
   function the runner exposes on the page. Recorded on the step (`announcements`, `ms_before_observation`, flag
   `ANNOUNCED`), on the last executed action's history entry (`announced`), in `result.announcements`, and in Jev's
   state for three observations (`state.announcements`) with the outcome question saying an announced message counts;
   announced lines are appended to the adjudication lines, so `evidence.line` can read `live message: Successfully
   Saved`. Probed on OrangeHRM (`.oxd-toast` carries `aria-live=assertive`, appears 0.3 s after the click, gone at
   3 s) and checked live: a Personal Details save whose only confirmation is that toast passed with the toast as its
   evidence line, the outcome read at 0.99 from the announcement. Six unit tests, selftest 4l.
4. **Defer a marginal action while the page is busy** (`038cc9d`, widened in `8fea73d`). A CLICK, TYPE_TEXT or SELECT
   decided below `thresholds.covered_action_confidence` (0.8) while `covered_controls` > 0 is deferred once per page (a
   runner WAIT ending when the page changes; `step.action_deferred`, flag `DEFERRED-<OP>:n`); the next decision on the
   same page is executed (a layer that stays is a dialog). It began as a typing-only rule (the sidebar typings read
   0.54–0.67, the right fields 0.84–0.99); round 2 lost three Leave runs of three to a marginal CLICK on the next tab
   while the spinner before the confirmation dialog covered the form, so it now covers every targeted action. `038cc9d` also made
   an overlay lifting a **whole-page change**: the observation tags the covered controls (`data-jev-covered`) and the
   fingerprint re-reads how many are still covered, so every WAIT on such a page now ends the moment the overlay
   lifts (selftest: 629 ms instead of the 1500 ms ceiling). Selftest 4i, 4j.
5. **Outcomes that fire too early** (`038cc9d`). `outcome.after: {"click": "Search"}` (also `type`, `select`; several
   keys all required) defers the outcome until an executed action of that kind targeted a control whose label contains
   the text; recorded like `requires_action` (`outcome_deferred`, `DEFERRED:<name>`). Live cause: the Leave List's
   'No Records Found' fired on the unfiltered list before Search although the filter checks in `requires` read 0.82 /
   0.88. Three unit tests, selftest 4k.
6. **Housekeeping** (`f06f818`, `989ab2f`, `8fea73d` and the docs commit after them). The three OrangeHRM specs and
   the comparison specs on `${RUN_STAMP}`, the Leave spec with `after` and an accurate account of the page after
   Assign and after Ok, README rows and counts, the comparison numbers in
   `docs/superpowers/measurements/2026-09-24-claude-cost-comparison.md`, three rounds of the three specs × 3 on one
   worker in `2026-09-24-hrm-three-suite{-round1,-round2,}.{json,md}` (section "OrangeHRM fixes" of the measurements
   README), `.playwright-cli/` ignored. Two runner defects the rounds found and fixed on the way: the observer's
   tab-wrapper duplicate (`989ab2f`) and the deferral widened to clicks (`8fea73d`).

## Numbers

Three rounds of the three new specs, `--repeat 3 --workers 1`, each from a clean export
(`docs/superpowers/measurements/2026-09-24-hrm-three-suite{-round1,-round2,}.{json,md}`; the measurements README
section "OrangeHRM fixes" has the reading):

| spec | round 1 `f06f818` | round 2 `989ab2f` | round 3 `8fea73d` |
|---|---|---|---|
| `hrm-admin-add-user` | pass 3/3 | pass 3/3 | **pass 3/3** |
| `hrm-leave-assign` | pass 2/3 (duplicate tab split the choice) | 0/3 (the next tab clicked mid-request) | **pass 3/3** |
| `hrm-pim-add-employee-list` | pass 3/3 | pass 3/3 | **pass 3/3** |

Round 1's red run traced to OrangeHRM's top-row tabs being offered twice (an `<li>` with a pointer cursor around an
`<a>` of the same caption); `989ab2f` drops such wrappers. Round 2 then lost every Leave run to a click the duplicate
had been masking: the Leave List tab at 0.74 while the spinner before the 'Balance not sufficient' dialog covered the
form; `8fea73d` widens the covered-page deferral from typing to any marginal action, and the spec's goal names the wait
for the dialog. Round 3: nine of nine, and the deferral fired five times in the PIM runs (a premature "Employee List"
click while the Save was in flight in all three). The comparison's numbers are in
`2026-09-24-claude-cost-comparison.md`.

## Findings left as they are

- The comparison's Claude-token figures (71.6k / 5.7k / 19.3k, and an unreconciled 57k) are the earlier session's
  report, not re-measured; the Jev runs and the Playwright CLI snapshots are on disk and are the re-measurable half.
  The next comparison should start from the scaffold and record the session's usage report at the time.
- An announcement is the text of a live region or a toast-like class; an app whose toasts have neither is not captured
  (the troubleshooting row says to anchor on the stable state).
- The deferral of a marginal typing is once per page signature; on a page whose layer never lifts the second decision
  is executed as-is.
- `.playwright-cli/` in the worktree holds the comparison's Playwright CLI snapshots (126 KB, ten files); ignored, kept.

## Suggested next steps

- Rerun the comparison from the scaffold (two flows, both paths, one session) and record Claude's tokens from the usage
  report; the break-even claim then rests on two measured points.
- Run the full examples suite (`specs/examples/*.json --repeat 3 --workers 2`, the `hrm-*` specs on one worker) at HEAD
  for a measurements section like the eighteen-spec one; this session ran only the three new specs.
- Use the skill on WasteHero from the scaffold (a staging URL and a test account are the inputs; `specs/local/`).
