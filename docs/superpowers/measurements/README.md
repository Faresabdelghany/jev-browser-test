# Measurements

Every performance number in the README, SKILL.md and `references/` comes from `scripts/bench.py` output
committed here (Track 3's from `scripts/run_suite.py`'s `results.json`, which reuses bench's per-run measures
but keeps a shorter median list). Files are named `<date>-<track>-<what>.json`; each holds the per-run
records and the medians for one or more specs, plus the git commit the runs were made at when the bench could
read it: `2026-09-22-track2-before.json` / `-after.json` record `git_commit: null` because they were run from
a `git archive` export (no `.git`; `bench._git_commit()` now falls back to a `GIT_COMMIT` environment
variable, so set it when benching from an export). Since 2026-09-22 each run record also carries the
result headline the tables quote (`first_seen_at_step`, `confirmed`, `assertions_ok` / `assertions_total`,
`evidence_line`) and `adjudication_ms`, the one request `requests` counts that the per-step `jev_ms` sum does
not; the Track 2 files predate those fields, so their "first seen" and "confirmed, 3/3 assertions" rows come
from the run traces on disk, not from the committed file.

How to read a file: `specs.<id>.medians` holds the per-run medians of every `RUN_FIELDS` entry (wall,
duration, Jev ms, browser ms, requests, tokens, decision confidence, stale steps, the first request's
latency, the per-run warm-request and per-action medians, `trace.timing`) plus three medians pooled over
every step of every run: `decision_confidence_all_steps`, `jev_warm_ms_all_steps` (median `latency_ms.jev`
of steps 2..n, the first step paying for the TCP + TLS handshake) and `browser_per_action_ms_all_steps`
(median `latency_ms.browser` of the steps that executed a browser action; runner-inserted waits and
terminal markers excluded). The "Jev request, warm" and "browser per action" rows below are those two
pooled medians. The per-step lists are in each run record (`step_jev_ms`, `step_browser_ms`,
`action_browser_ms`, `step_confidences`) so anything here can be recomputed from the file alone. The
per-step fields were added to `bench.py` on 2026-09-22 and back-filled into the twelve Track 1 files from
their run traces (`backfilled` in each file says so); every previously stored median is unchanged.

## Track 1 (2026-09-21/22): the jev-ultrafast loop

Both smoke specs, 5 repeats, medians. Baseline = commit `9cce64a`, the tree before `e20f461` added
`bench.py` (no loop change between the two).

| spec | measure | baseline | after (`c3382c2`) |
|---|---|---:|---:|
| `smoke-login` | outcome | passed 5/5 | passed 5/5 |
| | wall-clock | 8,896 ms | 5,165 ms (−42%) |
| | Jev request, first (handshake) | 832 ms | 766 ms |
| | Jev request, warm | 770 ms | 307 ms |
| | browser per action | 646 ms | 147 ms |
| | decision confidence (median) | 0.94 | 0.95 |
| | input tokens per run | 3,858 | 5,126 |
| `smoke-login-badpw` | outcome | never_violated 5/5 | low_confidence 5/5 (see below) |
| | wall-clock | 11,563 ms | 6,040 ms (−48%) |
| | Jev request, warm | 751 ms | 328 ms |
| | browser per action | 642 ms | 146 ms |
| | decision confidence (median) | 0.70 | 0.41 (see below) |

`trace.timing` (recorded from `c3382c2` on): launch 152 ms, navigation to the remote site 1,979 ms, so
about 2 s of the remaining 5.2 s is the site's own page load.

Acceptance (spec §4.11): wall ≥ 40% lower ✓ (both specs); outcomes 5/5 unchanged ✓ for `smoke-login`,
✗ for `smoke-login-badpw`; median decision confidence not lower ✓ for `smoke-login` (0.95 vs 0.94),
✗ for `smoke-login-badpw` (0.70 → 0.41); selftest OK ✓.

**About the `smoke-login-badpw` confidence.** The drop is concentrated on the steps after the failed
login: on that page (the form again, "Your password is invalid!" above it) the `operation` decision read
0.15–0.42 in the baseline and 0.04–0.12 after (step 4 of every after-run: 0.08, 0.05, 0.04, 0.09, 0.12).
The three refused low-confidence steps at 0.03–0.30 drag the run median from 0.70 to 0.41. The A/B files
isolate the cause to the structured state, not the rules: with the old one-line request shape the same
step reads 0.27–0.34 (`...-ab-speed-only-nolabels.json`) against 0.05–0.07 with the structured shape
(`...-ab-structured-no-rules-nolabels.json`). This is the "structured state changes Jev's behaviour →
revert per item if worse" risk from spec §7; the structured shape was kept anyway, for the reasons in the
last paragraph of this section, and the trade-off is recorded here rather than hidden. Track 2's outcome
Choice ends this spec at the first sighting of the error, so the hesitant post-login steps disappear.

