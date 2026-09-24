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
  absences: `menu-random` gets none 3/3, `modal-close` none in 1 of 3 and, in 2 of 3, a line of the uncovered
  page ("If closed, it will not appear on subsequent page loads.") that is not a statement of the absence; the loader's "The text 'Hello World!' is displayed below the heading" gets
  no line 3/3 (trial 1/3) although `present` is high: Jev declines to equate the sentence with the bare line
  "Hello World!" on a three-line page. A spec author who wants that line quoted writes "The page says 'Hello World!'".
- **Time and tokens.** 97 s for 30 runs on 2 workers; the long encyclopedia page is a quarter of all input tokens
  (47,872 a run, 5 requests) and block F's text-cap lever is measured on it.

## Block F (2026-09-22): the token and time levers, `b3996fa` → `1890405`

Five levers from the post-trial brief, on Fares's yes, each committed and then measured from a `git archive`
export of its commit with `GIT_COMMIT` set, `bench.py --repeat 5`: the two smoke specs every time, `load-wait`
for the WAIT backoff, `wiki-search` for the long-page levers. Baseline `2026-09-22-levers-baseline-bench.json`
at `b3996fa` (the examples commit; the runner is block G's `20833f2`, and its smoke numbers are identical to
the real-app session's). Per lever: `2026-09-22-lever-f2-bench.json` (`69a80df`), `2026-09-22-lever-f1-bench.json`
(`4486d53`), `2026-09-22-lever-f3-bench.json` (`bd44433`), `2026-09-22-levers-f4-f5-bench.json` (`1890405`; F4
and F5 measured together because they touch disjoint runs: F4 only runs with consecutive WAITs, so `load-wait`;
F5 only pages with more than 2,000 chars of text, so `wiki-search`; the smoke specs show that both leave them
alone). Landed in the order F2, F1, F3, F4, F5; all five kept.

| lever | what changed | measured on | input tokens per run (medians) | wall-clock | decisions and evidence |
|---|---|---|---|---|---|
| F2 `69a80df` | shorter `blocked_reason` descriptions | smoke | 8,932 → 8,762 and 9,774 → 9,604 (−170 each) | 6.5 → 7.1 s and 6.7 → 7.0 s (browser launch was slow that round, 408 ms against ~155) | same lines 5/5, sighting step 4, confidence 0.95 / 0.91 (was 0.94 / 0.92) |
| F1 `4486d53` | `blocked_reason` asked only in a follow-up on a terminal step and on the final look | smoke | 8,762 → 7,742 and 9,604 → 8,584 (−1,020 each, −11.6%); output tokens 1,587 → 1,207 and 1,741 → 1,353 | 6.6 s and 6.6 s | same lines 5/5, sighting 4, confidence 0.95 / 0.92. The first bench of this commit hit an API stall: single requests of 3–13 s in 4 of 5 wrong-password runs, identical tokens and results, no reconnect (`2026-09-22-lever-f1-bench-stalled.json`, kept as the record); the numbers here are the clean re-run |
| F3 `bd44433` | adjudication lines sent once (criteria point at `state.lines` by id); per-request `usage` in the trace | smoke, wiki | smoke 7,742 → 7,753 and 8,584 → 8,580 (short lines: a pointer is as long as the line); wiki 47,872 → 45,794 (−2,078; the adjudication request is 8,763 of them now) | 6.6 / 6.3 s; wiki 5.7 → 5.9 s | the same line in 15/15 runs; adjudication confidence smoke 0.99 → 0.96–0.98, wiki 0.41–0.49 → 0.43–0.47; `present` unchanged |
| F4 `3f16bb6` | consecutive WAITs on an unchanged page pause settle_ms × 1, 2, 4, 4 | load-wait | 12,901 → 8,059 with 10 → 8 requests (WAITs of 400, 800, 1,600, 1,600 ms replace six of 400; F1 + F2 account for ~1.6k of the drop, the two missing requests for ~2.3k) | **10.3 → 11.5 s (+1.0 s)**: the last 1,600 ms pause overshoots the loader's end | pass 5/5, confidence 0.94 → 0.96, evidence "Hello World!" 5/5 (baseline 1/5: F3's doing, below) |
| F5 `1890405` | default `observation.max_text_chars` 4000 → 2000 | wiki, smoke | wiki 45,794 → 43,990 (−1,804: −418 to −487 on each of the four steps); smoke unchanged (pages under 300 chars) | wiki 5.9 → 5.7 s | same line 5/5, sighting step 3, per-step decision confidence 0.99 / 0.70 as before, adjudication confidence 0.44–0.52 |

Overall, `b3996fa` → `1890405`: `smoke-login` 8,932 → 7,753 input tokens per run (−13%), the wrong-password
spec 9,774 → 8,580 (−12%), the 5 s loader 12,901 → 8,059 (−38%) and 10 → 8 requests, the encyclopedia article
47,872 → 43,990 (−8%); wall-clock inside the run-to-run spread everywhere except the loader (+1.0 s); every
outcome, evidence line and sighting step the same in every run of every bench.

