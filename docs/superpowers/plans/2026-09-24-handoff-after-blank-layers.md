# Handoff after the normal-hour reruns and the blank-layer work (2026-09-24, 13:45–15:30)

Fares asked for a check of everything and then to "go on with everything till you get everything done", WasteHero set
aside. The previous handoff's open items were: the five OrangeHRM specs in a normal hour, two design questions the slow
hour had raised (Jev's BLOCKED after three undecided looks on a covered form; `covered_action_confidence` 0.9), the
comparison's normal-hour repeat, and the `.skill` zip. All four are done; the reruns found three more runner
limitations, each fixed test-first and rerun. Start with `git pull` (main is fast-forwarded to this branch), then the
measurements README section "Blank layers (2026-09-24, afternoon)" and the comparison's "Third measurement".

## Commits on badlands-saguaro (main fast-forwarded, pushed; `~/Downloads/jev-browser-test` pulled, the skill symlink points there)

- `1b69699` **a blank layer is a loader, a layer with controls is a dialog**: the observer counts the covering layer's own
  controls (`layer_controls`); a marginal action under a blank layer is deferred with backoff up to five times on one
  page (was once per page, then executed whatever it was: the sidebar filter took the first name at 0.77–0.83 and the
  Leave List tab was clicked at 0.71 before the dialog, in every slow-hour run at `6f9c5be`); nothing is deferred under
  a dialog or an open list; undecided looks under a blank layer get two more (`low_confidence_limit`);
  `covered_action_confidence` 0.9 (was 0.8). Flags `COVERED:n(layer:m)`, `DEFER-LIMIT:k`. Selftest 4j–4j4.
- `6deea29` **busy confirmation looks run for as long as a page may take to arrive**: past the count bound a look on a busy
  page parks again while the confirmation's waits are under `navigation_timeout_ms` (`can_recheck`,
  `step.recheck_waited_ms`), because a record page rendering 30 s after Save outlasted four busy looks. Selftest 4o2.
- `b740501` **an autocomplete's loading row is a busy signal**: `[role=option]` rows that only say 'Searching....' /
  'Loading...' are not offered, counted (`loading_options`, `LOADING:n`), kept out of the settle's options wait, and
  `page_loading` (a blank layer, or such a row) drives the deferral (`DEFERRED-<OP>:loading`) and the undecided looks'
  extra two; `hrm-admin-add-user`'s goal filters by the username unconditionally (the demo's user table passed fifty
  rows, one page, during the day). Selftest 4j5, `settle_check`'s placeholder case.
- `0ce1c20` the measurements README names `b740501`; this handoff and the README rows come in the docs commit after it.

Unit tests 135 (`~/Downloads/jev-browser-test/.venv/bin/python scripts/unit_tests.py`; the worktree has no venv),
selftest OK (~100 s).

## Results (all under `docs/superpowers/measurements/`, the reading in the README's afternoon section)

- **The seventeen non-OrangeHRM specs at `1b69699`**: no verdict moved; no deferral fired; `wiki-search`'s suggestion
  pick under its open list goes at once now (`COVERED:1(layer:2)`, 4 requests against 5). Three Heroku cold starts.
- **The five OrangeHRM specs**: 11/15 at `6f9c5be` as the demo recovered (the once-per-page deferral: the reds' cause),
  13/15 at `1b69699` in a slow hour (the deferral fix visibly working; the add-employee red was the recheck bound,
  the Leave red the 'Searching....' row), 12/15 at `6deea29` in a normal hour (the admin table past fifty rows, the
  'Searching....' row again), and **13/13 flows at `0ce1c20`** in a normal hour (two setup failures, the host).
- **The comparison, normal hour**: Jev path rerun 8.1k new Claude tokens (both scaffold specs green at once, 7 s and
  41 s of browser time), Playwright CLI path 15.0k (six turns, 88 s); break-even at the fourth run against the second
  measurement's first run. `2026-09-24-comparison-3/`.

## Open

1. The `0ce1c20` suite in a normal hour: **all pass, thirteen flows of thirteen**, two setup failures that were the
   demo's navigations timing out before the flow (recorded, not outcomes). Nothing is open on the OrangeHRM specs; the
   next full suite (`specs/examples/*.json --repeat 3`, the seventeen on two workers, the five on one) is the check
   after the next runner change. To read a red: `summarize_trace.py <run>/trace.json`, the first flag of the run,
   `--step n` for the offered elements; `SLOW-NAV`, `LOADING`, `DEFERRED-*` with the pass late is the host.
2. The demo's data grows during the day (users past fifty rows, many 'Jevtest' employees): a spec that depends on a
   row being on the first page of a list is a test issue waiting to happen; filter or search instead.
3. `~/Downloads/jev-browser-test-<sha>.skill` is written at the end of this session for Claude Desktop.