**About `smoke-login-badpw`.** Its `never` check (`"A red flash message says the username or password is
invalid"`) reads 0.73–0.84 on a page that says "Your password is invalid!", i.e. it straddles
`never_true = 0.8` in every configuration, including the baseline (0.75/0.76/0.78 for three steps, then
0.80–0.84). Whether a run ends `never_violated` or `low_confidence` after three refused steps is decided
by that ±0.03. With the final configuration the same spec ended `never_violated` in 5 of 6 runs in the
two A/B batches taken minutes earlier (`2026-09-22-track1-ab-structured-no-rules-nolabels.json`,
`...-phrasing-implicit.json`) and 0 of 5 in the final batch. This is the "never check hovering at
0.7–0.8" test-issue pattern the verdict rubric documents; the spec was deliberately not reworded or
loosened to get green, and Track 2's outcome Choice is the designed fix (a Choice compares the endings
instead of thresholding one Noul).

## Track 2 (2026-09-22): the results contract

Both smoke specs, 5 repeats, medians. Before = commit `5954577` (Track 1 plus the review fixes; the specs
still written with `done_when` / `never`), after = commit `1aec493` (outcomes + assert in the runner and
in both specs); both attributions are from the session notes, the files themselves carry `git_commit: null`
(see the top of this page). Files: `2026-09-22-track2-before.json`, `2026-09-22-track2-after.json`.

| spec | measure | before | after |
|---|---|---:|---:|
| `smoke-login` | result | passed 5/5 | `logged_in` (pass) 5/5, confirmed, 3/3 assertions |
| | wall-clock | 4,825 ms | 6,030 ms (+25%) |
| | Jev requests | 4 | 6 (+1 confirmation step, +1 adjudication) |
| | input tokens per run | 5,126 | 8,932 (+74%: the outcome and blocked_reason Choices every step) |
| | decision confidence (median) | 0.96 | 0.96 |
| | Jev request, warm | 285 ms | 307 ms |
| | browser per action | 151 ms | 146 ms |
| `smoke-login-badpw` | result | never_violated 2/5, low_confidence 3/5 | `bad_credentials` (pass, negative test) 5/5, confirmed, 3/3 assertions |
| | first sighting of the message | step 4–6 or never (threshold straddled) | step 4 in 5/5 runs (the first step it is on screen) |
| | wall-clock | 6,439 ms | 6,062 ms (−6%) |
| | Jev requests | 6 | 6 |
| | input tokens per run | 8,564 | 9,774 |
| | decision confidence (median) | 0.41 | 0.93 |

Acceptance (spec §5.8): `smoke-login-badpw` returns `bad_credentials` at the first step the message is
visible, no hovering under a threshold ✓ (5/5; the same message read 0.73–0.84 as a lone `never` Noul and
ended 3 of 5 before-runs `low_confidence`); `smoke-login` returns `logged_in`, confirmed, all assertions ok
✓ (5/5); old-style specs unchanged in status ✓ (the selftest's `done_when` / `never` spec still ends
`passed` and, on the error page, in the synthesized `never_error_visible` outcome with exit 1); selftest OK ✓.

