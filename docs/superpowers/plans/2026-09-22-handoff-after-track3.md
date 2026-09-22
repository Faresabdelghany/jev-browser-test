# Handoff after Track 3 (2026-09-22)

All three tracks of `docs/superpowers/specs/2026-09-21-ultrafast-loop-and-results-contract-design.md` are
implemented, measured and pushed to `main`. The brief (`2026-09-21-implementation-brief.md`) stays the
rulebook for commands, non-negotiables and the push recipe. Start with `git pull`.

## State of the repo

Selftest (`.venv/bin/python scripts/selftest.py`, 20 numbered checks, ~25 s) and unit tests
(`.venv/bin/python scripts/unit_tests.py`, 70 tests) are green at HEAD. `.env` and `.venv` are local and
git-ignored. Every number in README / SKILL.md / references comes from a file under
`docs/superpowers/measurements/` (see its README for how each row is derived).

Commits of this session, in order (`1c79f1b..67cb084`):

- Review triage, one commit per theme: `37c6a94` CDP selftest waits for the first tab (must_fix) ·
  `ca32c7c` bench.py records per-step latencies and timing, Track 1 files back-filled, measurements README
  corrected (must_fix; badpw confidence 0.70 → 0.41 now stated, baseline commit `9cce64a`, A/B provenance) ·
  `eeb2006` loop edge cases (stale streak reset, low-confidence WAIT waits `settle_ms`, terminal capture at
  `max_steps`, screenshot timeout + `screenshot_error`, popups closed in attached mode, unreachable browser
  → exit 2) · `b5420ba` observer fields (captions vs values, contenteditable, search/list roles, disabled
  optgroup, closed `<details>`, label-proxy tuple, pointer-events, exact text-head prefix) · `cbc3160`
  typed secrets masked in every observation · `868a331` options wait needs a *new* option · `032ff60`
  neutral demo vocabulary everywhere · `5954577` docs brought in line with Track 1.
- Track 2: `1ee2ed8` the results contract (spec, policy, runner, summarizer, selftest, unit tests) ·
  `1aec493` smoke specs rewritten with outcomes + assert · `6d1d5cc` `first_seen_at_step` · `1327df4`
  docs · `185a10f` measurement.
- Track 3: `8780958` `run_suite.py` + `report.py` · `ef0c9e9` docs · `67cb084` acceptance record.

## Numbers (medians of 5 live runs each; files in `docs/superpowers/measurements/`)

| | Track 2 before (`5954577`) | Track 2 after (`1aec493`) |
|---|---|---|
| `smoke-login` | passed 5/5, 4,825 ms, 4 requests, 5,126 tokens, conf 0.96 | `logged_in` (pass) 5/5 confirmed, 3/3 assertions, 6,030 ms, 6 requests, 8,932 tokens, conf 0.96 |
| `smoke-login-badpw` | never_violated 2/5 + low_confidence 3/5, 6,439 ms, conf 0.41 | `bad_credentials` (pass, negative test) 5/5, first seen at step 4 in 5/5, 6,062 ms, conf 0.93 |

Track 3 acceptance (`2026-09-22-track3-suite.json`): 2 specs × 5 repeats, 4 workers, **18.6 s**, all pass,
agreement 100% (acceptance < 60 s ✓).

Acceptance per the spec: §5.8 all four items ✓ (badpw at first sighting; smoke-login confirmed with all
assertions; old-style specs unchanged in status via synthesized outcomes, covered by the selftest;
selftest OK). §6: timing ✓, agreement / flaky computed and unit-tested ✓, the phrasing A/B re-run through
the suite ✗ (see deviations).

## Deviations and things to know

1. **The contract has a price**: +1 confirmation step and +1 adjudication request per run, and two extra
   Choices (`outcome`, `blocked_reason`) on every request: +25% wall and +74% input tokens on the demo
   pass path. Written down in the measurements README and the top-level README. If it matters, the cheap
   levers are shorter `BLOCKED_REASONS` descriptions and asking `blocked_reason` only when Jev's operation
   is BLOCKED/WAIT (the spec asked for "always"; measure before changing).
2. **Phrasing A/B not re-run through `run_suite.py`** (§6 acceptance, third item): the env knob behind
   `2026-09-22-track1-ab-phrasing-implicit.json` was removed after the tie, as the brief required, so there
   is nothing to switch. Re-adding a temporary knob for one suite run would cost ~20 live runs to re-measure
   a recorded tie.
3. **Outcome names may equal check names** (`logged_in` is both in `smoke-login`). Validation forbids
   only `none_yet` and the reserved question names; the spec's own example uses `logged_in` in both roles.
4. **`never_violated` no longer occurs**: a fired `never` check ends as status `outcome` with
   `never_<check>` (verdict bug), as the spec says. The status stays in `TERMINAL_STATUSES` for old traces.
5. **`seen_at_step` vs `first_seen_at_step`**: for a pass, `first_seen_at_step` is the sighting and
   `seen_at_step` the confirming step one later; for other verdicts they are equal.
6. Review findings deliberately **not** acted on (recorded in `2026-09-22-track1-review-findings.md`):
   the viewport-first text head makes DONE/BLOCKED/PRESS_ENTER stale when a fixed-position animated
   ticker crosses the fold (a consequence of §4.8's viewport-first text; rare, ends `unstable_page` with a
   documented remedy, not a wrong click); `page_changed: false` for an action whose effect lands after the
   DOM-quiet settle (inherent to the event-based settle; raise `quiet_ms` per spec); an overlay appearing
   over the target *during* the decision is caught by Playwright's actionability wait, then force-clicked
   and recorded `forced: true` (the design delegates hit-testing to Playwright; `pointer-events: none` and
   opacity-0 now do make the tuple stale); the settle's navigation-retry path has no fixture test.
7. Live runs were measured from a clean `git archive HEAD` export in the scratchpad so that edits to the
   working tree could not leak into the subprocess runs; do the same for any number that cites a commit.

## Suggested next steps (none required by the spec)

- Try the skill on a real app with `run_suite.py --repeat 3` and look at the outcome distributions; the
  demo site cannot show `flaky`, `stuck_reason` or `outcome_unconfirmed` in the wild.
- If tokens matter, measure the two levers in deviation 1 with `bench.py` before and after.
- The `report.py` page has no suite-level index; `results.md` is that index today.

## Reminders

- The skill's copy in **Claude Desktop is behind the repo** (it was behind after Track 1 already; three
  more tracks of changes since). Exporting from Desktop over this folder would revert everything above;
  re-import from the repo (or stop exporting) before the next round.
- Push recipe: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`.
- Live runs cost credit (~6 requests each now); the offline selftest and unit tests cover everything else.