- **F4 is a trade, stated plainly.** Fewer requests, and a `max_steps` budget that now covers a loader about
  2.7× longer, against about one second of overshoot on a 5 s loader. A cap of × 2 would sit on the same curve
  (one request fewer saved, half the overshoot) and was not measured. `browser.settle_ms` sets the base and
  `run_test.WAIT_BACKOFF_MAX` the cap: if time on loader pages matters more than requests, lower the cap.
- **F3 changed one pick, for the better.** The loader statement "The text 'Hello World!' is displayed below the
  heading" got its line in 1 of 5 baseline runs (and 0 of 3 in the examples suite) and in 5 of 5 after F3, at the
  same low confidence (0.41–0.50): with pointer criteria, "no line" seems a less attractive answer than it was
  beside a full second copy of the page. Every other statement's pick is identical before and after.
- **The encyclopedia adjudication is hesitant either way** (confidence 0.41–0.52, `present` 0.41–0.51): its
  statement is one clause with a bare "and" (heading plus first paragraph). Two sentences (block G) would be the
  spec author's remedy; not changed here.
- The F5 commit landed with a unit test and one selftest scenario still written for the old default;
  `e44e359` fixed both (the pipeline that ran the suites had masked their exit codes; the handoff says so).

## The examples suite after block F (2026-09-22): the ten specs at `188e50e`

The same `run_suite.py specs/examples/*.json --repeat 3 --workers 2` from a `git archive 188e50e` export with
`GIT_COMMIT` set (`188e50e` is a docs commit; the runner is `e44e359`, blocks G and F complete), against the run
at `b3996fa` above. Files: `2026-09-22-examples-suite-after-levers.json` / `.md`. 97.4 s wall-clock (was
96.9), 203 Jev requests and 499,916 input tokens in all (were 205 and 552,765: -10%), no environment failure.

| spec | verdict, `b3996fa` → `188e50e` | requests | input tokens per run (medians) | wall (median) | evidence line at `188e50e` |
|---|---|---|---|---|---|
| `shop-checkout` | pass → **pass** | 11 → 11 | 28,911 → 26,523 (-8%) | 7,572 → 7,522 ms | "Checkout: Complete!" 3/3 |
| `shop-add-second-item` | pass → **pass** | 5 → 5 | 13,143 → 12,193 (-7%) | 4,609 → 4,678 ms | "Sauce Labs Bike Light" 3/3 |
| `shop-checkout-problem-account` | bug → **bug** | 9 → 9 | 24,641 → 22,740 (-8%) | 6,355 → 6,209 ms | "Error: Last Name is required" 3/3 |
| `shop-checkout-error-account` | undetermined (suggested bug 3) → **undetermined (suggested bug 3)** | 9 → 10 | 26,151 → 25,660 (-2%) | 6,520 → 6,742 ms | none 3/3 |
| `wiki-search` | pass → **pass** | 5 → 5 | 47,872 → 43,990 (-8%) | 5,614 → 5,715 ms | "Playwright (software)" 3/3 |
| `todo-add-filter` | pass → **pass** | 9 → 9 | 19,349 → 17,469 (-10%) | 5,925 → 5,838 ms | "1 item left" 3/3 |
| `load-wait` | pass → **pass** | 10 → 8 | 12,901 → 8,059 (-38%) | 12,709 → 12,443 ms | "Hello World!" 3/3 |
| `notify-random` | flaky (action_unsuccessful 2, action_successful 1) → **flaky (action_unsuccessful 2, action_successful 1)** | 3 → 3 | 3,205 → 2,692 (-16%) | 4,619 → 4,492 ms | "Action unsuccesful, please try again" 2/3; "Action successful" 1/3 |
| `modal-close` | pass → **pass** | 5 → 5 | 5,523 → 4,572 (-17%) | 5,950 → 5,805 ms | "If closed, it will not appear on subsequent page loads." 3/3 |
| `menu-random` | bug → **flaky (all_entries 1, entry_missing 2)** | 2 → 2 | 2,117 → 1,893 (-11%) | 3,801 → 3,741 ms | none 3/3 |

- **Eight specs read exactly as before**; the two random pages both read `flaky` now: `notify-random` again
  (bug 2, pass 1) and `menu-random` (bug 2, pass 1) whose dropped entry showed on one of three loads this time
  where the first run had none: the page's randomness, and the second page on which the computed verdict has
  been seen live.
- **Every spec spends fewer tokens** than at `b3996fa`, from −2% on the random-menu page to −38% on the loader
  (10 → 8 requests, F4). The blocked shop account costs **one request more** (9 → 10): F1's follow-up on the
  terminal step, which returns the same `blocked_reason` and the same suggested bug 3/3.
