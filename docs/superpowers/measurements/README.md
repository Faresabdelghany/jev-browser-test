# Measurements

Every performance number in the README, SKILL.md and `references/` comes from `scripts/bench.py` output
committed here. Files are named `<date>-<track>-<what>.json`; each holds the per-run records and the
medians for one or more specs, plus the git commit and the `JEV_*` environment the runs were made with.

## Track 1 (2026-09-21/22): the jev-ultrafast loop

Both smoke specs, 5 repeats, medians. Baseline = commit `e20f461` (before any loop change).

| spec | measure | baseline | after (`c3382c2`) |
|---|---|---:|---:|
| `smoke-login` | outcome | passed 5/5 | passed 5/5 |
| | wall-clock | 8,896 ms | 5,165 ms (−42%) |
| | Jev request, warm | 770 ms | 307 ms |
| | browser per action | 646 ms | 147 ms |
| | decision confidence (median) | 0.94 | 0.95 |
| | input tokens per run | 3,858 | 5,126 |
| `smoke-login-badpw` | outcome | never_violated 5/5 | low_confidence 5/5 (see below) |
| | wall-clock | 11,563 ms | 6,040 ms (−48%) |
| | Jev request, warm | 751 ms | 328 ms |
| | browser per action | 642 ms | 146 ms |

Acceptance (spec §4.11): wall ≥ 40% lower ✓ (both specs); outcomes 5/5 unchanged ✓ for `smoke-login`,
✗ for `smoke-login-badpw`; median decision confidence not lower ✓ (`smoke-login` 0.95 vs 0.94); selftest OK ✓.

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
