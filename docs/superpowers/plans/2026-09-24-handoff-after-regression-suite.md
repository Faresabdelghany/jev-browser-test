# Handoff after the regression suite and the second comparison (2026-09-24, 12:15–13:45)

Fares approved the plan of the previous handoff: the regression suite of the other nineteen example specs at `9edd768`,
the comparison re-measured from the scaffold, `gh auth switch` (already done: the active account was Faresabdelghany
and `git push` worked) and a fresh `.skill` zip. This session ran the suite, found the OrangeHRM demo in a slow hour,
fixed the three runner defects the hour exposed plus a scaffold defect the comparison exposed, sharpened two specs,
re-measured the comparison, and left one thing for a normal hour. Start with `git pull` (main is fast-forwarded to this
branch), then `docs/superpowers/measurements/README.md` section "Regression suite after the OrangeHRM fixes" and
`2026-09-24-claude-cost-comparison.md` section "Second measurement".

## Commits on badlands-saguaro (main fast-forwarded, pushed)

- `d42c243` a click whose navigation outlasts `action_timeout_ms` is a landed, slow action (`navigation_pending`,
  `await_navigation`, `executed.slow_navigation`, flag `SLOW-NAV:<s>`; the same on a `setup` click); a pass sighted on a
  still-busy page whose assertions do not hold yet is rechecked (`assertions_can_wait`, flags `RECHECK:n
  ASSERT-PENDING:n`). Unit tests on Playwright 1.63's real call log; selftest 4m (a local site whose module page
  answers after 1 s), 4n (a save whose toast comes under the overlay).
- `0e2bc07` a busy page is one with covered controls or none at all (`page_busy`), both confirmation branches park on it;
  `hrm-add-employee` budget 24 / 240; `table-sort-due`'s bug outcomes carry `after: {click: Due}`. Selftest 4o.
- `b487e2e` `dynamic-controls`' pass outcome names the buttons' captions with the messages (the two-message wording read
  0.77–0.82 on the finished page; 0.96–0.97 now); the suite results so far under measurements.
- `81ce6a2` a busy page gets two more confirmation looks (`recheck_limit`: 2, or 4 while busy); the scaffold's comment no
  longer spells `${ENV_VAR}` / `${RUN_STAMP}` (the loader scans the whole spec: a scaffolded login spec ended exit 2);
  the comparison's two scaffolded specs under `specs/compare/scaffold-*.json`, its results under
  `measurements/2026-09-24-comparison-2/`.
- the docs commit after it: the measurements README, the comparison's second section, README rows, this handoff.

Unit tests 132 (`.venv/bin/python scripts/unit_tests.py`), selftest OK (~75 s).

## Results

- **The seventeen non-OrangeHRM specs**: unchanged verdicts at `9edd768`, `d42c243` and `0e2bc07` (three suites × 3
  repeats, two workers; `2026-09-24-regression-<sha>-examples.md`): no runner regression. Two spec fixes from what the
  suites showed: `table-sort-due` (`after` on the bug outcomes; one run had ended `not_sorted` after a footer-link
  click) and `dynamic-controls` (the wording at the gate; 3/3 at 0.96–0.97 after).
- **The five OrangeHRM specs**: 3/15 at `9edd768` (twelve `low_confidence` runs all starting with a sidebar click
  reported failed: Playwright's 8 s timeout on the navigation it scheduled, the page arriving anyway), still host-bound
  at `d42c243` (partial) and `b487e2e` (login 3/3, pim-add-employee-list 3/3 once the host was normal, add-employee
  0/3, admin and leave 1/3). The demo's login page took 3–7 s to serve from 12:15 to at least 13:40 (0.9 s normally).
- **The comparison** (13:12–13:31, both paths, one session, tokens from the transcript): Jev path first run from the
  scaffold 36.7k new tokens (six runs in the slow hour, one exit 2 from the scaffold defect), rerun 5.4k, Playwright
  CLI path 21.7k; break-even at the first rerun (second, with the `SKILL.md` read added). Reported before: 71.6k /
  5.7k / 19.3k, break-even 3.8.

## Open

1. **Rerun the five OrangeHRM specs in a normal hour** (the one thing this session could not do):
   `curl -o /dev/null -s -w '%{time_total}' https://opensource-demo.orangehrmlive.com/web/index.php/auth/login` under
   1.5 s three times, then from a clean export (`git archive <sha> | tar -x -C <dir>`, copy `.env`):
   `GIT_COMMIT=<sha> python scripts/run_suite.py specs/examples/hrm-*.json --repeat 3 --workers 1 --out runs/suite/hrm-<sha>`.
   Record it as `2026-09-24-regression-<sha>-hrm.{json,md}` and finish the measurements section; the README's
   `hrm-add-employee` row says "rerun in a normal hour pending".
2. Two things the slow hour showed and this session did not change, for a design pass rather than a patch: Jev's
   BLOCKED (`site_refused_or_error`) after three undecided looks on a form still covered by its loader (the undecided
   steps already wait with backoff; a covered page might restart or extend that count), and the sidebar filter typed
   into at 0.81–0.89 with the form covered (`thresholds.covered_action_confidence` is 0.8; 0.9 for the OrangeHRM
   specs would defer those and still let the Leave flow's Ok at 0.93–0.97 through).
3. A normal-hour repeat of the comparison from `specs/compare/scaffold-*.json` (the two specs as they passed): J2 plus
   one CLI drive, ~30k tokens.
4. `~/Downloads/jev-browser-test-<sha>.skill` (`git archive --format=zip --prefix=jev-browser-test/ <sha>`) is written
   at the end of this session for Claude Desktop; Claude Code sees the code through the symlink after `git pull` in
   `~/Downloads/jev-browser-test`.