- **Evidence lines**: the loader statement now gets "Hello World!" 3/3 (0/3 before; F3, see block F); the modal
  statement, an absence, quotes the uncovered page's own sentence 3/3 (2/3 before), a line that is not a statement
  of the absence; every other pick is as before, including the two-sentence todo statement's "1 item left" 3/3 and
  none for the menu statement.
- **Time**: the suite's wall is the same within a second; with two workers its per-spec medians are noisier than
  the bench's, so the loader's +1.0 s (F4) is read from the bench, not from here.

## Speed levers after the skill eval (2026-09-22): `2956a93` → `a09f89f` → `7b93b47`

Three benches of the same three specs, 5 repeats each, medians, each from a clean export of its commit
(`2026-09-22-speed-before-bench.json`, `2026-09-22-speed-levers-1-bench.json`, `2026-09-22-speed-levers-2-bench.json`).
The site's page load (`navigation_ms`, ~2.0 s) and the browser launch (~0.17 s) are the demo host's and Playwright's;
the last row takes them out to show the runner's own time.

| `smoke-login` (3 actions, passed 5/5 in all three) | `2956a93` before | `a09f89f` levers 1 | `7b93b47` levers 2 |
|---|---:|---:|---:|
| wall-clock per run | 6,384 ms | 6,195 ms | **4,958 ms (−22%)** |
| Jev, all requests | 2,000 ms | 1,658 ms | 1,196 ms |
| first Jev request | 756 ms | 331 ms | 288 ms |
| warm Jev request (pooled) | 303 ms | 317 ms | 294 ms |
| browser work | 1,297 ms | 1,301 ms | 764 ms |
| requests / input tokens | 6 / 7,753 | 5 / 7,456 | 5 / 6,418 (−17%) |
| duration minus site load and launch | 4,066 ms | 3,704 ms | **2,629 ms (−35%)** |

| `smoke-login-badpw` (bad_credentials 5/5) | before | levers 1 | levers 2 |
|---|---:|---:|---:|
| wall-clock per run | 6,536 ms | 6,339 ms | **4,980 ms (−24%)** |
| Jev, all requests / first | 2,082 / 747 ms | 1,637 / 331 ms | 1,185 / 292 ms |
| browser work | 1,274 ms | 1,274 ms | 760 ms |
| requests / input tokens | 6 / 8,580 | 5 / 8,294 | 5 / 6,873 (−20%) |
| duration minus site load and launch | 4,208 ms | 3,340 ms | **2,656 ms (−37%)** |

| `load-wait` (a 5 s loader, "Hello World!" 5/5) | before | levers 1 | levers 2 |
|---|---:|---:|---:|
| wall-clock per run | 11,325 ms | 9,434 ms | **8,850 ms (−22%)** |
| Jev, all requests / first | 2,657 / 760 ms | 2,147 / 287 ms | 1,857 / 306 ms |
| browser work | 5,562 ms | 4,508 ms | 3,974 ms |
| requests / input tokens | 8 / 8,059 | 7 / 7,774 | 7 / 6,949 (−14%) |
| duration minus site load and launch | 9,025 ms | 7,052 ms | **6,483 ms (−28%)** |

