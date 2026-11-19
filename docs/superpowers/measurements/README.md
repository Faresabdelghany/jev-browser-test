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

**The five OrangeHRM specs at `b487e2e`** (`2026-09-24-regression-b487e2e-hrm.md`, 1,178 s on one worker, 13:11–13:31,
the login page 3–6 s by `curl` for most of it and normal for the last two specs): `hrm-login` **pass 3/3** (11–16 s)
and `hrm-pim-add-employee-list` **pass 3/3** (20–27 s, the host normal by then); `hrm-add-employee` 0/3,
`hrm-admin-add-user` pass 1, `low_confidence` 1, one environment failure, `hrm-leave-assign` pass 1, `low_confidence`
2. Every sidebar click of the hour is `SLOW-NAV` (8.5–19.4 s) and Jev's history says it landed; what ended the red runs:

| run | ending | what the trace says |
|---|---|---|
| `hrm-add-employee` 1 | `low_confidence` (BLOCKED, `site_refused_or_error`) | the form stayed under its loading overlay for the three undecided looks after the sidebar typing (17 s of waits); Jev gave up on a page still on its way |
| `hrm-add-employee` 2, 3 | `assert_failed` after two parked looks | covered form (the toast in sight), empty shell, then the record's page under its own overlay with url and heading holding and the two `field_value`s not yet rendered: the bound of two rechecks ran out one look early → `81ce6a2` gives a busy page two more looks |
| `hrm-admin-add-user` 1 | environment failure | `setup[9]`, the seed employee's Save: `Locator.click: Timeout 8000ms`, the button under the form's loader for 8 s |
| `hrm-admin-add-user` 3 | `low_confidence` in 174 s | 26 steps, `SLOW-NAV` 17.2 s, hesitation on a page with eight covered controls |
| `hrm-leave-assign` 1, 3 | `low_confidence` (BLOCKED, `other`) in 162 s / 94 s | 25–27 steps, `SLOW-NAV` 19.4 / 10.6 s in run 1; Jev gave up late in the flow |

The two passes of the slower specs took 178 s (admin) and 131 s (leave), against 33 s and 30 s in the morning's round
3. **Reading:** the seventeen specs say the runner changes are safe; the five OrangeHRM specs in this hour measure the
host, and the three defects the hour exposed in the runner (a landed click reported as failed, a pass confirmed on a
covered or empty page, the recheck bound on a page rendering in stages) are fixed and covered offline. The rerun that
can say "green" is the same command in a normal hour, from a clean export of `81ce6a2` or later:
`GIT_COMMIT=<sha> python scripts/run_suite.py specs/examples/hrm-*.json --repeat 3 --workers 1` after
`curl -o /dev/null -s -w '%{time_total}' https://opensource-demo.orangehrmlive.com/web/index.php/auth/login` reads
under 1.5 s three times.

**The comparison, re-measured** in the same hour (13:12–13:31): `2026-09-24-claude-cost-comparison.md`, section
"Second measurement". Claude's tokens read from the session transcript: Jev path first run 36.7k new tokens (from the
scaffold, six runs in the slow hour, one exit 2 from a scaffold defect fixed in `81ce6a2`), rerun 5.4k, Playwright CLI
path 21.7k; break-even at the first or second rerun, against the reported fourth.

## Blank layers (2026-09-24, afternoon): the hrm suite at `6f9c5be` as the demo recovered, the cause of its reds, `1b69699`

