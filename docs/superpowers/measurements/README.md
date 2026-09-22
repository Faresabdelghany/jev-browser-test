# Measurements

Every performance number in the README, SKILL.md and `references/` comes from `scripts/bench.py` output
committed here. Files are named `<date>-<track>-<what>.json`; each holds the per-run records and the
medians for one or more specs, plus the git commit the runs were made at.

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
in both specs). Files: `2026-09-22-track2-before.json`, `2026-09-22-track2-after.json`.

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