- **Levers 1 (`a09f89f`)**: the client's connection is opened in a background thread while the browser launches
  (`JevClient.warm_up`: the first request 756 → 331 ms), the evidence questions ride in the confirmation request
  (6 → 5 requests on a pass), a WAIT ends as soon as the page's fingerprint changes instead of sleeping its whole
  backed-off pause (the loader's browser time 5,562 → 4,508 ms). Wall-clock moved little on the login specs because
  the site's load happened to be slower in that bench (+115 and +619 ms); the last row shows the runner's own gain.
- **Levers 2 (`7b93b47`)**: a pass whose `assert` block already holds on the sighting page is confirmed at once in
  code (`confirm: "assert"`, default) instead of a 400 ms pause, a second observation and another request; the
  evidence line is then asked in its own request, so the request count stays at 5 and the browser work halves
  (1,301 → 764 ms). `final.png` is a copy of the terminal picture. Tokens fall because the confirmation step's
  observation is no longer sent.
- **What did not help, measured**: a probe of 40 identical requests (`scratchpad/probe_latency.py`, not committed)
  put HTTP/2 via httpx at 302 ms against the stdlib HTTP/1.1 keep-alive's 313 ms, and 8 questions at 294 ms
  against 2 questions' 313 ms: the ~300 ms is the API's floor from this machine, and the number of questions per
  request is free, as the docs say. The stdlib client stays; the levers are round trips and waiting.
- Decisions and evidence lines are the same in all fifteen runs of each spec; confidence 0.95–0.96 / 0.92 / 0.96.

## The examples suite after the speed levers (2026-09-22): the ten specs at `0a8727c`

`2026-09-22-examples-suite-after-speed.json` / `.md`: `run_suite.py specs/examples/*.json --repeat 3 --workers 2`
from a clean export of `0a8727c`. Against the previous suite at `188e50e`:

| spec | verdict | requests | input tokens a run | evidence line |
|---|---|---|---|---|
| `shop-checkout` | pass → **pass** | 11 → 10 | 26,523 → 24,392 | "Checkout: Complete!" 3/3 |
| `shop-add-second-item` | pass → **pass** | 5 → 4 | 12,193 → 10,312 | "Sauce Labs Bike Light" 3/3 |
| `shop-checkout-problem-account` | bug → **bug** | 9 → 9 | 22,740 → 22,740 | "Error: Last Name is required" 3/3 |
| `shop-checkout-error-account` | undetermined (suggested bug 3) → **expected 3/3** (the same undetermined/blocked/`control_had_no_effect`, now declared in `expect`) | 10 → 10 | 25,660 → 25,660 | none 3/3 |
| `wiki-search` | pass → **pass** | 5 → 4 | 43,990 → 34,470 (−22%) | "Playwright (software)" 3/3 |
| `todo-add-filter` | pass → **pass** | 9 → 8 | 17,469 → 15,120 | "1 item left" 3/3 |
| `load-wait` | pass → **pass** | 8 → 7 | 8,059 → 6,949 | "Hello World!" 3/3 |
| `notify-random` | flaky (bug 2, pass 1) → **flaky (pass 2, bug 1)** | 3 → 3 | 2,692 → 2,663 | "Action successful" 2/3; "Action unsuccesful, please try again" 1/3 |
| `modal-close` | pass → **pass** | 5 → 4 | 4,572 → 3,506 | "If closed, it will not appear on subsequent page loads." 3/3 |
| `menu-random` | flaky (pass 1, bug 2) → **flaky (pass 1, bug 2)** | 2 → 2 | 1,893 → 1,893 | none 3/3 |

- **Every pass is confirmed by its assertions** on the sighting page (`confirmed_by: assertions` 21/21 pass runs):
  the confirmation step is gone, so six specs need one request fewer (205 → 183 requests in all) and the
  encyclopedia spec, whose confirmation observation carried a 40k-token page, saves 22% of its tokens.
- **`shop-checkout-error-account` reads `expected`**: the same blocked ending as before, now declared in the spec's
  `expect`, so the suite is green on it and would go red if the Finish button started working. A first attempt put
  the explanation of `expect` into the spec's `notes`; Jev read it as a hint about the page and its confidence in
  BLOCKED after the dead click fell from 0.85 to 0.3–0.4 (the run ended `low_confidence` 3/3, `suite-7b93b47` in
  the scratchpad, not kept). The sentence moved to the human-only `comment` field and the ending came back 3/3.
- **`notify-random`** asserts `text_in {"selector": "#flash", "contains": "Action successful"}` instead of a
  page-wide `text_contains` that the page's own paragraph made true on every load (found by the skill eval); the
  two pass runs confirm through it, the failing run quotes the page's own "unsuccesful".
- **Wall-clock is not a measurement in this file**: three eval subagents were starting on the same machine while
  the suite ran (122 s against 94 s for the same suite at `7b93b47` an hour earlier); the request and token
  counts, verdicts, confidence and evidence lines are the comparison.

## More examples (2026-09-24): eighteen specs at `14ecee9`, and the runner defects the eight new ones forced

`2026-09-24-bench-smoke-login.json`: `bench.py specs/smoke-login.json --repeat 5` from a clean export of `14ecee9`.
`2026-09-24-examples-suite-eighteen.json` / `.md`: `run_suite.py specs/examples/*.json --repeat 3 --workers 2` from the
same export (54 runs, 359 Jev requests, 228 s on 2 workers). `2026-09-24-follow-up-hrm-table.json` / `.md`: the two
specs that disagreed with themselves, rerun from a clean export of the commit that fixed their causes (section end).

**The bench, against `7b93b47`** (medians of 5, the same 3 actions and 5 requests):

| | `7b93b47` | `14ecee9` |
|---|---:|---:|
| wall | 4,958 ms | 6,085 ms |
| runner (duration) | 4,801 ms | 5,965 ms |
| Jev, 5 requests | 1,196 ms (239 a request) | 1,494 ms (299 a request) |
| browser work | 764 ms | 765 ms |
| input tokens | 6,418 | 6,446 |

The runner's own browser work is the same to the millisecond and the request and token counts did not move; the
extra second is the API answering 60 ms slower a request tonight and the demo site's page load (2.1 s). None of the
runner changes below touches a run that never hesitates.

**The suite** (verdict, median requests and input tokens a run, the evidence line Jev quoted):

| spec | verdict at `14ecee9` | requests | tokens in | evidence |
|---|---|---:|---:|---|
| `shop-checkout` | pass 3/3 | 10 | 24,455 | "Checkout: Complete!" 3/3 |
| `shop-add-second-item` | pass 3/3 | 4 | 10,333 | "Sauce Labs Bike Light" 3/3 |
| `shop-checkout-problem-account` | bug 3/3 | 9 | 22,796 | "Error: Last Name is required" 3/3 |
| `shop-checkout-error-account` | expected 3/3 | 10 | 25,730 | none (blocked, `control_had_no_effect`, as declared) |
| `wiki-search` | pass 3/3 | 4 | 33,533 | "Playwright (software)" 3/3 |
| `todo-add-filter` | pass 3/3 | 8 | 15,169 | "1 item left" 3/3 |
| `load-wait` | pass 3/3 | 7 | 6,991 | "Hello World!" 3/3 |
| `notify-random` | flaky (pass 2, bug 1) | 3 | 2,677 | "Action successful" 2/3, "Action unsuccesful, please try again" 1/3 |
| `modal-close` | pass 3/3 | 4 | 3,527 | "If closed, it will not appear on subsequent page loads." 2/3 |
| `menu-random` | bug 3/3 (was flaky bug 2 / pass 1) | 2 | 1,900 | none 3/3: the entry the page drops at random was missing every time |
| `web-form-submit` | **pass 3/3** | 8 | 20,484 | "Form submitted" 3/3 |
| `add-remove-elements` | **pass 3/3** | 5 | 5,078 | "Delete" 3/3 |
| `dynamic-controls` | **pass 3/3** | 10 | 13,682 | "It's gone!" 3/3 |
| `forgot-password` | **expected 3/3** (server_error) | 4 | 3,643 | "Internal Server Error" 3/3 |
| `login-logout` | **pass 3/3** | 6 | 8,395 | "You logged out of the secure area!" 3/3 |
| `table-sort-due` | **flaky**: declared result in 2/3 (`low_confidence` 2, `stuck` 1) | 7 | 18,705 | none |
| `hrm-add-employee` | **flaky**: pass 1/3, `done_unverified` 2/3 | 9 | 41,461 | "Jevtest Runner" 1/3 |
| `toolshop-search-cart` | **pass 3/3** | 10 | 39,169 | "Proceed to checkout" 3/3 |

- **Wall-clock is not a measurement in this file**: the-internet.herokuapp.com is a free Heroku app and cold-started
  three times during the suite (23–26 s of `navigation_ms` in a run; `dynamic-controls` median 25 s, one
  `table-sort-due` run 27 s, against 5–9 s warm). The runner reports it as navigation time, never as a verdict.
- **The ten older specs read exactly as at `0a8727c`** (verdicts, requests, evidence), except `menu-random`, whose
  page drops an entry at random and dropped it three times of three tonight.
- **`table-sort-due`** ended `low_confidence` twice and `stuck` once: the footer link "Elemental Selenium" was the only
  clickable thing near the goal, and Jev's confidence in clicking it sat on both sides of `min_confidence` (0.44–0.61);
  once executed, the link changed nothing (it opens a new tab) and three of those made `stuck`. Both endings say the
  same thing (the headers cannot be reached), so the spec's `expect` now names the outcome only, and its `notes` name
  the footer link as not part of the task. Follow-up: 3/3 `low_confidence` matched, 4 requests a run.
- **`hrm-add-employee`** lost two runs to a single look: Jev said DONE while the demo's Save was in flight (`NO-EFFECT`
  on the click, then a saving overlay: `COVERED:9`); the one confirmation look, 2.5 s later, landed on the next
  page's own loading overlay (`COVERED:15`, the employee's name not yet rendered) and read `employee_saved` at
  0.72–0.75. The record existed in every run (`empNumber` 470–472). The runner now looks again while the page keeps
  changing between looks (`recheck_again`, twice at most, `CONFIRM_RECHECKS_MAX`; selftest 4h). It also exposed a race in the app: two forms opened in the
  same second on two workers were both pre-filled with Employee Id 0684 and the second Save was rejected with
  "Employee Id already exists", an ending the spec had no outcome for (`done_unverified`, `validation_error` 0.31).
  It is now the `employee_id_taken` bug outcome, and the spec says to run it on one worker.