The price is written down rather than hidden: the pass path costs one more step (the settle-and-recheck
that used to apply only to Jev's DONE now applies to every pass sighting, +`settle_ms` and one request)
and one adjudication request, and every request carries the outcome Choice and the blocked_reason Choice,
which is where the 74% more input tokens go. On the demo login that is +1.2 s per passing run. What it
buys: the run comes back as one declared outcome with the page's own line as evidence, the negative test
is decided on the first step its message appears, and the hesitant post-error steps (0.04–0.12 operation
confidence, three refused WAITs) are gone.

## Track 3 (2026-09-22): hands-off suite

`scripts/run_suite.py specs/smoke-login.json specs/smoke-login-badpw.json --repeat 5 --workers 4` with the
runner at commit `185a10f` (the runner of Track 2) and `run_suite.py` itself still uncommitted in the working
tree (it landed in `8780958`; the suite ran from the checkout, not from an export, which is how the file got
its commit): `2026-09-22-track3-suite.json` / `.md` are the `results.json` / `results.md` it wrote.

| | |
|---|---|
| wall-clock for 2 specs × 5 repeats, 4 workers | 18.6 s (acceptance: < 60 s ✓) |
| `smoke-login` | `logged_in` (pass) 5/5, agreement 100%, first sighting at step 4 in every run, median 6,432 ms |
| `smoke-login-badpw` | `bad_credentials` (pass) 5/5, agreement 100%, first sighting at step 4 in every run, median 6,192 ms |
| suite verdict | ALL PASS, exit 0 |

Agreement and the `flaky` verdict are computed by `run_suite.aggregate_spec`, exercised in the unit tests
with a fake runner whose spec alternates outcomes (agreement 50% → `flaky`), a spec that is always
`undetermined` (suggested verdicts tallied) and a runner that exits 2 (recorded as an error run). The
brief's third acceptance item, re-running the target-question phrasing A/B through the suite tool, was
not done: the temporary env knob that produced `...-ab-phrasing-implicit.json` was removed after the tie,
as the brief required, so there is nothing to switch; re-adding it for one suite run would have cost 20
live runs to re-measure a tie already recorded above.

### Per-item A/B (3 repeats each, both specs)

`2026-09-21-track1-after-all-items.json` is the first after-measurement with every Track 1 item on: it
failed (smoke-login done_unverified 4/5, confidence 0.60; badpw low_confidence 4/5, 19k tokens per run).
The variants that located the cause:

| variant (file suffix) | smoke-login | conf | badpw | note |
|---|---|---:|---|---|
| `speed-only` (old request shape, new runner) | passed 3/3 | 0.95 | never_violated 2/3 | 6.8 s; labels still offered |
| `structured-no-rules` | passed 3/3 | 0.98 | never_violated 3/3 | 6 requests: Jev clicked the "Username"/"Password" labels first |
| `light-rules` | passed 2/3 | 0.57 | low_confidence 3/3 | rules on `operation` only |
| `full-rules-no-check-rule` | passed 2/3 | 0.50 | low_confidence 3/3 | |
| `rules-noblocked` | passed 3/3 | 0.97 | low_conf 2/3, budget 1/3 | NEXT_ACTION minus the BLOCKED sentences |
| `rules-minimal` | passed 3/3 | 0.56 | never_violated 2/3 | only the two guard sentences |
| `structured-no-rules-nolabels` | passed 3/3 | 0.95 | never_violated 2/3 | **adopted shape**; 4 requests, 5.3 s |
| `speed-only-nolabels` | passed 3/3 | 0.99 | never_violated 3/3 | old request shape with the label fix, 3.7k tokens |
| `phrasing-implicit` | passed 3/3 | 0.94 | never_violated 3/3 | target premise implicit: a tie with named |

Decisions taken from this table: the rules text is not attached by default (`"rules": true` in a spec
turns it on); labels whose control is already in the table are no longer offered as clickables; the
target questions keep the named premise; the structured state and object criteria stay because they meet
the acceptance against the baseline. Note for the reader: on this demo the old one-line request shape
scored marginally higher confidence with a third fewer tokens; the structured shape was kept for the
things the demo cannot exercise (`page_changed` feedback, `current_value` in the criteria).

**Provenance of the A/B files.** The nine `2026-09-22-track1-ab-*.json` files record `git_commit:
f693ebb` and an `env` block of `JEV_STATE` / `JEV_CRITERIA` / `JEV_RULES` / `JEV_CHECK_RULE` /
`JEV_RULES_TEXT` / `JEV_TARGET_PHRASING`. Those knobs were temporary switches in the *uncommitted*
working tree at `f693ebb`, removed before `c3382c2` as the brief required, and the shortened rule
wordings (`light`, `minimal`, `noblocked`, `no-check-rule`) were never committed either: checking out
`f693ebb` and setting the variables reproduces the default behaviour, not the variants. The two
`nolabels` files differ from their twins by the observer change that `c3382c2` committed (labels of
already-offered controls are not clickables), not by the env. What is reproducible from a commit is the
adopted shape: `c3382c2` is what `2026-09-21-track1-after.json` measures. The rows above are kept as the
record of why the decisions were taken, not as re-runnable experiments.

## Review fixes (2026-09-22): the runner at `9c20838`

Both smoke specs, 5 repeats, medians, then the suite, all from a `git archive 9c20838` export in the
scratchpad with `GIT_COMMIT=9c20838` set: the three files record the commit, and every bench run record
carries the headline fields (`first_seen_at_step`, `seen_at_step`, `confirmed`, `assertions_ok` /
`assertions_total`, `evidence_line`, `adjudication_ms`), so nothing in this section comes from a trace
outside the file. `9c20838` applies the fifteen findings of the max-effort review of `1c79f1b..25df84d`
(its commit message lists them). The ones a live run exercises: the `assert` block is evaluated on a
whole-document observation taken after the confirming step (one more observation per passing run), the
adjudication offers visibility-filtered, viewport-first lines, adjudication lines and assertion actuals are
masked, and `smoke-login.json` dropped its `done_when` / `never` because declared outcomes are now the whole
contract. Files: `2026-09-22-review-fixes-bench.json`, `2026-09-22-review-fixes-suite.json` / `.md`.

| spec | measure | Track 2 after (`1aec493`) | review fixes (`9c20838`) |
|---|---|---:|---:|
| `smoke-login` | result | `logged_in` (pass) 5/5, confirmed, 3/3 assertions | `logged_in` (pass) 5/5, confirmed, 3/3 assertions |
| | first sighting → confirming step | 4 → 5 (from the traces) | 4 → 5 in 5/5 (in the file) |
| | evidence line | "You logged into a secure area!" | the same, 5/5 |
| | wall-clock | 6,030 ms | 6,372 ms (+6%) |
| | Jev ms per run / requests | 2,049 / 6 | 2,016 / 6 |
| | adjudication request | not in the file | 319 ms |
| | Jev request, warm | 307 ms | 307 ms |
| | browser per action | 146 ms | 152 ms |
| | input tokens per run | 8,932 | 8,932 |
| | decision confidence (median) | 0.96 | 0.94 |
| `smoke-login-badpw` | result | `bad_credentials` (pass) 5/5, confirmed, 3/3 assertions | the same |
| | first sighting → confirming step | 4 → 5 (from the traces) | 4 → 5 in 5/5 (in the file) |
| | evidence line | "Your password is invalid!" | the same, 5/5 |
| | wall-clock | 6,062 ms | 6,282 ms (+4%) |
| | Jev ms per run / requests | 2,019 / 6 | 1,966 / 6 |
| | adjudication request | not in the file | 291 ms |
| | Jev request, warm | 315.5 ms | 296.5 ms |
| | browser per action | 147 ms | 144 ms |
| | input tokens per run | 9,774 | 9,774 |
| | decision confidence (median) | 0.93 | 0.92 |

**The token counts are identical because the requests are identical.** Jev reports `input_tokens` per
request, and every run of a spec has read the same figure since `1aec493`. The `checks` block is still
asked every step and the outcome Choice already offered only the declared outcomes (`logged_in`,
`bad_credentials`, `server_error`, `none_yet`) at `1aec493`; the synthesized `goal_reached` /
`never_login_error` that `9c20838` removed lived in the runner's outcome table, where the lone `login_error`
Noul raced the Choice at `never_true`, not in the request. Dropping `done_when` / `never` from the spec
therefore changed what can end the run, not what Jev is sent.

**Wall-clock and confidence.** Jev ms and browser ms per run are unchanged; the medians moved by +342 ms
and +220 ms while the runs spread 6,299–7,024 ms against 5,996–6,370 ms before, so the difference is
inside the run-to-run spread plus the one whole-document observation per passing run, and is reported as
measured rather than attributed. The confidence medians (0.94 vs 0.96, 0.92 vs 0.93) are Jev's variance on
identical requests: per run 0.93–0.96 against 0.95–0.96 for `smoke-login`, 0.88–0.92 against 0.88–0.94 for
`smoke-login-badpw`, same model `jev-1.13.0`.

The suite, `run_suite.py specs/smoke-login.json specs/smoke-login-badpw.json --repeat 5 --workers 4`, from
the same export:

| | Track 3 (`185a10f`, from the checkout) | review fixes (`9c20838`, from the export) |
|---|---|---|
| wall-clock, 2 specs × 5 repeats, 4 workers | 18.6 s | 20.8 s (acceptance < 60 s ✓) |
| `smoke-login` | pass 5/5, agreement 100%, first sighting at step 4 in 5/5, median 6,432 ms | pass 5/5, agreement 100%, step 4 in 5/5, median 7,461 ms |
| `smoke-login-badpw` | pass 5/5, agreement 100%, first sighting at step 4 in 5/5, median 6,192 ms | pass 5/5, agreement 100%, step 4 in 5/5, median 6,736 ms |
| suite verdict | ALL PASS | ALL PASS (`all_pass: true`, exit 0) |

Per-run wall under four concurrent browsers is higher than in the bench, as before. The `results.md` cells
now hold the evidence line and a link to each `result.json`; the runner exits 2 for a spec problem or an
unreachable browser and the suite exits 2 when no run produced a result, which no run here did.

## After the real-app session (2026-09-22): the runner at `eecf79e`

Both smoke specs, 5 repeats, medians, then the suite, from a `git archive eecf79e` export in the scratchpad
with `GIT_COMMIT=eecf79e` set (all three files record the commit). `eecf79e` is the last code commit of the
session: the three offline fixes of the review round (`9eab4fe` a run that wrote no trace is an environment
failure, not an outcome; `99b0f0e` suite results carry paths relative to their directory; `99f4a6a` a warning
for a secret too short to mask safely) and the three runner fixes the real-application trial produced
(`d833f95` identical labels are told apart by the card or entry that contains them; `cf24586` a WAIT is not a
repeated action and a budget spent waiting reports `still_loading`; `eecf79e` a BLOCKED right after a no-op
action is suggested from that step's `stuck_reason`). Files: `2026-09-22-real-app-session-bench.json`,
`2026-09-22-real-app-session-suite.json` / `.md`.

| spec | measure | review fixes (`9c20838`) | real-app session (`eecf79e`) |
|---|---|---:|---:|
| `smoke-login` | result | `logged_in` (pass) 5/5, confirmed, 3/3 assertions | the same |
| | first sighting → confirming step | 4 → 5 in 5/5 | 4 → 5 in 5/5 |
| | evidence line | "You logged into a secure area!" 5/5 | the same, 5/5 |
| | wall-clock | 6,372 ms | 6,376 ms |
| | Jev ms per run / requests | 2,016 / 6 | 2,111 / 6 |
| | adjudication request | 319 ms | 279 ms |
| | Jev request, warm | 307 ms | 334.5 ms |
| | browser per action | 152 ms | 145 ms |
| | input tokens per run | 8,932 | 8,932 |
| | decision confidence (median) | 0.94 | 0.96 |
| `smoke-login-badpw` | result | `bad_credentials` (pass) 5/5, confirmed, 3/3 assertions | the same |
| | first sighting → confirming step | 4 → 5 in 5/5 | 4 → 5 in 5/5 |
| | evidence line | "Your password is invalid!" 5/5 | the same, 5/5 |
| | wall-clock | 6,282 ms | 6,359 ms |
| | Jev ms per run / requests | 1,966 / 6 | 1,994 / 6 |
| | adjudication request | 291 ms | 321 ms |
| | Jev request, warm | 296.5 ms | 324.5 ms |
| | browser per action | 144 ms | 147 ms |
| | input tokens per run | 9,774 | 9,774 |
| | decision confidence (median) | 0.92 | 0.92 |

**The smoke specs are unchanged, by construction.** The demo login page has no two controls with the same
label (pass 4 of the observer adds nothing to its table), no step waits on a loader, and both runs end in a
declared outcome, so none of the six fixes touches what Jev is sent or how these runs end: requests and
tokens are identical, the sighting and confirming steps are the same in every run, and the evidence lines
are the same words. The walls (+4 ms, +77 ms) sit inside the run-to-run spread (6,255–6,522 and 6,317–6,646
ms) and the confidence medians (0.96 vs 0.94, 0.92 vs 0.92) are Jev's variance on identical requests.

The suite, `run_suite.py specs/smoke-login.json specs/smoke-login-badpw.json --repeat 5 --workers 4`, from
the same export:

| | review fixes (`9c20838`) | real-app session (`eecf79e`) |
|---|---|---|
| wall-clock, 2 specs × 5 repeats, 4 workers | 20.8 s | 19.4 s (acceptance < 60 s ✓) |
| `smoke-login` | pass 5/5, agreement 100%, step 4 in 5/5, median 7,461 ms | pass 5/5, agreement 100%, step 4 in 5/5, median 6,619 ms |
| `smoke-login-badpw` | pass 5/5, agreement 100%, step 4 in 5/5, median 6,736 ms | pass 5/5, agreement 100%, step 4 in 5/5, median 6,498 ms |
| suite verdict | ALL PASS | ALL PASS (`all_pass: true`, exit 0, no environment failures) |

This is the first suite file written after `99b0f0e`: every path under `specs` is relative to the directory
the file was written in (`smoke-login/01`, `smoke-login/01/trace.json`, `../export-eecf79e/specs/smoke-login.json`),
each run carries its repeat number and its `trace`, each spec its `environment_failures` (empty) and
`reason` (null), and the suite its `environment_failures` map; only the top-level `out_dir` still records the
scratchpad directory the suite was given, as documented. The trial against the public sites is **not** in
this directory: its nine specs are local (`specs/local/`, git-ignored) and its `results.json` files carry the
sites' own text, so the handoff (`docs/superpowers/plans/2026-09-22-handoff-after-real-app.md`) describes it
generically and cites the untracked files under `runs/`.

## A live `flaky` (2026-09-22): the runner at `20833f2`

The computed `flaky` verdict on real runs, for the first time. `run_suite.py specs/local/notify-random.json
--repeat 5 --workers 2` from a `git archive 20833f2` export in the scratchpad with `GIT_COMMIT=20833f2` set
and the spec copied into the export (it is local, see below). Files: `2026-09-22-live-flaky-suite.json` / `.md`.

The page is a practice page whose notification after one click is a random success or a random failure by
design: the trial's `notify-random` spec (`docs/superpowers/plans/2026-09-22-handoff-after-real-app.md`),
whose earlier 6 runs had all succeeded. The spec declares the success as `action_successful` (pass, with a
`text_contains` assertion) and the failure as `action_unsuccessful` (bug, with a note that the page is
random by design).

| | at `20833f2` |
|---|---|
| runs | 5, 2 workers, 16.4 s wall-clock |
| outcomes | `action_successful` 3, `action_unsuccessful` 2 |
| verdicts | pass 3, bug 2 |
| agreement | 60% |
| suite verdict | **flaky** (`all_pass: false`, `flaky: ["notify-random"]`, no environment failure, `suggested_verdicts` empty: every run ended in a declared outcome) |
| evidence lines | "Action successful" 3/3 and "Action unsuccesful, please try again" 2/2: the page's own words, its spelling |
| outcome probability / confidence | 0.91–0.93 / 0.87–0.89 for the pass, 0.98–0.99 / 0.97–0.98 for the bug |
| first sighting → deciding step | 2 → 3 for the pass (the settle-and-recheck confirms it), 2 → 2 for the bug (terminal at first sighting) |
| requests / input tokens per run | 4 / 4,531 for a pass, 3 / 3,205 for a bug (one step and one request fewer) |
| wall-clock (median) | 5,742 ms |
| decision confidence (median) | 0.99 |

What it shows: `flaky` is computed from the disagreement between repeats and never diagnosed, so it reads the
same whether the disagreement comes from the app (here, by design) or from the test; the per-run
`result.json` files keep each run's declared verdict, so a reader sees at once that 2 of 5 runs ended in the
declared bug with the app's own text as evidence, and the `.md` header says NOT ALL PASS and names the spec
whose trace to open. Block G's per-sentence adjudication plays no part: both statements are one sentence.

The spec was untracked when this was measured (its `spec` path points to `specs/local/` inside the export);
since `b3996fa` it is committed unchanged as `specs/examples/notify-random.json`.

## The examples suite (2026-09-22): the ten public-site specs at `b3996fa`

`run_suite.py specs/examples/*.json --repeat 3 --workers 2` from a `git archive b3996fa` export in the scratchpad
with `GIT_COMMIT=b3996fa` set: the first committed run of the real-application trial's specs, promoted to
`specs/examples/` in that commit (block D of the post-trial brief, on Fares's yes), plus `menu-random`, written
this session. Files: `2026-09-22-examples-suite.json` / `.md`. 30 runs, 96.9 s wall-clock on 2 workers,
205 Jev requests and 552,765 input tokens in all, no environment failure. README.md's "Examples" section names the
sites and flows.

| spec | verdict | agreement | outcomes | evidence line | requests / input tokens / wall (medians) | confidence |
|---|---|---:|---|---|---:|---:|
| `shop-checkout` | **pass** | 100% | `order_complete` 3/3 | "Checkout: Complete!" 3/3 | 11 / 28,911 / 7,572 ms | 0.98 |
| `shop-add-second-item` | **pass** | 100% | `bike_light_in_cart` 3/3 | "Sauce Labs Bike Light" 3/3 | 5 / 13,143 / 4,609 ms | 0.875 |
| `shop-checkout-problem-account` | **bug** | 100% | `form_error` 3/3 | "Error: Last Name is required" 3/3 | 9 / 24,641 / 6,355 ms | 0.87 |
| `shop-checkout-error-account` | **undetermined (suggested bug 3/3)** | 100% | `undetermined` 3/3 | none 3/3 | 9 / 26,151 / 6,520 ms | 0.94 |
| `wiki-search` | **pass** | 100% | `article_shown` 3/3 | "Playwright (software)" 3/3 | 5 / 47,872 / 5,614 ms | 0.85 |
| `todo-add-filter` | **pass** | 100% | `active_filtered` 3/3 | "1 item left" 3/3 | 9 / 19,349 / 5,925 ms | 0.915 |
| `load-wait` | **pass** | 100% | `loaded` 3/3 | none 3/3 | 10 / 12,901 / 12,709 ms | 0.94 |
| `notify-random` | **flaky** | 67% | `action_unsuccessful` 2/3, `action_successful` 1/3 | "Action unsuccesful, please try again" 2/3; "Action successful" 1/3 | 3 / 3,205 / 4,619 ms | 0.99 |
| `modal-close` | **pass** | 100% | `modal_closed` 3/3 | none 1/3; "If closed, it will not appear on subsequent page loads." 2/3 | 5 / 5,523 / 5,950 ms | 0.575 |
| `menu-random` | **bug** | 100% | `entry_missing` 3/3 | none 3/3 | 2 / 2,117 / 3,801 ms | none (no action decided) |

What the file shows, against the trial's untracked runs at `cf24586` (3 repeats, handoff
`2026-09-22-handoff-after-real-app.md`):

- **The nine trial specs end as they did**: the same verdict for each, and request and token medians identical
  to the trial's for eight of them (the sites are deterministic: 11 / 28,911, 5 / 13,143, 9 / 24,641, 9 / 26,151,
  5 / 47,872, 10 / 12,901, 5 / 5,523). `todo-add-filter` sends 19,349 input tokens against 19,078: its outcome
  statement is now two sentences and block G's second evidence Choice costs about 270 tokens on that page.
  `notify-random` is **flaky** here (bug 2, pass 1) where the trial's 3 runs had all passed: the page is random
  by design, and this is what the suite says about it (the 5-run measurement above says the same, 3 / 2).
- **`shop-checkout-error-account`** ends `undetermined` 3/3 with `suggested_verdict: bug` 3/3 (BLOCKED right after
  the dead Finish button, `stuck_reason: control_had_no_effect`): the trial's third fix, seen from a clean export.
- **`menu-random`** (new) ends **bug 3/3**: the entry the page drops at random was missing on all three loads (and
  on 3 of 4 observer peeks without Jev), so the page's randomness is skewed and the suite reads a unanimous bug,
  not flaky. As an example it shows an outcome decided on the start page with nothing to click: one step, two
  requests (the step and the adjudication), `decision_confidence` none (no operation was executed), no evidence
  line (the statement is an absence).
- **Evidence lines.** One-sentence statements that name one visible string get their line 3/3 (the product
  name, the form error, the completion heading, the article title, either notification text); the two-sentence
  todo statement is quoted 3/3 ("1 item left", block G; the trial's one-clause statement got a line 1/3);
  absences get none (`menu-random` 3/3; `modal-close` 2/3, and the third quotes a line of the uncovered page that
  is not a statement of the absence); the loader's "The text 'Hello World!' is displayed below the heading" gets
  no line 3/3 (trial 1/3) although `present` is high: Jev declines to equate the sentence with the bare line
  "Hello World!" on a three-line page. A spec author who wants that line quoted writes "The page says 'Hello World!'".
- **Time and tokens.** 97 s for 30 runs on 2 workers; the long encyclopedia page is a quarter of all input tokens
  (47,872 a run, 5 requests) and block F's text-cap lever is measured on it.
