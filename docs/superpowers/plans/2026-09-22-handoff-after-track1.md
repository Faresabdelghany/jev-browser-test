# Handoff after Track 1 (2026-09-22)

Read this, then `docs/superpowers/plans/2026-09-21-implementation-brief.md` (still the rulebook: commands,
non-negotiables, push recipe) and the spec `docs/superpowers/specs/2026-09-21-ultrafast-loop-and-results-contract-design.md`
sections 5 and 6 for what is left. Start with `git pull`.

## State of the repo

Track 1 (spec §4, items 4.1–4.11) is implemented, measured and pushed to `main` (`e20f461..74a04f4`).
Selftest (`.venv/bin/python scripts/selftest.py`, 17 checks) and unit tests (`.venv/bin/python
scripts/unit_tests.py`, 50 tests) are green at HEAD. `.env` and `.venv` are in place locally and
git-ignored. Tracks 2 and 3 are **not started**.

Commits, one per task: 4.1 `8479593` persistent connection · 4.7 `4e41727` strict answer validation ·
4.2 `278a0b1` structured state · 4.3 `12fdb1a` object criteria · 4.4 `cdb71ed` rules · 4.5 `7fc950f`
event-based settle · 4.6 `316c17a` freshness guard · 4.8 `1c3aef5` observer defaults + viewport-first
text · 4.9 `9bc02cc` CDP attach · 4.10 `f693ebb` screenshot policy · `c3382c2` adoption after the
measurement · `7e0b1c7` after-measurement + numbers · `74a04f4` mock keychain for the CDP selftest.

## Measurement result (details: `docs/superpowers/measurements/README.md`)

| | baseline | after |
|---|---:|---:|
| `smoke-login` wall (5 runs, median) | 8,896 ms, passed 5/5 | 5,165 ms (−42%), passed 5/5 |
| warm Jev request | 770 ms | 307 ms |
| browser per action | 646 ms | 147 ms |
| decision confidence | 0.94 | 0.95 |
| input tokens per run | 3,858 | 5,126 |
| `smoke-login-badpw` wall | 11,563 ms, never_violated 5/5 | 6,040 ms (−48%), low_confidence 5/5 |

Acceptance: wall ≥ 40% lower ✓, confidence not lower ✓, selftest OK ✓, outcomes unchanged ✓ for
`smoke-login` and ✗ for `smoke-login-badpw`. The badpw flip is a knife-edge `never` check (0.73–0.84
against `never_true = 0.8` in every configuration including the baseline); the same configuration ended
`never_violated` 5/6 in the two batches minutes earlier. The spec was not loosened. Track 2's outcome
Choice is the designed fix and its §5.8 acceptance targets exactly this spec.

## Deviations from the spec, all measured and documented

1. **Rules (4.4) are opt-in** (`"rules": true` in a spec; default off). Attached in any wording tried they
   lowered the operation decision's confidence and made badpw hesitate between TYPE_TEXT and BLOCKED
   (the page text hints at the right password); the CHECK rule pulled a borderline check from 0.85 to 0.68.
   Nine A/B files under `docs/superpowers/measurements/2026-09-22-track1-ab-*.json`; the table is in
   `measurements/README.md`. `scripts/rules.py` keeps the wording and the numbers.
2. **Labels of already-offered controls are no longer offered as clickables** (observer pass 3). With the
   structured state Jev clicked "Username" before typing into it (two wasted steps per run).
3. **`trace.timing`** {launch, navigation, setup, steps, final} was added so the wall-clock budget is
   visible (~2 s of the remaining 5.2 s is the remote site's page load).
4. The target-question phrasing A/B (named vs implicit premise) tied; the named premise stays.
5. Note for the owner: on this demo the old one-line request shape scored marginally higher confidence
   (0.99 vs 0.95) with a third fewer tokens (`...-ab-speed-only-nolabels.json`). The structured shape was
   kept because it meets the acceptance against the baseline and the design's reasons for it
   (`page_changed` feedback, `current_value` criteria) need a richer app than the demo to show.

## Open: the Track 1 code review (unverified findings)

A 27-reviewer pass (spec compliance, correctness, hygiene per commit) was run and stopped before its
skeptic-verification and fix stages to save budget. The raw findings are in
`2026-09-22-track1-review-findings.md` (88 must/should findings, ~83 distinct, **unverified**: expect
duplicates, some wrong, and several that are the same stale-doc issue seen from different commits).
Themes worth acting on first, in this order:

- **must_fix (2)**: `cdp_check` in `selftest.py` snapshots the remote-debugging tab list before Chromium
  has finished opening `about:blank` (timing-fragile); README/measurements quote per-request and
  per-action medians (307/770 ms, 147/646 ms) that are derived from the traces, not present as fields in
  the bench JSON — either add those fields to `bench.py` output or say how they were derived.
- Stale docs after 4.10/4.6: SKILL.md step 3 still says "a screenshot per step, taken before the
  decision"; README Layout/exit-code list omit `unstable_page`, `rules.py`, `bench.py`, `unit_tests.py` and
  say "8 scenarios"; `element_label` docstring; runner-design Files table; SKILL.md troubleshooting lacks
  `unstable_page` and the `cdp_url` route for "page needs an existing login session".
- Correctness candidates in `observe.py` / `run_test.py`: `current_value` shows the caption of
  `input[type=submit|button]` and the static content of textareas; secrets typed into non-password fields
  come back unmasked through observed element values (also in the trace); `visibleText(500)` is not
  always a prefix of `visibleText(4000)` (the in-viewport bucket cut), so the "text head" claim in
  runner-design is not exactly true; the options-wait after TYPE_TEXT fires on any already-visible
  `[role=option]`; `stale_streak` is not reset by an intervening low-confidence step; a `cdp_url` nobody
  listens on ends in a traceback and exit 1 with no trace.json instead of exit 2; runner-inserted WAITs
  (low confidence, stale) now wait only ~quiet_ms; `budget_exhausted` at max_steps gets no terminal
  screenshot in "key" mode.
- Hygiene: `assets/spec.example.json`, the selftest controls fixture and some doc anecdotes use a
  waste-container / pickup-order flow and "Nile Bakery" (no company name or URL, but recognisably the
  employer's domain); the example spec pins `max_elements` to 70.

## What to do next

1. Triage the findings above (verify before fixing; the two must_fix first), one commit per theme,
   selftest + unit tests green, push.
2. Track 2 (spec §5): outcomes + assert in `spec.py`, per-step `outcome` / `blocked_reason` /
   `stuck_reason` questions, termination rules, final adjudication request, `result.json`, synthesized
   outcomes for old specs, docs + rubric + SKILL.md steps 2–4, selftest cases; acceptance §5.8. Add
   `outcomes`/`assert` to both smoke specs (`smoke-login-badpw` is a negative test: `bad_credentials`
   should carry `verdict: "pass"` with a note that the wrong password is deliberate). Measure with
   `bench.py` before/after as Track 1 did.
3. Track 3 (spec §6): `run_suite.py`, `results.json` + `results.md` with agreement/flaky, `report.py`,
   SKILL.md `run_in_background` guidance; acceptance §6.

## Reminders

- The skill's copy in **Claude Desktop is behind the repo**. Exporting from Desktop over this folder
  would revert everything above; re-import from the repo (or stop exporting) before the next round.
- Push recipe: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch` (toggles back).
- Live runs cost credit (~4–7 requests each); the offline selftest and unit tests cover everything else.