- **Follow-up at `9139e22`** (`2026-09-24-follow-up-hrm-table.{json,md}`: both specs × 3 on one worker from a clean
  export): `hrm-add-employee` **pass 3/3**, 10 requests and 47.5k input tokens a run, "Jevtest Runner" 2/3 and
  "Personal Details" 1/3 as the evidence line; `table-sort-due` **expected 3/3** (`low_confidence`, 4 requests a run).
  The repeated confirmation look did not need to fire in these three runs (the 2.5 s pause reached the saved record);
  two of the table runs again carried a 20 s cold start in `navigation_ms`.
- **Four runner defects the new specs found**, all committed with offline scenarios: (1) three undecided steps ended a
  run `low_confidence` in ~2 s while a 5 s loader was visibly running (Jev split WAIT 0.47 / DONE 0.46): undecided
  steps now wait like a chosen WAIT, `settle_ms` × 1, 2, 4, ending when the page changes, and the count restarts when
  the page changes; (2) Jev typed a first name into the sidebar's Search box because the form's fields sat under a
  loading overlay and Search was the only field offered: the observer now counts `covered_controls` and Jev sees the
  count (the same step then read TYPE_TEXT into Search at 0.38 and was refused; the next step typed into First Name
  at 1.00); (3) a Save that navigated during the confirmation look raised "Execution context was destroyed" and the
  run ended `error` / suggested `flaky` for a flow that had saved: the observation is retried on the new document;
  (4) the single confirmation look described above.

