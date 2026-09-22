# Brief for the next session — after the real-application trial (2026-09-22)

You are continuing work on the `jev-browser-test` repo. The design is implemented, measured, reviewed and
tried against real applications; this session closes what the trial left open. Read this brief, then the
handoff it points to, then start. Do not re-brainstorm the design. Ask only where this brief says to.

## 1. Where things are

- Repo: `/Users/fares/Downloads/jev-browser-test` (git, branch `main`, remote
  `https://github.com/Faresabdelghany/jev-browser-test`, **public**). Start with `git pull`; HEAD should be
  at or after `eadb9e5`.
- Read first: `docs/superpowers/plans/2026-09-22-handoff-after-real-app.md` (state, the nine trial specs,
  the three runner fixes, findings left as they are, deviations 1–7), `docs/superpowers/measurements/README.md`
  (last section: the runner at `eecf79e`), then `SKILL.md` and `references/*.md`. The rulebook is still
  `docs/superpowers/plans/2026-09-21-implementation-brief.md` (§1 environment, §2 shape, §4 non-negotiables).
- State at `eadb9e5`: unit tests 76 (`.venv/bin/python scripts/unit_tests.py`), selftest OK
  (`.venv/bin/python scripts/selftest.py`, 25 run scenarios plus observer / settle / CDP / dotenv checks,
  ~39 s). Both green at HEAD.
- **Untracked, local only**: the nine trial specs in `specs/local/` (`shop-checkout`,
  `shop-add-second-item`, `shop-checkout-problem-account`, `shop-checkout-error-account`, `wiki-search`,
  `todo-add-filter`, `load-wait`, `notify-random`, `modal-close`) and their results in `runs/trial-1..3/`.
  They target public demo and practice sites with public demo credentials inline in `setup`. If they are
  missing, the handoff's table describes each flow well enough to rewrite them; `scratchpad/peek.py` (a
  Jev-free dump of the observer's table for a URL) is gone with the scratchpad, rewrite it from
  `observe.observe` + `render_table` if needed.
- Commands: as in the previous brief (`spec.py` validates, `run_test.py` one live run, `summarize_trace.py
  --result` first, `run_suite.py … --repeat N --workers W` hands-off, `bench.py … --repeat 5 --json`);
  `report.py runs/suite/<ts>` renders a whole suite. Measurements that cite a commit come from a clean
  `git archive <sha>` export in the scratchpad with `.env` copied in and `GIT_COMMIT=<sha>` set, bench then
  suite, files under `docs/superpowers/measurements/` as `<date>-<what>-<file>.json` plus a README section.
- Pushing: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`. End every commit
  message with the attribution line your session's system reminder specifies.

## 2. What this session does, in order

### Block D — the trial specs become committed examples (ask Fares first: yes or no)

The specs use public sites and public demo credentials, exactly like the committed smoke specs. If Fares
says yes:

D1. `git mv`-equivalent: copy `specs/local/*.json` to `specs/examples/`, validate each, one commit. Keep
    `specs/local/` git-ignored for genuinely private applications. Update the `.gitignore` comment.
D2. One suite run of `specs/examples/*.json --repeat 3 --workers 2` from a clean export of D1's commit with
    `GIT_COMMIT` set; commit `results.json` / `results.md` as `<date>-examples-suite.json` / `.md` with a
    README section. Expected from the trial: 7 pass, `shop-checkout-problem-account` bug,
    `shop-checkout-error-account` undetermined suggested bug. Triage anything else with the rubric.
D3. Name the sites and flows in a short "Examples" section of README.md and in SKILL.md ("Files"), and
    replace the generic wording of the handoff's trial table with the ids and sites (a one-line note that
    the specs are now committed). One commit.
D4. Push.

If Fares says no, skip to block E and leave the specs where they are.

### Block E — a live `flaky`

The computed `flaky` verdict is covered by unit tests only; the random-result page succeeded 6/6 times.
E1. Run `notify-random` (or its example twin) with `--repeat 5` once; if every run agrees, run the practice
    site's other random page (menu entries that appear or disappear at random) written as a spec whose pass
    is "every entry is listed" and whose bug is "an entry is missing", `--repeat 5`.
E2. Record the first `flaky` verdict from a committed `results.json` (clean export, `GIT_COMMIT`), with the
    outcome distribution and agreement, in the measurements README and in the handoff. If neither page
    disagrees in 10 runs, say so and stop; do not manufacture flakiness.

### Block F — the token and time levers (only if Fares says tokens or time matter; skip otherwise)

Each lever: measure from a clean export with `bench.py` (5 repeats, both smoke specs, plus the loader
spec for F4) before and after, keep it only if it wins, record a deviation in the handoff and in the design
spec §5 when it changes what the spec prescribes:
F1. ask `blocked_reason` only when Jev's operation is BLOCKED or WAIT (the spec says "always");
F2. shorter `BLOCKED_REASONS` descriptions;
F3. send each adjudication line once (`state.lines` and the criteria both carry them);
F4. WAIT backoff: double the pause on consecutive WAITs on an unchanged page (400, 800, 1,600 ms, capped),
    measured on `load-wait` (10 requests, 10.8 s today) and on the selftest loader fixture;
F5. a lower default `observation.max_text_chars` for long pages, measured on `wiki-search` (~9.6k input
    tokens per request today); only if decision confidence and the outcome are unchanged.

### Block G — evidence lines for compound statements (optional, small)

The adjudication picks no line for a `when` that names several facts or an absence (handoff, "Findings
left as they are"). G1. In `policy.build_adjudication`, ask one `evidence_line` Choice per sentence of the
statement (split on ". " / "; " / ", and "), keep the first line found, in code. G2. Selftest scenario with
a two-sentence outcome statement whose second sentence is the one on the page. G3. Live check on
`todo-add-filter` (`evidence.line` was null in 2 of 3 runs). One commit, or drop it if it costs a request
per sentence: one adjudication request per run is the budget.

## 3. Non-negotiables (unchanged)

- Stdlib + Playwright only. Every behavioural change lands with a selftest scenario or unit test; both
  suites green after every task. Keep the `run_test.run(spec, jev, out_dir)` seam and the fake Jev.
- Keep `spec.data`: Jev only chooses among prepared strings. Targets are indices into the observed table.
- Never commit `.env`, `runs/`, `.venv/`, `.remember/`, `specs/local/`. Employer-specific content (URLs,
  flows, company names, account handles) never enters a tracked file; public demo sites are fine once
  Fares has said yes in block D.
- Every number in the docs comes from a committed `bench.py` / `run_suite.py` file taken from a clean
  export with `GIT_COMMIT` set. 5 repeats per spec is the ceiling for a measurement, 3 for an example suite.
- Small commits, one per task, push after each block. Implement directly; no multi-agent review workflows.
  Live runs only where a block needs them. After an observer change, dump the real page's table without
  Jev before spending a run (handoff deviation 3).

## 4. When you finish (or stop)

Write `docs/superpowers/plans/<date>-handoff-after-examples.md` in the shape of the current handoff: state
of the repo (test counts, HEAD), commits of the session, what changed, the numbers with their files,
deviations. Push it. Report to Fares in a few lines: what passed, what was found, what was left out and why.