The demo answered its login page in 0.34 s at 13:45 (three probes), so the rerun the previous handoff left open went
out at once from a clean export of `6f9c5be` (`2026-09-24-regression-6f9c5be-hrm.md`, 861 s on one worker): **11/15**.
`hrm-add-employee` 3/3 (19–28 s a run, the slow hour's budget untouched), `hrm-admin-add-user` 3/3 (31–39 s),
`hrm-login` 3/3, `hrm-leave-assign` 2/3, `hrm-pim-add-employee-list` 0/3. The host slowed again during the suite
(login page 5–9 s by 13:51, module pages `SLOW-NAV` 16–20 s), and the four reds are its last four runs.

**The reds read the same way.** Leave run 3 (`low_confidence`, 134 s): Assign clicked at step 16, the form under its
spinner (`COVERED:7`), the dialog not yet open; Jev picked the Leave List tab at 0.73, the runner deferred it once
(`DEFERRED-CLICK:7`, one `settle_ms` of 2.5 s), Jev picked it again at 0.71 on the same page and the once-per-page rule
executed it: the assignment was never confirmed, the Leave List showed no record, and three undecided BLOCKEDs ended the
run. PIM run 1 (`app_error`, "Error Invalid Parameter"): the form under its loader (`COVERED:9`), the first name into
the sidebar filter at 0.77 (deferred once, then executed the same way; the filter then hid the module links), Save, and
Employee List clicked at 0.78 while the saving overlay was still up; the app answered the mid-save navigation with an
error toast, which the spec's `app_error` outcome named a bug. Runs 2 and 3 (`budget_exhausted`, 154 / 131 s): the same
sidebar typing at 0.83 / 0.79, `SLOW-NAV` 16–20 s twice, the 26-step budget spent on waits, and the suggestion row
"mandaa Brooks" at 0.55 with the list still loading. The pictures at the deferred steps show a spinner over the form
and nothing else on it.

**What was wrong in the runner.** The covered-page deferral fired once per page signature and then executed the next
decision whatever it was, on the reasoning that a layer that stays is a dialog and its controls are the controls. Both
halves failed here: the layer was a loader (5–17 s on this host, against one 2.5 s wait), and the executed pick was
never a control of the layer. The two design questions the previous handoff left open (Jev's BLOCKED after three
undecided looks on a covered form; `covered_action_confidence` 0.9 for these specs) are the same fact from two sides.

**`1b69699`.** The observer now counts the covering layer's own controls (`layer_controls`: offered controls inside a
coverer, around it, or within its box: a dialog's Ok over a backdrop, an open list's options, a banner's Accept over a
shade). A layer with none is blank, a loading or saving overlay: a marginal action under it is deferred with the WAIT
backoff (`settle_ms` × 1, 2, 4, 4, 4), `deferral_limit` = `max_low_confidence_steps` + 2 = five times on one page, each
wait ending when the page changes, and only then executed (`deferrals_exhausted`, `DEFER-LIMIT:5`); undecided looks
under it get the same two extra looks the confirmation rechecks get (`low_confidence_limit`). A layer with controls (a
dialog, a dropdown list: `COVERED:n(layer:m)`) defers nothing and does not make the page busy, so a marginal option
pick or Ok goes at once, where before it waited one `settle_ms`. With that distinction the deferral gate could rise:
`covered_action_confidence` 0.9 (was 0.8; the sidebar typing read 0.77–0.90). Offline: unit tests 133, selftest
scenarios 4j (five deferrals then the action), 4j2 (a loader outliving one wait: three deferrals, the third wait ending
as the overlay lifts, then the right field), 4j3 (four undecided looks under a loader, then the field), 4j4 (a marginal
click on a dialog's Ok executed at once), `covered_check` on the fixture's loader (0 layer controls) and dialog (1).

**The seventeen at `1b69699`** (`2026-09-24-regression-1b69699-examples.md`, 307 s on two workers, 14:16–14:21): no
verdict moved against `0e2bc07` / `b487e2e`. Twelve pass 3/3, `forgot-password`, `shop-checkout-error-account` and
`table-sort-due` expected 3/3, `shop-checkout-problem-account` bug 3/3, `dynamic-controls` pass 2/2 (its wording fixed
at `b487e2e`), the two pages that vary by design `menu-random` flaky (all 2 / missing 1) and `notify-random` pass 3/3
this time. Three environment failures, all `Page.goto: Timeout 30000ms` on the-internet.herokuapp.com (`dynamic-controls`,
`login-logout`, `modal-close`, one run each; the other runs of each passed): the host, not the flows. No deferral fired
in the 51 runs (no `DEFERRED-*`, no `DEFER-LIMIT`), and the new count did its one job: `wiki-search` runs 2 and 3 clicked
the suggestion "Playwright (software)" at 0.68 / 0.71 while the open list covered one control, `COVERED:1(layer:2)`, and
went at once, where the same pick used to wait one `settle_ms` (4 requests a run, against 5); `modal-close`'s Close read
`COVERED:1(layer:1)` at 0.98. Request counts otherwise equal (`toolshop-search-cart` 8 against 10, Jev's choice of path).

**The five hrm specs at `1b69699`, in the slow hour** (`2026-09-24-regression-1b69699-hrm-slow.md`, 14:16–14:35, launched
on probes of 2.8–4.4 s, the host recovering during the last spec; 1,121 s on one worker): **13/15**, against 3/15 and
4/15 in the midday hour and 11/15 as the demo recovered at `6f9c5be`. `hrm-admin-add-user` 3/3 (144–182 s a run in this
hour), `hrm-login` 3/3, `hrm-pim-add-employee-list` 3/3 (18–21 s, the host back), `hrm-add-employee` 2/3,
`hrm-leave-assign` 2/3. The deferral did what it was changed to do: every PIM form typed the first name into the sidebar
filter no more (two deferrals, `DEFERRED-TYPE_TEXT:9` twice, then First Name at 0.95), and the Leave flow that used to
leave for the Leave List tab under the spinner waited it out (steps 16–18 undecided or `DEFERRED-CLICK:7` three times,
then the dialog: `COVERED:29(layer:3)`, its Ok clicked at 0.96 at once, then the tab deferred once more under the
saving spinner and taken after the toast). The two reds: `hrm-add-employee` run 3 (`done_unverified`, 99 s) saw its
Save's toast, then the empty shell, then the record page under its loader (`COVERED:15`), and the fourth busy look was
the last the count allowed, 27.5 s of waits at `settle_ms` 2500, one look before the fields rendered: fixed at `6deea29`
below. `hrm-leave-assign` run 1 (`low_confidence`, 162 s): the flow reached the Leave List with the assignment saved,
typed the employee name into the filter, and while the suggestion list still showed the "Searching...." placeholder
(the WAIT before it had ended on that row appearing) Jev clicked Search at 0.70 instead of waiting for the suggestion,
against the notes; the unchosen name did not filter, and four undecided steps on the result ended the run. The runner
executed a decision above `min_confidence`; the notes name the placeholder; in a normal hour the suggestion arrives
within a second (runs 2 and 3 passed in 68 and 34 s as the host recovered).

**`6deea29`.** A confirmation look on a busy page (a blank layer over controls, an empty document) may park again past
the count bound for as long as the confirmation's waits are under `navigation_timeout_ms` (`can_recheck`,
`pending.waited_ms`, `step.recheck_waited_ms`; the wait clipped to what is left): a page on its way may take as long as
a page may take to arrive here, 45 s in the hrm specs. Selftest 4o2 (the staged record page at three times its delays,
`settle_ms` 300, `navigation_timeout_ms` 15 s: the looks go past four and the pass is confirmed on the record); unit
tests 134.

**The comparison, repeated in the normal hour** (14:45–14:48, right after the `6deea29` suite): `2026-09-24-claude-cost-comparison.md`,
section "Third measurement". Jev path rerun 8.1k new Claude tokens (both scaffold specs green at once, 7 s and 41 s of
browser time), Playwright CLI path 15.0k (six turns, 88 s); break-even at the fourth run against the second section's
first run, between the slow hour's first-rerun figure and the original report's fourth.

**The five hrm specs at `6deea29`, in a normal hour** (`2026-09-24-regression-6deea29-hrm.md`, 14:35–14:42, launched on
probes of 0.5–0.7 s; 420 s on one worker): **12/15**. `hrm-add-employee` 3/3 (16–17 s), `hrm-login` 3/3,
`hrm-pim-add-employee-list` 3/3 (21–69 s), `hrm-admin-add-user` 1/3, `hrm-leave-assign` 2/3. Seventeen deferrals in
the suite, none exhausted; two confirmation rechecks, none past the first. The three reds are not the host's:

- `hrm-admin-add-user` runs 2 and 3 (`low_confidence`, 39 / 42 s): the user was saved (the toast, the System Users list
  at 0.95) and its row was not on the page: the demo's user table now holds 56–57 rows, fifty a page, after a day of
  runs adding one each, and the goal's "only if that row is not in the table, filter by the username" left Jev
  undecided between DONE and the filter (0.3–0.57, four looks). Run 1 found the row on the page. A test issue: the
  goal now filters by the username unconditionally and says so about the page size (the spec at `b740501`).
- `hrm-leave-assign` run 2 (`low_confidence`, 57 s): the same step as the slow hour's run 1, the employee name typed
  into the Leave List filter and Search clicked at 0.66 while the list still read "Searching...." (the suggestion took
  longer than the WAIT before it, which had ended on the placeholder row appearing); the unchosen name filtered
  nothing. Runs 1 and 3 waited (0.61 and an undecided 0.50), chose the suggestion and passed.

**The loading placeholder** (`b740501`). An autocomplete row that only says the suggestions are loading
('Searching....', 'Loading...', `LOADING_OPTION` in the observer) is not offered and is counted (`loading_options`, in
the fingerprint too), the settle's options wait does not take it for the suggestions, and `page_loading` treats it as
it treats a blank layer: a marginal action while it shows is deferred (`DEFERRED-<OP>:loading`) until the page changes,
undecided looks get the two extra looks. Selftest 4j5 (a server-side autocomplete: Go at 0.7 over the placeholder is
deferred twice, the suggestion is then chosen, Go clicked, the page says the result) and `settle_check`'s placeholder
case; unit tests 135.

**The five hrm specs at `0ce1c20`, in a normal hour** (`2026-09-24-regression-0ce1c20-hrm.md`, 14:53–15:06, login page
0.6–1.0 s at launch, 0.4–0.6 s during; 494 s on one worker): **ALL PASS, thirteen flows of thirteen**, with two setup
failures that are the host's, not outcomes (`hrm-add-employee` run 2: the scripted login's `wait_for **/dashboard/**`
timed out at 40 s; `hrm-leave-assign` run 2: the seed employee's Save navigation, 45 s): `hrm-add-employee` 2/2 (30–60 s),
`hrm-admin-add-user` 3/3 (29–66 s, the filter step now unconditional), `hrm-leave-assign` 2/2 (31–63 s), `hrm-login` 3/3
(6 s), `hrm-pim-add-employee-list` 3/3 (20 s). Thirteen deferrals, eleven steps with a 'Searching....' row counted and
not offered (`LOADING:n`), six confirmation rechecks, none exhausted. Against the day: 3/15 in the midday slow hour at
`9edd768`, 11/15 as the demo recovered at `6f9c5be`, 13/15 in a slow hour at `1b69699`, 12/15 at `6deea29`, 13/13 here.

## Skill eval iteration 3 and the observer changes (2026-09-24, late afternoon): `d30a966` → `b92b24f` → `152a7f5`

Three new skill-eval prompts (ids 3–5 in `evals/evals.json`, with-skill arm only, one run each from a clean export of
`d30a966`; workspace `~/Downloads/jev-browser-test-workspace/iteration-3/`, `benchmark.json`, `review.html`): the
close-the-loop path on a local sign-up page with a planted inverted e-mail rule (9/11: red, a one-character fix, the same
spec green in two runs; no check that a malformed e-mail is still rejected after the fix, `secrets` removed on an invented
password), the triage of the `1b69699` slow-hour `done_unverified` (11/11: not a bug, one control run, FLAKY/environment
with both traces), and a Recruitment add-candidate-then-search on the slow demo (10/11 after rewording the two
assertions that assumed a pass, 8/11 as first written: the demo's candidate-name type-ahead answers 'No Records Found'
for a full name, its API matching one name part, shown by a plain-Playwright probe; BUG; three undetermined runs, no
declared ending at the two-revision bound). Mean 143k tokens and 795 s a run (iteration 2: 139k, 729 s on the three
older prompts). The agents' notes became `103c62f` (scaffold `--bug name=`, `--after`, `--comment`; `NO-EFFECT
IN-FLIGHT`; `reason.assertions_at_last_look`; the SKILL.md and troubleshooting text) and `b92b24f` (form controls and
buttons below the first screen offered marked `(below the fold)`, icon-only controls named from their class, layer
controls counted only over the covered region so a fixed top bar above a full-page loader leaves the layer blank, a
wheel fallback for SCROLL_DOWN, the `--slow` preset at 40 steps / 480 s, a `suggestion_not_found` outcome in the two
autocomplete examples).

**The seventeen non-OrangeHRM specs at `b92b24f`** (`2026-09-24-examples-suite-b92b24f-seventeen.*`, 3 repeats, 2
workers, 298 s): ten pass 3/3, three expected 3/3, `shop-checkout-problem-account` bug 3/3, `notify-random` and
`menu-random` flaky by design, three navigation timeouts on the-internet (its slow hour: `add-remove-elements` 2/2 beside
one, `menu-random` 1/1 beside one), and `dynamic-controls` 1 pass, 1 timeout, 1 `low_confidence`: Enable was clicked at
0.54 while the Remove loader still ran, the finished page then showed 'It's enabled!' without 'It's gone!', and the
two-message pass wording read 0.65–0.67 with DONE hovering at 0.53–0.58. Rerun ×3 on one worker
(`2026-09-24-dynamic-controls-b92b24f-rerun.*`): 2 pass (both messages on the finished page, 9 requests, 8–16 s), 1
`low_confidence` in 6.8 s: three undecided looks (WAIT against CLICK Enable) during the Remove loader, on a page the
observer changes do not touch (no layer, no icon, no control below the fold; the element table is the one earlier
suites saw). The loader is text and a bar, not a layer, so the undecided looks get no extra turns: the candidate fix
is to read a visible loading indicator (`role=progressbar`, an id or class saying loading / spinner / progress) as
`page_loading` too. `wiki-search` stays at 4 requests and 34.3k tokens: the below-fold offer excludes links, so a long
article's table did not grow. `toolshop-search-cart` 11 requests (was 10).

**The five OrangeHRM specs at `b92b24f`** (`2026-09-24-examples-suite-b92b24f-hrm.*`, 3 repeats, 1 worker, 492 s, a
normal hour, 0.3–0.5 s a page): `hrm-add-employee` 3/3 (15.0 s, 10 requests, its last name now `Runner${RUN_STAMP}`),
`hrm-login` 3/3 (6.7 s), `hrm-pim-add-employee-list` 3/3 (23.2 s, 22 requests: the new outcome is one more option in
the Choice), and the two seeded specs 0/3 in their setup, all six at the same `wait_for a[href*="/leave/"]` after the
seed: a visitor of the public demo had switched the **Leave module off** (the sidebar listed eleven modules, Leave
missing). Switched back on through Admin > Configuration > Modules (the demo's default; it resets nightly anyway),
`hrm-admin-add-user`'s sentinel changed to its own module's link (`152a7f5`), and the two rerun
(`2026-09-24-examples-suite-152a7f5-hrm-two.*`, 1 worker, 170 s): **`hrm-admin-add-user` 3/3** (26.8 s, 18 requests),
**`hrm-leave-assign` 3/3** (28.5 s, 23 requests). So at `152a7f5` every OrangeHRM flow passes, 15/15 across the two
suites once the environment was put back.

## First live runs of 0.3.0–0.6.0 (2026-11-17): `8847bbb` → `9b43ae7` / `839d2f5` (0.5.1) → `fdbc6ca` / `e805067` (0.6.0)

0.3.0, 0.4.0 and 0.5.0 were merged on offline evidence only; this is their first contact with the live Jev API. The
model is **`jev-1.14.0`** (September's files say `jev-1.13.0`), so a difference from September can be the model's as
well as the runner's or the site's. Every run's `result.json` records the model. Environment of this machine: the
python.org interpreter has no CA bundle (`SSL_CERT_FILE=/etc/ssl/cert.pem` in `.env`), and its DNS blocks
`*.log.optimizely.com`, so every the-internet run carries `REQ-FAILED` flags for that beacon (noise, never in Jev's
state; it does break a spec that asserts `no_failed_requests` there).

**Examples suite at `8847bbb` (= main at 0.5.0)** (`2026-11-17-examples-suite-8847bbb{,-hrm}.*`, 3 repeats; 17 specs on
2 workers in 131 s, the five hrm specs on 1 worker in 366 s, the demo at 0.4–0.6 s a page). Verdicts against September
(`2026-09-24-regression-1b69699-examples`, `-0ce1c20-hrm`), each moved one read from its traces:

| spec | September | 8847bbb | cause | done |
|---|---|---|---|---|
| `dynamic-controls` | pass | undetermined 3/3 (`done_unverified`) | **site**: the redesigned page has one message line; 'It's enabled!' replaces 'It's gone!' (probed with plain Playwright), so the two-message pass can never be true. The flow was identical in all three runs | pass reworded on the finished page, removal asserted by the checkbox's absence and the Add caption (`9b43ae7`) |
| `forgot-password` | expected (server_error) | pass 3/3 | **site**: the demo's mailer works now (`/email_sent`) | `expect` removed |
| `modal-close` | pass, 4 requests | pass, 2 requests, 0 actions | **spec + timing**: the modal shows a moment after load; the first look saw no modal and the assertion confirmed the pass at once | `after: {click: Close}`: 4 requests again |
| `add-remove-elements` | pass, 5 requests | pass, 3 requests | **spec + model**: one Add already leaves one Delete; Jev stopped there | `after: {click: Delete}`: 5 requests again |
| `hrm-leave-assign` | pass | undetermined 3/3 | **spec**: the leave date 2026-14-10 had passed; past leave is Taken, the Scheduled filter finds nothing | 2026-16-12 |
| `hrm-add-employee` | pass 3/3 | 2 pass, 1 `employee_id_taken` | **site**: the declared Id race, with the public demo's other visitors (nothing else of ours on the host) | none |

**Runner regression: none.** The September runner (`28a5506`, `2026-11-17-control-28a5506-modal-addremove.*`) run
today on the two shortcut specs gives the same steps, requests and tokens as 0.5.0. After the spec fixes
(`2026-11-17-fixed-specs-9b43ae7{,-hrm}.*`): forgot-password, modal-close, add-remove 3/3, hrm-leave-assign 3/3,
hrm-add-employee 2/3 (one `low_confidence` on the first field, 0.35–0.47 three times on a loaded form: Jev's reading;
nothing 0.3–0.5 changed is asked of this spec).

**`dynamic-controls` ×5** (`2026-11-17-dynamic-controls-x5-9b43ae7.*`): 5/5. The 0.4.0 loading-indicator rule fired in
every run (`LOADING-IND:1` on each undecided look), one run on three undecided looks in a row, which ended
`low_confidence` before the rule. At `fdbc6ca` one run of three still ended `low_confidence`: the loader finished in the
~0.3 s between the observation and the indicator check (which runs after Jev's answer), the check found nothing, and
the limit fell back to three. Fixed in `e805067` (re-read the page before an undecided streak ends the run); ×5 after
(`2026-11-17-dynamic-controls-x5-e805067.*`): 5/5, the race occurred in two runs (`moved_while_deciding`).

### The A/B protocol (`plans/2026-11-16-ab-protocol-jev-driven.md`)

Arms interleaved by `ab.py`, one at a time per host; hrm specs in a process of their own. Commit `9b43ae7` (runner =
0.5.0) for the 22 examples; `839d2f5` / `16f9176` for the probes.

**Shadow DOM** (`2026-11-17-ab-shadow-{nonhrm,hrm}.*`, ×3): arm A recorded no `shadow_hosts` on any of the 22 specs, and
the two arms' first observations are field-for-field identical on 19 of them; the other three differ symmetrically
(OrangeHRM's dashboard widgets rendering, Wikipedia's appearance panel appearing in some sessions in either arm). No
spec moved in every run; three hrm specs moved in some (the Id race, the first-field reading above, and
`hrm-leave-assign` a01, whose arm A ran on the superseded spec during a branch switch: rerun ×3,
`2026-11-17-ab-shadow-rerun-leave.*`, nothing moved; `modal-close`'s six runs were on its old spec too, rerun
`-shadow-rerun-modal.*`, nothing moved). Where it matters: the Polymer shop (`experiments/jev-driven/
shadow-polymer-shop.json`) passes with it (8 requests; Size select M → L, Add to cart) and stalls without it (an empty
table, `low_confidence`, the hint names the option); on MDN, whose page content sits in web components, a light-DOM
flow (`shadow-mdn-chrome.json`, `-ab-shadow-mdn.*`, ×5) was **0/5 without and 5/5 with**, confidence 0.53 / 0.56, 6 / 5
requests, although the option adds 23 chrome controls there (many unnamed). Cost: 19 → 31 ms an observation on MDN
(121 shadow hosts), nothing measurable on pages without. **Default flipped to on (`74b4a58`).**

**Hover** (`-ab-hover-{nonhrm,hrm}.*`, ×5): HOVER offered on 776 steps (455 non-hrm, 321 hrm), chosen on none (highest probability 0.10); no
spec moved in every run, no median confidence fell by more than 0.02; the some-run moves are the two random specs and
`table-sort-due`'s `low_confidence` / `blocked` (both undetermined, both its expected result; ×10 alone,
`-ab-hover-table-sort-x10.*`: 10/10 vs 9 + 1). Cost: **+14.6% input tokens** (non-hrm) and +15.2% (hrm) for the
`hover_target` question on every step; requests and latency unchanged. The one spec that needs it
(`experiments/jev-driven/hover-menu.json`, ×5, `-ab-hover-menu-16f9176.*`): 5/5 with (HOVER, CLICK, pass; 0.70, 4
requests) and 4/5 without (the menu also opens on a click; 0.50, 5 requests). **Kept opt-in**: safe, not free, and the
benefit is one line away for the specs that need it. Two defects found on the way, both fixed in 0.6.0: 0.5.0's HOVER
did not wait for jQuery UI's 300 ms menu delay (every hover flagged NO-EFFECT; `16f9176`), and the experiment's first
pass statement was true of the start page (the draft's own warning; reworded, with `after`).

**Evidence `"failures"`** (`-ab-evidence-{nonhrm,hrm}.*`, ×3, the two random specs left out): 564 → 505 requests
(**−10.5%**, one per pass), 2.03 M → 1.88 M input tokens (−7.4%), wall-clock 551 / 556 s (the host's noise is larger than
the ~210 ms of Jev time saved per pass). `menu-random` and `notify-random` "moved in every run": each run's outcome
matches what its page showed (four vs five menu entries, success vs failure), and a 12-load probe shows both pages random,
not alternating; the option acts after the outcome is read, so this is chance. The three confidence warnings fall on
steps whose requests are identical in both arms. **Kept `"always"`**: the saving is real, the cost is the quoted line
on every pass, which reports and tickets use.

**Uploads** (`experiments/jev-driven/upload-file.json`): at 0.5.1 Jev chose dropzone's hidden input (`file "file"
(hidden file field)`, sorted first at 0,0) over the form's field (also `file "file"`) at 0.99 → Upload with the field
empty → 500 (`server_error`, the test issue the draft foresaw). Fixed in `8fb6478` (an orphan input is offered only when
the page has no other file field); after: UPLOAD_FILE into the form's field, 'File Uploaded!', 4 requests.

**Frames** (`experiments/jev-driven/frames-stripe-card.json`): the Stripe payments demo's card element is a cross-origin
iframe 323 × 18 px, under 0.4.0's 40 × 20 floor, so `observation.frames` contributed nothing. Fixed in `a8b0fbc`
(0.5.1); after: Jev typed number, expiry and CVC into the frame at 0.75–1.00. The pay step cannot complete there: the
demo's backend answers 500 to every `POST /payment_intents` (its account no longer enables 'wechat'), so the run ends
`budget_exhausted` with Pay NO-EFFECT. An invisible captcha frame there reads as a blank layer (`COVERED:1`, layer 0)
and deferred marginal clicks on Pay five times a page: noted, not changed.

**Examples suite at `fdbc6ca` (0.6.0, shadow DOM on)** (`2026-11-17-examples-suite-fdbc6ca.*`, 17 non-hrm ×3, 1 worker,
261 s): every verdict as expected (the random specs happened to land 3/3 each), `dynamic-controls` 2/3, the race above.

**The five OrangeHRM specs at `e805067` (0.6.0, merged as `b6dc583`)** (`2026-11-17-examples-suite-e805067-hrm.*`, ×3,
1 worker, 414 s): login, leave, pim-list 3/3; add-employee 2/3 (one `low_confidence` after Save, the app's toast 'Error
Invalid Parameter', `site_refused_or_error`: the demo's server) and admin 2/3 (three undecided looks at the Status
dropdown). OrangeHRM pages have no shadow roots, so 0.6.0's default observes them as 0.5 did; the same two stalls
occurred at 0.5.1 today (`hrm-add-employee` over the whole day: 48 passes, 4 `low_confidence`, 1 Id race).

### Skill evals, iteration 4 (`2026-11-17-skill-eval-iteration-4/`; workspace `~/Studio/jev-browser-test-workspace/iteration-4/`)

With-skill arm on ids 0–5 at `839d2f5` (SKILL.md as of 0.5.0/0.5.1), one run each, graded against `evals/evals.json`:
0 ticket-sort-bug 9/10, 1 triage-dead-finish-button 8/10, 2 flaky-notification 8/8, 3 slow-spa 11/11, 4
triage-unverified-save 10/11, 5 fix-loop 10/11. **Ids 0–2: 25/28** (iteration 2: 28/28); **ids 3–5: 31/33**
(iteration 3: 30/33). Eval 1 again with the September skill (`28a5506`, old_skill arm): 8/10, the same verdict
(TEST_ISSUE: the overnight spec lacks the example's `expect`), so its two misses come from the triage rule written
after iteration 2 (`534da71`; this paragraph first named `b14d587`), not from the 0.3.0 rewording; the eval expected
BUG with an expected-red note, and was changed the same afternoon (section "0.7.0" below: 10/10 on both arms). Eval 0's miss
is the published demo password printed in the ticket block (SKILL.md allows it, unchanged since September). Browser
runs per eval 3 / 2 / 15 / 4 / 2 / 3 (eval 2: 5 runs of the check as written, 10 of its replacement, 5 of those wasted
on a `no_failed_requests` assertion against the DNS-blocked beacon). Mean 104k tokens a run.

### Cost of the day

756 runner runs (714 under `runs/`, 42 by the eval agents), **6,344 Jev requests**, 22.9 M input tokens.

## 0.7.0 (2026-11-17, afternoon): `b6dc583` → `45d681b` → `3983b35` → `ff5385e` → `83c61d5` → `554b427`

The four follow-ups Fares chose from the morning's handoff: eval 1's expectation, the date placeholder, naming across
shadow roots, the suggested verdict. `jev-1.14.0` throughout.

### Eval 1: the rule stays, the eval follows it

`evals/evals.json`, id 1: expectation 1 asks for TEST_ISSUE with the documented breakage and the missing `expect`
named; expectation 8 ("rules out a test problem") asks that the report puts the test problem in the spec and not in
the run. Prompt, files and the other eight are unchanged, so iteration 4's two saved reports were **re-graded, not
rerun**: an independent grader agent was given the two reports and the two new texts and nothing else. With-skill
10/10 (was 8/10); old-skill (`28a5506`) 10/10 (was 8/10), both new ones borderline there: the report does not print
the label TEST_ISSUE ("The test is what needs fixing") and was saved condensed. Ids 0–2 are now 27/28. The grading
files and `benchmark.*` in `2026-11-17-skill-eval-iteration-4/` carry the new grades and say what they were.

### Date placeholders (`3983b35`; `2026-11-17-hrm-leave-assign-date-placeholder.md`)

Five runs of `hrm-leave-assign`, 130 requests. With `${DATE+30d+workday:yyyy-dd-mm}`: pass today, and
`low_confidence` with `RUN_DATE=2026-12-17`, because the leave fell on 18 January 2027 and the demo's Leave List
shows the current leave year only. With `${DATE+2d+workday:yyyy-dd-mm}`: pass today twice and pass pinned to 17
December, the day the literal date it replaces (`2026-16-12`) would have gone red. Left over: the last two to four
days of each December. The demo's sixteen holidays and its work week were read through its API (one login, no Jev).

### Naming across shadow roots (`ff5385e`; `2026-11-17-ab-shadow-names-*`)

Offline first, with a Playwright probe of the observer (no Jev): the Polymer shop's list page 17 entries with 7
unnamed → 10 with none; MDN's checkbox page 61 entries with 13 unnamed → 61 with 1 (the code editor, a
contenteditable). Old and new observer, both with shadow DOM on, on the 15 start pages of the example and smoke
specs, element table and assertion oracle: **identical on all 15** (none has a shadow root).

A/B with `ab.py --a-runner`, arm A the runner at `3983b35` (`git archive` into `runs/old-3983b35`), arm B the
working tree that became `ff5385e`, interleaved, the three specs in `experiments/jev-driven/`:

| spec | A | B | decision confidence A / B | requests A / B |
|---|---|---|---:|---:|
| `shadow-mdn-copy` (needs a slot-named button) ×5 | `low_confidence` ×4, pass ×1 | pass ×5 | 0.35 / 0.89 | 5 / 3 |
| `shadow-polymer-shop` ×5 | pass ×5 | pass ×5 | 0.98 / 0.93 | 8 / 8 |
| `shadow-mdn-chrome` ×5 | pass ×5 | pass ×5 | 0.60 / 0.48 | 5 / 5 |
| `shadow-mdn-chrome` ×10 (rerun, the tool's advice for a flagged delta) | pass ×10 | pass ×10 | 0.61 / 0.51 | 5 / 5 |

Reading the two flagged deltas step by step. **MDN table of contents:** the one action, CLICK on the 'Browser
compatibility' link, is 0.99–1.00 in both arms. What fell is the looks after it, where Jev answers DONE below
`min_confidence` and the runner waits for the assertion instead: median 0.60 (0.52–0.75) in A, 0.47 (0.35–0.52) in B
over the ten-run rerun. The ranges barely overlap, so it is the change's doing: with ten buttons now reading `Copy`
and one `Reset`, Jev is less sure there is nothing left to do. No ending, request count or action moved. **Polymer
shop:** the first click's target confidence is 0.97 in A (`link "Men's Outerwear Shop Now"`) and 0.80–0.85 in B
(`link "Men's Outerwear"`): the category's image link was `link ""` and now carries the same name as its Shop Now
link, and Jev splits between two links to the same page. The product click is 1.00 in both, on a table of 9 entries
in place of 30.

MDN's Copy button answers 'Copy failed!' in a headless browser (no clipboard permission): the spec accepts either
caption, as an experiment, and says so. MDN's Log in link, the other slot-named control, leads to a third-party
CAPTCHA page and was not used as a flow.

### The suggested verdict (`45d681b`)

Offline only: unit tests and selftest H reproduce the morning's Polymer probe (`2026-11-17-probes/polymer-off-result.json`:
`low_confidence`, `control_not_on_page`, suggested `bug`) and now read `test_issue` with `reason.hints`.

### Release check at `554b427` and cost

The 22 examples once each, 1 worker (`2026-11-17-examples-suite-554b427*`): the 17 non-hrm in 86 s, every spec
ending in its documented result (13 pass; `shop-checkout-problem-account` its `form_error` bug; the two expected-red
specs matched; of the two random specs `menu-random` landed pass and `notify-random` bug); the five OrangeHRM specs
5/5 in 113 s, `hrm-leave-assign` among them with the placeholder. One repeat each: a check that nothing broke, not a
measurement of stability. Offline at the same commit: 191 unit tests, SELFTEST OK.

Cost of the afternoon: **77 runner runs, 589 Jev requests** (5 leave runs 130; 50 A/B runs 265; 22 suite runs 194).
No eval agent ran; one grader agent read two reports.

## 0.8.0 (2026-11-17, evening): replay

Step 1 of the speed work: a passing run saves its path, a later run walks it without asking Jev
(`run_test.py --replay`, `scripts/replay.py`). Baseline for the whole programme: the 0.7.0 release check above, the
22 examples on one worker in 198 s (17 public specs 85.7 s, 5 OrangeHRM specs 112.5 s), 194 requests, about 676k
input tokens.

**Protocol.** `.jev/paths` emptied; one suite with `--replay` to record (`2026-11-17-replay-suite-record-*`); then
`ab.py --b-arg=--replay --repeat 3` (`2026-11-17-replay-ab-*-8d9c8c1`), arm A the spec as it is, arm B with the saved
paths; then one rerun suite with `--replay` (`-suite-rerun-*`), one with `--replay --replay-verify assert`
(`-suite-assert-*`) and one without replay (`-suite-plain-*`). Two streams side by side, the 17 public specs and the
5 OrangeHRM specs, one run at a time in each. Commit `8d9c8c1`, `jev-1.14.0`.

| 22 examples, 3 runs an arm, sums of the specs' medians | without replay | with replay |
|---|---:|---:|
| Jev requests | 190 | 53 |
| input tokens | 674,879 | 171,590 |
| Jev time | 39.1 s | 11.4 s |
| wall-clock | 184.6 s | 150.8 s |

Verdicts: the same in every run of 19 specs. Three moved in some runs, none through a saved path: `menu-random`
(entry_missing once in each arm) and `notify-random` (3 of 3 successful in A, 1 of 3 in B) are random pages, and
`hrm-add-employee` ended `employee_id_taken` once in arm B in a run that had no path to walk (the recording run had
ended undetermined, so B1 was Jev's from the first step; the demo's own id collision). On the 16 specs with a path
every replayed run cost one request, the deciding look.

| per spec, medians | requests | input tokens | wall |
|---|---:|---:|---:|
| `shop-checkout` | 10 → 1 | 24,991 → 2,101 | 5.2 → 3.5 s |
| `web-form-submit` | 9 → 1 | 23,844 → 1,506 | 4.9 → 2.6 s |
| `todo-add-filter` | 8 → 1 | 15,169 → 2,384 | 4.0 → 2.5 s |
| `toolshop-search-cart` | 11 → 1 | 46,217 → 5,266 | 8.8 → 5.6 s |
| `load-wait` (a 5 s loader) | 7 → 1 | 8,147 → 1,114 | 8.1 → 7.5 s |
| `hrm-leave-assign` | 23 → 1 | 133,164 → 8,581 | 27.9 → 21.4 s |
| `hrm-admin-add-user` | 21 → 1 | 110,191 → 10,597 | 30.2 → 23.7 s |
| `hrm-login` | 5 → 1 | 12,010 → 3,672 | 5.9 → 5.3 s |

| the 22 as two suites on one worker | wall | requests | input tokens |
|---|---:|---:|---:|
| 0.7.0 release check | 198.2 s | 194 | 676k |
| recording (first run with `--replay`) | 84.7 + 97.6 s | 110 + 73 | 267k + 375k |
| rerun, `--replay` | 79.0 + 79.2 = 158.2 s | 39 + 5 | 103k + 38k |
| rerun, `--replay --replay-verify assert` | 67.4 + 75.8 = 143.1 s | 23 + 1 | 60k + 8k |
| without replay, same hour | 83.9 s + (152.1 s) | 110 + 78 | 267k + 418k |

The OrangeHRM suite without replay ran last, in a slow stretch of the demo (one start page that never loaded, two
flows at 40 to 45 s): its 152 s is the hour, not the option, which is why the comparison is the interleaved A/B. In
the rerun, `notify-random` rolled its failure after one saved step, so the suite ran it again without the path
(8.3 s for the two runs; the second passed, the page being random) and listed it under `replay.disagreed_specs`.

What the time is made of after replay, `shop-checkout` (3.2 s inside the runner): launch 0.14 s, the start page
0.60 s, the login in `setup` 0.60 s, eight replayed steps at about 165 ms each (the observation 15 ms, the action,
the settle 105 to 130 ms), the deciding request 0.21 s. On OrangeHRM the saved steps mostly wait for the application
(4 to 7 s a flow, `result.replay.waited_ms`): a Save that takes five seconds takes five seconds.

Two things were changed on the way and are in the numbers above. The first A/B (`-ab-*-6a3cc07`: the same verdicts,
190 → 43 requests, 193 → 161 s) showed saved steps on OrangeHRM waiting two to four seconds, or handing over, for a
filter chip's "×" button and an icon-named button that render a moment earlier or later from run to run, and a final
page recorded under its loading layer being waited for until the budget ran out (`hrm-add-employee` 17.7 → 21.7 s
with replay). The fingerprint now counts only word-named controls outside table rows, and the wait for the ending
ends when the assertions hold.

## 0.9.0 (2026-11-17, evening): one request per form

Step 2: `--batch-fields` (`scripts/policy.py` `build_fill_questions` / `plan_batch`, the batch in `run_test.py`).
First runs only, as asked. `ab.py --b-arg=--batch-fields --repeat 5` on the eight examples whose flow fills more
than one text field (`2026-11-17-batch-ab-public`, `-hrm`), step 2's branch at `22dfde0`'s code, `jev-1.14.0`.

| spec | ended in (A, B) | requests | input tokens | wall |
|---|---|---:|---:|---:|
| `shop-checkout` | order_complete 5/5, 5/5 | 10 → 8 | 24,991 → 20,744 | 5.6 → 5.1 s |
| `shop-checkout-problem-account` | form_error 5/5, 5/5 | 9 → 7 | 23,457 → 19,232 | 5.3 → 5.4 s |
| `shop-checkout-error-account` | blocked 5/5, 5/5 | 10 → 8 | 26,266 → 21,868 | 6.2 → 5.4 s |
| `web-form-submit` | form_submitted 5/5, 5/5 | 9 → 7 | 23,844 → 20,383 | 5.0 → 4.0 s |
| `login-logout` | logged_out 5/5, 5/5 | 6 → 5 | 9,770 → 8,756 | 5.0 → 4.6 s |
| `hrm-add-employee` | employee_saved 5/5; 3/5, employee_id_taken 1, low_confidence 1 | 12 → 10 | 54,743 → 46,835 | 23.1 → 19.0 s |
| `hrm-pim-add-employee-list` | employee_listed 5/5, 5/5 | 18 → 17 | 102,186 → 103,366 | 20.2 → 19.8 s |
| `hrm-admin-add-user` | user_listed 5/5, 5/5 | 20 → 21 | 108,822 → 118,820 | 29.0 → 31.2 s |
| sum of medians | | 94 → 83 | 374,079 → 360,004 | 99.5 → 94.4 s |

What the batches did (from the B traces): on the checkout form Jev typed First Name and assigned Last Name (0.99)
and Zip/Postal Code (1.0) in the same request, both typed with no request; on the web form Text input, then Textarea
(0.97), with the three other empty fields `leave_empty` at 1.0; on OrangeHRM's Add Employee, First Name then Last
Name (0.80 to 0.99), the sidebar's Search box and Middle Name `leave_empty` at 0.96 to 1.0. On Add User the plan
after the employee type-ahead was Username, Password, Confirm Password, and the batch ended at once ("a layer or a
loading list appeared over the form": the suggestions, which must be clicked first); the second plan typed Password
and ended on Confirm Password ("the page's text changed": the strength line). No batch typed a wrong value.

`hrm-add-employee` moved in some runs, so it was run alone, ten an arm (`-hrm-add-employee-x10`): employee_saved 8,
low_confidence 1, employee_id_taken 1 without the option; employee_saved 9, low_confidence 1 with it. The
low-confidence runs are the first-field decision that has been shaky under `jev-1.14.0` all day (TYPE_TEXT First
Name at 0.33 to 0.42 three times), with no batch planned in them; `employee_id_taken` is the shared demo handing the
same next id to two visitors.

Decision: opt-in. One request per plain extra field is a real gain and a small one (half a second of 5.6 on the
checkout), and on forms that react it costs tokens and saves nothing.

## 0.10.0 (2026-11-17, evening): the network-aware settle

Step 3: `browser.settle: "network"` (`run_test.NetWatch`, `settle`). `ab.py --b-arg=--settle=network --repeat 5`,
all 22 examples, two streams (`2026-11-17-settle-ab-public`, `-hrm`), `jev-1.14.0`.

| | 17 public | 5 OrangeHRM |
|---|---:|---:|
| browser time per action, median (n actions) | 153 → 102 ms (345, 337) | 248.5 → 100 ms (282, 240) |
| browser time per action, mean | 401 → 283 ms | 542 → 681 ms |
| stale decisions, all runs | 6 → 0 | 8 → 0 |
| undecided (low-confidence) steps, all runs | 39 → 28 | 46 → 24 |
| Jev requests, sum of the specs' medians | 111 → 106 | 82 → 67 |
| input tokens, sum of medians | 263,916 → 252,317 | 431,725 → 400,359 |
| wall-clock, sum of medians | 83.6 → 78.5 s | 109.4 → 117.7 s |

Verdicts. Public: 14 specs the same in all ten runs; `menu-random` and `notify-random` vary in both arms;
`toolshop-search-cart` ended `budget_exhausted` once in arm A (6 stale steps there, none in B) and passed 5/5 with
the option, 8.3 → 6.1 s. OrangeHRM: `hrm-admin-add-user` ended `low_confidence` twice in arm A and hit a setup
timeout once in arm B (`wait_for` the saved employee's page, 45 s: the demo); the other four the same.

Reading it. The 0.7.0 baseline's "260 ms and 560 ms per browser step" are means (288 and 433 ms per action, 319 and
598 ms per step in the release-check files). A mean is mostly the steps that wait for the application, and those are
not shortened: on OrangeHRM a click that loads a module takes 0.8 to 1.3 s with or without the option, and the
steps that used to be Jev's WAITs (4 to 9 a run) are now inside the settle of the click before them (2 to 3.6 a
run left). So the per-action mean rose while the number of steps and requests fell, and the wall-clock is where it
was. The median, which is the typing step, fell from 249 to 100 ms.

The shortcut that was dropped (`-settled-wait-dropped`): an undecided step asked Jev again after 300 ms when no
request was in flight. Public: nothing moved (81.4 → 75.9 s, per action 153 → 103 ms, the same verdicts).
OrangeHRM: `hrm-add-employee` low_confidence 1/5 → 3/5, wall-clock 124.7 → 125.4 s. Reverted before the pull
request.

Decision: opt-in. Fewer requests, no stale decisions, 6% less wall-clock on fast pages; none on the slow one, which
was the target.

## 0.11.0 (2026-11-17, evening): log in once, keep the cache

Step 4: saved sessions for specs that share a `login`, and an HTTP cache that outlives the run
(`scripts/session.py`). `ab.py --repeat 3`, arm B with `--reuse-sessions` (its own empty session directory, so B1
logs in and saves, B2 and B3 reuse) or with `--http-cache` (its own empty cache). Files `2026-11-17-step4-*`.

**Sessions** (the medians of arm B are over the runs that reused a session).

| before the first step, ms | page load | login | setup | wall-clock |
|---|---:|---:|---:|---:|
| 4 OrangeHRM specs, first version (`s4-sessions-hrm`) | 8,298 → 10,939 | 10,846 → 0 | 17,525 → 16,552 | 117.2 → 101.2 s |
| 4 OrangeHRM specs, direct `goto` (`s4b-sessions-hrm`) | 8,608 → 9,149 | 11,061 → 0 | 14,038 → 12,799 | 100.1 → 95.6 s |
| 4 shop specs (`s4-sessions-public`) | 2,374 → 2,886 | 2,296 → 0 | 0 | 18.3 → 17.4 s |

The first version opened the page the login had ended on, the dashboard, which is the heaviest page of the demo
(2.5 s), only to check the session, and two of the four specs then left it at once for the page their setup names:
the page-load column grew by 2.6 s. The check now runs on that page when `setup` begins with a `goto` (second row:
+0.5 s). `shop-add-second-item` reused, on its first B run, the session `shop-checkout` had saved a minute earlier:
the same login on the same site.

**HTTP cache.**

| | page loads | wall-clock, sum of medians |
|---|---:|---:|
| 17 public specs (`s4-cache-public`) | 19,016 → 7,701 ms | 82.7 → 69.5 s |
| ... the-internet, per load | 1,405 to 1,546 → 622 to 657 ms | |
| ... saucedemo, per load | 612 to 846 → 128 to 162 ms | |
| 5 OrangeHRM specs (`s4-cache-hrm`) | 10,319 → 4,547 ms | 111.9 → 108.2 s |

Verdicts. Public: the same in every run except `menu-random` and `notify-random`. OrangeHRM: over the three A/Bs
(54 runs) the flows that finished ended the same; `employee_id_taken` ended three runs, all in arm B
(`hrm-add-employee` and `hrm-pim-add-employee-list` with the cache, `hrm-pim-add-employee-list` with a session), and
`low_confidence` on `hrm-add-employee`'s first field one run in each arm. In the day's other A/Bs
`employee_id_taken` fell in arm A as well (the form-batch ×10, the settle re-measurement). No mechanism connects a
cookie file or a disk cache to the id the demo pre-fills, but three against none is recorded here as it fell.

Decision: both opt-in for a single run; sessions on in the rerun command of step 6.

## 0.12.0 (2026-11-17, evening): parallel runs with a limit per host

Step 5: `run_suite.py --per-host`, `--host-limit`, a spec's `host_limit`, and the scheduler (`run_pool`). The 22
examples once each, nothing else on; files `2026-11-17-step5-*`.

| | wall-clock | per-host peak |
|---|---:|---|
| 0.7.0 at its safe setting: 17 public on `--workers 2` (`before-public`), then 5 OrangeHRM on `--workers 1` (`before-hrm`) | 38.9 + 96.5 = 135.4 s | 2; 1 |
| one suite, `--workers 8` (`after-1`, `after-2`) | 105.4 s; 121.9 s | the-internet 2, saucedemo 2, OrangeHRM 1, the four single-spec hosts 1 |
| one suite, `--workers 4` (`after-w4`) | 121.0 s | the same |
| the 17 public specs alone, `--workers 6` (`try-public`) | 23.7 s | 2, 2, 1, 1, 1, 1 |

The suite is as long as OrangeHRM's queue: its five specs took 96.5 s alone and 105.4, 121.9 and 121.0 s with the
others beside them (the first 25 s of each suite), in an hour in which single flows there ran between 17 and 50 s.
Eight workers against four changes nothing once every other host has finished, which they have after 25 s.

Not green: `shop-checkout-problem-account` (the documented bug, every run); `toolshop-search-cart` in every suite of
this hour, before and after (the practice site answered "0 products found for 'Pliers'", or left the run blocked on
its search); `notify-random` and `menu-random` once each (random pages); `hrm-leave-assign` once (`low_confidence`
after 50 s) and `hrm-add-employee` once (`low_confidence`, its first field). No run failed for load on a host: the
peaks are the limits.

## 0.13.0 (2026-11-17, night): the rerun command, and the six steps together

Step 6: `scripts/rerun.py`, and replay resuming after a handover. Every file is `2026-11-17-final-*`: `f-*` the
first pass (step 6 before its two replay fixes), `g-*` the second, an hour later, on the final code; each a
`results.json` / `results.md` and the `summary.md` the command printed.

**Protocol.** `.jev` emptied. `rerun.py specs/examples` on one worker (`w1-first`: every spec is Jev's, paths and
sessions are saved), twice more (`w1-rerun-1`, `-2`), twice on eight workers (`w8-rerun-*`); then with `--http-cache
--run-arg=--settle=network` once to fill the cache (`w1-all-warm`), once more on one worker (`w1-all-1`) and twice on
eight (`w8-all-*`); then the same with `--replay-verify assert` on eight and on one. No option beyond the command's
defaults in the first group.

| the 22 examples | wall-clock | Jev requests | input tokens | of which specs that walked their path and passed |
|---|---:|---:|---:|---:|
| 0.7.0 release check, one worker | 198.2 s | 194 | 676k | |
| first run through `rerun.py`, one worker | 208.4; 189.0 s | 188; 190 | 642k; 672k | |
| rerun, one worker | 158.6, 136.2; 147.4, 140.1 s | 76, 46; 46, 46 | 290k, 137k; 149k, 147k | 74k to 84k (178k in the run with a handover at step 1) |
| rerun, eight workers | 73.0, 71.3; 115.7, 80.7 s | 45, 44; 44, 49 | 138k to 165k | 73k to 82k |
| every option, one worker | 126.7; 134.3 s | 49; 50 | 162k; 166k | 71k; 75k |
| every option, eight workers | 83.1, 77.5; 69.3, 78.4 s | 52, 43; 49, 49 | 144k to 184k | 75k to 122k |
| every option and `verify assert`, one worker | 111.5; 144.0 s | 28; 30 | 65k; 73k | 0; 8k |
| every option and `verify assert`, eight workers | 62.7; 71.3 s | 30; 26 | 70k; 66k | 5k; 4k |

(first pass; second pass.) The spread is OrangeHRM: its five specs took between 59 and 116 s as a chain, and that
chain is the whole of an eight-worker suite and half of a one-worker one. `g-w8-rerun-1` (115.7 s) had every
OrangeHRM step replayed, one request a spec, and two flows at 37 and 41 s where they take 20: their setup alone ran
9 and 14 s.

Three flows alone, five runs an arm (`final-ab-f-flows`: as 0.7.0 runs them against `--replay --reuse-sessions
--http-cache --settle=network`; `-defaults`: against `--replay --reuse-sessions`), medians:

| | as before | rerun defaults | every option |
|---|---:|---:|---:|
| `login-logout` | 4.6 s, 6 requests, 9,770 tokens | 3.5 s, 1, 2,359 | 2.3 s (page load 1.56 → 0.57 s) |
| `shop-checkout` | 5.2 s, 10 requests, 24,991 tokens | 2.9 s, 1, 2,101 | 2.0 s (page load 0.64 → 0.37 s, login 0.58 → 0, per action 146 → 103 ms) |
| `hrm-pim-add-employee-list` | 20.3 s, 18 requests, 101k tokens | 14.7 s, 1, 7,092 | 13.8 s (login 2.4 → 0, per action 320 → 86 ms) |

First runs with every first-run option (`final-ab-combo-first-public`: `--batch-fields --settle=network
--http-cache`, 17 public specs, 3 an arm): the same verdicts, 110 → 98 requests, 81.5 → 64.3 s; `shop-checkout`
5.2 → 3.9 s and 10 → 8 requests.

**What the two passes found.**
- A saved session that had expired made two runs end `blocked`: saucedemo's cookie lasts ten minutes, the probe of
  the saved session was answered with the login page and an alert, and the alert reached Jev as an announcement on
  the first step after the fresh login (`f-w1-all-warm`: `shop-checkout-problem-account`,
  `shop-checkout-error-account`). Fixed in step 4's branch; the second pass has none.
- A handover at step 1 on OrangeHRM's dashboard (its quick-launch buttons had loaded in one run and not in the
  recording) made a flow of twelve saved steps Jev's from the start (`f-w1-rerun-1`: 76 requests where the other
  reruns have 46). Replay now resumes when Jev's own decision is the saved step.
- `load-wait` handed over at its ending once: the assertions held on the live page, the observation had been taken
  a moment before the loader ended. The page is now observed again once the assertions hold.
- `toolshop-search-cart` was red in part of each pass, with and without its path (the practice site answering "0
  products found" for a product it has): the command ran it again without the path each time and reported the
  second run, "the same without the saved path".

**The skill eval** (`2026-11-17-skill-eval-iteration-5/`): eval 6, "rerun an existing suite", one agent a
configuration. 55.6 s and 73,950 tokens with the skill at v0.7.0 (seven tool calls, five files opened) against 28.7 s
and 68,189 tokens at 0.13.0 (four tool calls, SKILL.md alone). Both answers right.

## 0.13.1 (2026-11-18): an application the examples had not seen

The first run of the skill against an application none of its rules or examples were written on: a private,
server-rendered operations app (a component-library UI, lists that take 10 to 32 s to show their records), one
account, read-only flows. The app, its data and the raw runs are the owner's and are **not** in this repository;
what is here is the tally.

**How.** One read-only look at the app with a plain browser script (the eleven pages of its menu, the first rows of
each list), then eleven specs scaffolded with `scaffold.py --slow`: sign in, a rejected sign-in, sign out, open a
record, switch a tab, three list searches, remove a filter, change a dropdown, the global search. Scripted sign-in in
`login` for nine of them. `run_suite.py`, 2 workers, `jev-1.14.0`.

| | 0.13.0, first run (11 x 1) | `fix/first-contact`, corrected specs (11 x 3) |
|---|---:|---:|
| wall-clock, 2 workers | 108.4 s | 262.1 s |
| pass | 6 of 11 | 10 specs 3/3, 1 spec 2/3 |
| BUG that was not one | 1 | 0 |
| undetermined | 4 | 1 run of 33 |
| Jev requests / input tokens (per pass of the 11) | 66 / 205k (10 specs ran) | about 76 / 244k |

**What the five non-passes of the first run were.**

| spec | ended | cause | whose |
|---|---|---|---|
| tab of a list | BUG `no_records` | the list said "Loading records…" in its body and "0 records · No matching records" in its footer for 10 s; the outcome was taken after 8 | the runner (fixed: the outcome is held) |
| change a dropdown | `low_confidence` | the control is `<button role="combobox">`, offered for typing only; Jev answered CLICK at 0.95 with no such target | the runner (fixed) |
| a list search | setup failure | the scripted sign-in filled the server-rendered form before its code had loaded; the app answered "missing email or phone" | the runner's timing (fixed: scripted steps wait for the page's scripts) |
| remove a filter | `assert_failed` | my URL assertion: the list is also the page a sign-in lands on, at another path | the spec |
| global search | `low_confidence` | the search box does nothing (checked by hand: typing and Enter change nothing) | the application |

Two more things the first attempts cost before any of that: `run_suite.py specs` (a folder) ended `[Errno 21] Is a
directory` (fixed), and a workspace without the machine's `SSL_CERT_FILE` ended eleven runs "TypeSafe API
unreachable", each suggested `flaky` (open: it is the environment's, not the page's).

**After the fixes** (three specs corrected: the URL assertion dropped, the dropdown's option named, a bug outcome
for a search that shows nothing): the false BUG is gone (the outcome was held in 3 of 3 runs of that spec and the
list's records were the ending), the dropdown passes 3/3 at 0.95, no sign-in failed in 27 scripted sign-ins (two
waited about 100 ms for the page's scripts, the rest found them in).

**Still wrong, and the two findings that matter.**

1. **A pass by another route.** The global-search spec passes 3/3 although the search box does nothing: Jev types
   the query, sees no results, and reaches the record through the menu. The bug outcome written for it ("the query
   is in the Search field and the page shows no results for it") read 0.33 against `none_yet` 0.54 on the page
   where it was true, below the threshold, and the next step left that page. A goal-driven run takes whatever
   route is open; a spec has no way yet to say "by this control, or it is a bug".
2. **Patience on an undecided page is shorter than a slow list.** The remove-a-filter spec stalled once in three:
   the list took 32 s to load, and five undecided looks on a page with a loading indicator end after about 27 s at
   the `--slow` settings (2.5 s x 1, 2, 4, 4), while `navigation_timeout_ms` is 45 s.

Smaller: a failed setup step does not quote what the page said (the screenshot had "missing email or phone"; the
result had a Playwright timeout); a goal that leaves a choice open ("another period") splits Jev 0.55 / 0.45 between
two equally good options and the run ends undecided (documented in spec-format.md; the runner could say so itself).

**Did the fixes move the 22 examples?** `ab.py --a-runner` (0.13.0 against the branch, interleaved, one at a time,
two streams): 17 public specs x 2 repeats, no ending moved, requests equal, wall-clock within noise. 5 OrangeHRM
specs x 2: four unchanged; `hrm-add-employee` differed in some runs, so it was run alone x 5 more. Over the seven
runs of each arm: **A** `employee_saved` 5, `low_confidence` 1, `employee_id_taken` 1; **B** `employee_saved` 5,
`low_confidence` 1, `employee_id_taken` 1 (the spec's known noise, the same in both arms). In all the branch's
example runs the hold never fired and no scripted step waited 50 ms or more: the fixes took no part in them.

Offline: 244 unit tests, `selftest.py` and `selftest_capabilities.py` (scenario S: a list that loads under a
"No matching records" footer passes, the same list empty after loading ends BUG, an indicator that never ends
holds the outcome no longer than a navigation; a button combobox is clicked open; a sign-in form whose code
arrives 700 ms late is waited for, its 2.5 s analytics script is not).

## 0.14.0 (2026-11-19): `via`, the control under test

Finding 1 of 0.13.1, "a pass by another route". The spec field `via` names the action a pass has to come through; the
runner compares the page before it with the pages after it, in code, and a run that goes on another way while nothing
but the control itself has changed ends in the outcome `via_no_effect`. Branch `feat/required-control`, runner at
commit `6975bf9` (the `git_commit` in the result files is the checkout the suites were started from, `main` at
`d4631ae`), `jev-1.14.0`.

**The private application** (the one of 0.13.1; nothing of it is here but the tally). Seven of its eleven specs have
one control under test; each got `via` naming it, and the three search specs' `after` was corrected (see below).
`run_suite.py`, 3 repeats, 2 workers, final code.

| spec | 0.13.1, no `via` (3 runs) | 0.14.0 with `via` (3 runs) | median run | of it, waiting for the page to come to rest |
|---|---|---|---:|---:|
| global search (the box does nothing) | pass 3 | **`via_no_effect` (bug) 3** | 24.8 s -> 55.8 s | 30 to 40 s |
| search a list (three specs) | pass 9 | pass 9 | 17 to 31 s -> 41 to 45 s | 14 to 25 s |
| change a dropdown | pass 3 | pass 3 (one run not judged) | 7.7 s -> 40.4 s | 30 to 34 s |
| switch a tab | pass 3 | pass 3 | 14.2 s -> 38.9 s | 33 to 34 s |
| remove a filter | pass 2, `low_confidence` 1 | pass 3 | 33.6 s -> 39.2 s | 3 to 31 s |

On the dead search the ending came two ways: twice Jev chose the menu link (0.5 or more) and the run ended on that
decision; once it stayed undecided three times on the unchanged page (0.36, 0.35, 0.46 for the same link) and the
run ended there. `waited_ms` 18.6 to 18.7 s: 10 s of patience (`settle_ms` 2500 x 4), then the looks.

The wait is the application's: after sign-in its start page makes 63 API requests over about 34 s, 38 of them only
after the previous one has finished, 46.6 s of request time in all (measured with a plain browser script, twice).
The page is usable long before; a change on it is attributable only after. Without the wait the first probe of the
design would have counted the list arriving as the search box answering.

**The examples: does a declared `via` change an ending?** `experiments/via-014/make_variants.py` writes a `-via`
variant of 15 examples (the control each flow goes through) and of the error account; examples and variants ran in
one suite each (public: 2 workers; OrangeHRM: 1), 3 repeats. Slim results: `experiments/via-014/*-final.json`;
`tab.py` prints the comparison.

| | without `via` | with `via` |
|---|---|---|
| 13 public examples x 3 | 37 pass, 2 `action_unsuccessful` (notify-random, random by design) | 37 pass, 2 `action_unsuccessful` |
| 2 OrangeHRM examples x 3 | 6 pass | 6 pass |
| requests, median per run | 3 to 11 public, 6 and 19 OrangeHRM | 3 to 11, 6 and 24 |
| median run | 3.0 to 9.4 s public | 3.3 to 9.3 s |
| `shop-checkout-error-account` (Finish does nothing) x 3 | the example: undetermined, `blocked`, suggested `bug` | `via_no_effect` (bug) 3 of 3 |

In the 45 runs of a working control the page was seen to answer it 42 times (`VIA-ANSWERED`, usually within 30 ms);
3 were not judged (modal-close: the Close control sits in a dialog whose layer reads as blank). 10 steps waited for a
page at rest (`VIA-WAIT`).

**A bug of this change, found by the first measurement** (`*-before-fix.json`). The wait for a page at rest was also
triggered by a blank layer, which is read off an observation and which the wait's own polling cannot see: on
modal-close the wait returned at once, Jev decided again, the layer was still there, and the run spent its eight steps
that way: `budget_exhausted` 3 of 3, where the example passes 3 of 3. Fixed: only requests in flight and loading
indicators trigger the wait, three times at most; a control used under a blank layer is not judged. In that first
measurement the other twelve public pairs and both OrangeHRM pairs already ended alike (one baseline run of
toolshop-search-cart was undetermined; none of its variant's).

**A mistake in the 0.13.1 specs, found on the way.** Their bug outcomes carried `after: {"type": <the query>}`.
`after` matches the label of the control typed into, never the text, so "the list still shows the other record"
could not have fired in any of those runs. `spec.py` now warns when `after.type` / `via.type` is a `data` value.

**What `via` does not do.** A control that answers wrongly has changed the page (a worded bug outcome's job). A
control whose whole effect is outside the element table and the text (a canvas) would read as dead; none of the 22
specs measured has one. Naming a field whose text does nothing until a button is clicked would read as dead; the
rubric says what that looks like in `result.via.then`.

Offline: 252 unit tests (`ViaTests`), `selftest_capabilities.py` scenario T (dead and working search, slow answer,
control skipped, DONE after a dead control, a clicked control, a page still fetching, a page that never comes to
rest), `selftest.py`.