## OrangeHRM fixes (2026-09-24, morning): the three new specs, rounds 1–3 at `f06f818`, `989ab2f`, `8fea73d`

`2026-09-24-claude-cost-comparison.md`: the Jev-versus-Playwright-CLI comparison of 04:04–04:12 (its Jev runs and the
Playwright CLI snapshots are the re-measurable half; the Claude-token figures are the session's report).
`2026-09-24-hrm-three-suite-round1.json` / `.md`: `run_suite.py` over `hrm-admin-add-user`, `hrm-leave-assign` and
`hrm-pim-add-employee-list`, `--repeat 3 --workers 1`, from a clean export of `f06f818` (the commit that added the
specs on `${RUN_STAMP}`, after the run stamp, the deferred typing, the toast capture, the `after` option and the
scaffold). `2026-09-24-hrm-three-suite-round2.json` / `.md`: the same from a clean export of `989ab2f`, the observer
fix that round 1 forced, which exposed the next defect. `2026-09-24-hrm-three-suite.json` / `.md`: round 3, from a
clean export of `8fea73d`, the deferral widened to clicks.

| spec | round 1 (`f06f818`) | round 2 (`989ab2f`) | round 3 (`8fea73d`) | requests / run (r1 · r2 · r3) | evidence |
|---|---|---|---|---:|---|
| `hrm-admin-add-user` | **pass 3/3**, 27.4 s median | **pass 3/3**, 26.5 s | **pass 3/3**, 33.3 s | 18 · 18 · 19 | the username (`jev<stamp>`) or the employee name, 3/3 |
| `hrm-leave-assign` | **flaky**: pass 2/3, `low_confidence` 1/3, 28.3 s | **undetermined 3/3** (`low_confidence`), 42.7 s | **pass 3/3**, 29.7 s | 23 · 19 · 22 | "(1) Record Found" on every pass |
| `hrm-pim-add-employee-list` | **pass 3/3**, 19.2 s | **pass 3/3**, 19.2 s | **pass 3/3**, 18.6 s | 17 · 16 · 16 | "(1) Record Found" 3/3 |

- **Every run had its own stamp** (`result.run_stamp`, eight base-36 characters): nine runs, nine distinct usernames /
  last names, no "Already exists", no second record found, no cleanup run.
- **The typing deferral fired live** (PIM run 1, step 3: `TYPE_TEXT` into the sidebar's `Search` at 0.68 with nine
  controls covered, `TYPE-DEFERRED:9`; the wait ended when the overlay lifted and step 4 typed First Name at 0.94).
  In the two other PIM runs the form was already shown when Jev first typed. Before the deferral every PIM run of the
  night typed the first name into the sidebar filter first.
- **Toasts were captured in every run** ("Success Successfully Saved", `live`, tone `success`: the seeded employee's
  save during `setup` lands on step 1, and the Leave assignment's own save 0.35 s before the observation after Ok).
  The Leave pass rested on the table row, not on the toast; the capture is evidence in the trace for now.
- **The one red run** (Leave 2/3) was neither the stamp nor the toast: after Ok the Assign Leave form is shown again,
  emptied, and Jev had to click the Leave List tab; OrangeHRM builds its top-row tabs as an `<li>` with `cursor:
  pointer` around an `<a>` of the same caption, so the observer offered every tab twice (`clickable "Leave List"`,
  `link "Leave List"`) and Jev split its choice 0.57 / 0.25, then hesitated toward re-filling the form, three undecided
  steps on one page. The spec had also said Ok redirects to the Leave List (it does not). `989ab2f` drops a pointer
  wrapper whose only content is one offered control (a click on the control bubbles to it anyway) and corrects the
  spec's account of the page after Ok. In run 1 of the same round Jev clicked the link at 0.62 and passed; the
  duplicate was a coin the runner should not have offered.
- `after: {click: Search}` on `no_records` did not need to fire (the outcome never crossed 0.8 before Search in these
  runs); it is the guard against the night's early firing, kept.
- **Round 2 lost all three Leave runs**, and to the same step: after Assign the form's controls sit under a spinner
  (`COVERED:7`) for a moment before the 'Balance not sufficient' dialog opens; Jev, seeing the form and the goal's next
  clause, clicked the Leave List tab at 0.63 / 0.74 (operation / target) while that request was in flight, the dialog
  never came, and it then hesitated over the two unnamed calendar icons until `low_confidence`. In round 1 the same
  pick was split across the duplicate tab (0.57 / 0.25) and refused, and the wait let the dialog appear: the duplicate
  had been hiding the premature click. `8fea73d` widens the covered-page deferral from typing to any marginal CLICK /
  TYPE_TEXT / SELECT (`thresholds.covered_action_confidence`, flag `DEFERRED-<OP>:n`): that click, at 0.63 with seven
  controls covered, becomes one wait that ends when the dialog opens. The spec's goal now also says to wait for the
  dialog and click nothing else before it.
- **Round 3: all nine runs passed**, 100% agreement on each spec, nine distinct stamps, 243 s of wall-clock on one
  worker (`2026-09-24-hrm-three-suite.md`). The Leave runs clicked Ok at 0.93–0.97 the step the dialog was on screen
  (the goal now names the wait) and needed no deferral; the PIM runs used it five times in nine (`DEFERRED-TYPE_TEXT:9`
  on the sidebar filter in two runs, `DEFERRED-CLICK:9` on the Employee List tab while the Save was in flight in all
  three: the very shape of round 2's Leave failure, caught one step earlier). Requests a run barely moved across the
  rounds (PIM 17 → 16 → 16, Leave 23 → 19 → 22, admin 18 → 18 → 19): a deferral costs one request and saves the
  wandering it prevents.

## Regression suite after the OrangeHRM fixes (2026-09-24, midday): twenty-two specs at `9edd768`, a slow hour, `d42c243`, `0e2bc07`

Today's runner changes (the observer dropping a pointer wrapper around one control, the covered count in the
fingerprint, the deferral of any marginal action on a covered page) touch every spec, and the morning's rounds had
rerun only the three new OrangeHRM specs. This is the full suite: `specs/examples/*.json --repeat 3`, the seventeen
non-`hrm-*` specs on two workers and the five `hrm-*` specs on one worker, each from a clean export
(`2026-09-24-regression-<commit>-{examples,hrm}.{json,md}`).

**At `9edd768`, the seventeen read exactly as at `14ecee9` / `9139e22`** (`2026-09-24-regression-9edd768-examples.md`,
240 s on two workers): twelve pass 3/3 with the same request counts and evidence lines, `forgot-password`,
`shop-checkout-error-account` and `table-sort-due` expected 3/3, `shop-checkout-problem-account` bug 3/3, the two pages
that vary by design computed flaky (`menu-random` entry missing 2 / all 1, `notify-random` success 2 / failure 1), and
one environment failure (`login-logout` run 3: `Page.goto: Timeout 30000ms`, a Heroku cold start; the other two runs
passed). No verdict moved.

**The five OrangeHRM specs went 3/15** (`2026-09-24-regression-9edd768-hrm.md`, 1,254 s on one worker): `hrm-login`
pass 3/3, the four others 0/3, twelve runs `low_confidence` and one `assert_failed`. The demo had entered a slow hour
(its login page 5–7 s to serve by `curl`, against 0.9 s; a module page 9–17 s), and every red run has the same first
step: the sidebar click flagged `ACTION-FAILED` with `TimeoutError: Locator.click: Timeout 8000ms exceeded`, and the
next observation on the page the click asked for. Playwright performs the click ("click action done" in its call
log) and then waits for the navigation it scheduled; on this host that wait, not the element, ran out
`action_timeout_ms`. The history then told Jev the click had failed while the page showed it had worked, and every
later decision of the run read 0.2–0.5 (five to eight `LOW-CONF` steps a run, wall-clock 68–126 s against 19–33 s
in the morning's round 3). The one `assert_failed` (add-employee run 3) confirmed `employee_saved` on the toast
'Successfully Saved' while the saving overlay still covered the form (`COVERED:9`) and the URL was still the form's,
two seconds before the Personal Details page arrived.

**`d42c243`** reads Playwright's account (`navigation_pending`: the marker "waiting for scheduled navigations to
finish"), waits for the page for the rest of `navigation_timeout_ms` and records the click as executed and slow
(`executed.slow_navigation`, flag `SLOW-NAV:<s>`; the same tolerance on a scripted `setup` click), and parks a
confirmation look again when the pass is in sight on a page still covered or changed during the pause but the
assertions do not hold yet (`assertions_can_wait`, flags `RECHECK:n ASSERT-PENDING:n`). Nine unit tests on the real
1.63 call log, selftest 4m (a local site whose module page answers after 1 s) and 4n (a save whose toast comes under
the overlay), both red on the `9edd768` scripts. Rerun in the same hour:

- The seventeen (`2026-09-24-regression-d42c243-examples.md`, 249 s): no failed and no slow action in 51 runs, the same
  verdicts, `login-logout` 3/3 this time, and two runs worth the trace. `dynamic-controls` run 2 (a 28 s cold start)
  never showed "It's gone!" after Remove: the trace's text carries "It's enabled!" alone through steps 10–12, Jev read
  `both_done` at 0.56–0.60 and DONE at 0.36–0.47, and the run ended `low_confidence` (suggested bug): the right hedge
  on a page the app had left half done. `table-sort-due` run 2: Jev clicked the footer link at 0.55 (`NO-EFFECT`, it
  opens a tab) and `not_sorted`, a bug outcome with `requires_action`, then read as the ending against the spec's
  `expect`; the two bug outcomes describe the table after the Due header was clicked and the header is the one
  control Jev cannot see, so they now carry `after: {click: Due}` (`0e2bc07`).
- The five (`2026-09-24-regression-d42c243-hrm-partial.log`; the suite was stopped after seven runs to make room for
  the next commit): every sidebar click is `SLOW-NAV` now (13.3 / 17.2 / 12.4 s on the PIM link) and Jev's history
  says it landed, but `hrm-add-employee` still 0/3 with new endings. Run 2 saw `employee_saved` on the Personal Details
  URL while the document was still empty (no controls, no text, one signature for two looks) and ended `assert_failed`
  on it. Runs 1 and 3 reached the Save's confirmation on the last of their 16 steps (a slow navigation, the deferred
  sidebar typing and two hesitations on the covered form, two waits while the Save was in flight) and ended
  `done_unverified` / `budget_exhausted` with the record saved. `hrm-admin-add-user`: pass in 152 s, and two
  environment failures at `setup[10]`, the seed employee's Save taking more than 45 s to reach its Personal Details
  page; `hrm-leave-assign` run 1 `low_confidence` in 142 s.

**`0e2bc07`**: a busy page is one with covered controls or none at all (`page_busy`), and both confirmation branches
(a pass in sight whose assertions do not hold, a DONE with no pass yet) park again on it, bounded by
`CONFIRM_RECHECKS_MAX` (selftest 4o: the record page arriving as an empty shell first, two parked looks, then the
pass). `hrm-add-employee` gets `max_steps` 24 / `max_seconds` 240 (its comment counts the slow hour's steps), and
`table-sort-due` the `after` above. The reruns at this commit follow below; the five OrangeHRM specs were held until
the demo's login page answered in under 1.5 s again, because a `setup` step that waits 45 s for a Save is the
host's failure, never the flow's.

**The seventeen at `0e2bc07`** (`2026-09-24-regression-0e2bc07-examples.md`, 219 s on two workers; no failed action, no
slow navigation, no recheck in 51 runs): the same twelve pass 3/3, the three expected 3/3 (`table-sort-due` with the
`after`: `low_confidence` 3/3 at 4 requests), `shop-checkout-problem-account` bug 3/3, `menu-random` all 2 / missing 1,
`notify-random` failure 3/3 (its coin), and `dynamic-controls` undetermined 2/3: both runs ended `done_unverified` on
a page that showed both messages and passed every assertion, Jev reading `both_done` at 0.77–0.79 (the third run 0.82,
pass). The two-message wording has always sat at the gate on this page (the row in README "Examples" recorded 0.81 at
`14ecee9`): the text "Wait for it..." stays on the page after each loading bar. The outcome now names the buttons' new
captions with the messages, and the notes say what "Wait for it..." means: 3/3, `both_done` 0.96–0.97, 9 requests
(`runs/suite/dyn-sharpened` of the export; the spec change is in the commit after `0e2bc07`).

| spec | `9edd768` | `d42c243` | `0e2bc07` |
|---|---|---|---|
| twelve flows (`add-remove-elements`, `load-wait`, `login-logout`, `modal-close`, `shop-add-second-item`, `shop-checkout`, `todo-add-filter`, `toolshop-search-cart`, `web-form-submit`, `wiki-search`, and see below) | pass 3/3 (one `login-logout` run a Heroku `Page.goto` timeout) | pass 3/3 | pass 3/3 |
| `dynamic-controls` | pass 3/3 | flaky: pass 2, `low_confidence` 1 (the app never rendered "It's gone!" after a 28 s cold start) | flaky: pass 1, `done_unverified` 2 (`both_done` 0.77–0.79 on the finished page); **3/3 at 0.96–0.97 with the sharpened wording** |
| `forgot-password`, `shop-checkout-error-account` | expected 3/3 | expected 3/3 | expected 3/3 |
| `table-sort-due` | expected 3/3 | flaky: expected 2, `not_sorted` 1 (the footer link at 0.55) | expected 3/3 (`after`) |
| `shop-checkout-problem-account` | bug 3/3 | bug 3/3 | bug 3/3 |
| `menu-random` / `notify-random` (vary by design) | flaky 2/1 · flaky 2/1 | flaky 2/1 · flaky 1/2 | flaky 2/1 · bug 3/3 |
