# Jev runner versus Playwright CLI on the same two OrangeHRM flows (2026-09-24, 04:04–04:12)

Two flows on OrangeHRM's public demo (Admin / admin123, printed on its login page), driven twice: once by Claude
through the `playwright-cli` skill (Claude reads a page snapshot, picks the next action, repeats), once by Claude
writing a spec for this runner and reading the result (Jev picks every action). The question was the cost to
**Claude**: tokens and wall-clock, first run and reruns. The specs are `specs/compare/orangehrm-login.json` and
`specs/compare/orangehrm-pim-add-and-find.json` (plus `orangehrm-pim-cleanup.json`, the housekeeping detour); they
were written with a fixed last name (`Jevcmp0404`) and carry `${RUN_STAMP}` since.

## What is on disk and re-measurable

The Jev runs (`runs/` of the worktree the comparison ran in; the traces are the record):

| run | ended | Jev requests | Jev input tokens | wall-clock | of which site load + setup | actions | weakest decision | evidence |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `orangehrm-login` 04:06:55 | pass (`dashboard_open`) | 5 | 13,219 | 6.5 s | 2.6 s | 3 | 0.89 | "PIM" |
| `orangehrm-pim-add-and-find` 04:07:11 | pass (`one_record_found`) | 12 | 71,020 | 16.2 s | 5.3 s | 10 | 0.51 | "(1) Record Found" |
| `orangehrm-pim-add-and-find` 04:11:39 (rerun after the cleanup) | pass (`one_record_found`) | 15 | 89,563 | 23.4 s | 5.4 s | 11 | 0.57 | "(1) Record Found" |
| `orangehrm-pim-cleanup` 04:10:16 | undetermined (`done_unverified`) | 11 | 70,933 | 34.3 s | 6.5 s | 7 | 0.62 | none |

The Jev tokens are Jev's, not Claude's: the model in the loop is TypeSafe's, billed per request there. The browser
time of the two flows together is about 30 s a run (6.5 + 16–23 s), of which 8 s is the demo's page loads and the
scripted login.

The Playwright CLI side left its page snapshots in `.playwright-cli/` (ignored by git since this commit): 10 files,
126 KB of accessibility-tree YAML, the first written at 04:04:40 and the last at 04:07:00 local time, so the two flows
took 2 min 20 s of snapshots (the session's own note says 2 min 35 s end to end). Every one of those snapshots was
read by Claude: at roughly four characters a token that is ~31k tokens of page state alone, before Claude's own
reasoning and tool calls.

## What the session reported (not re-measured here)

The session that ran the comparison (its handoff note of 04:18) recorded Claude's token use as:

| path | first run | rerun |
|---|---:|---:|
| Jev runner (read the skill and the spec reference, write three specs by hand, the cleanup detour, read the results) | ~71.6k | ~5.7k (run the existing spec, read `result.json`) |
| Playwright CLI (drive both flows step by step from snapshots) | ~19.3k | ~19.3k (every run is a first run) |

Break-even: (71.6 − 19.3) / (19.3 − 5.7) ≈ 3.8, so **from the fourth rerun on the Jev path is cheaper in Claude
tokens** (the note said "about five"); the same note also carries a figure of 57k tokens for the Playwright CLI path
next to its 2 min 35 s, which this file cannot reconcile with the 19.3k and leaves as recorded. In wall-clock the Jev
path was about five times faster for the flows themselves (~30 s of browser time against 2 min 20–35 s), and the
result came back as a typed verdict with an evidence line rather than as Claude's reading of the last snapshot.

## What the first-run cost was made of, and what changed

Most of the 71.6k was reading the 270-line `SKILL.md` plus `references/spec-format.md`, writing three specs by hand
(each 60–150 lines), and the cleanup detour (a whole run spent deleting the duplicate the second run had created,
because the last name was fixed). The commits of this session attack each part:

- `scripts/scaffold.py` (`c221f4a`): a valid spec from a URL, a goal and the data values, so Claude edits twenty
  lines instead of authoring eighty; `SKILL.md` starts spec writing from it.
- `SKILL.md` lost its troubleshooting table and its suites section to `references/troubleshooting.md` and
  `references/suites.md` (`c221f4a`): 292 lines / 27.5k characters (~6.9k tokens) → 270 lines / 21.5k characters
  (~5.4k tokens), read on every first run; the references are read only when a run misbehaves or a suite is run.
- `${RUN_STAMP}` (`e0a1ba1`): the duplicate that cost the cleanup detour cannot happen again; the name is fresh
  every run and `result.run_stamp` says which.

The next comparison should be run the same way (two flows, both paths, one session) from the scaffold, and its
Claude-token figures recorded from the session's usage report at the time, with the `.playwright-cli/` snapshot sizes
and the `runs/` traces kept beside them as the re-measurable half.

## Second measurement (2026-09-24, 13:12–13:31): both paths in one session, Claude's tokens from the transcript

Run as the first section asked: the same two flows, both paths, one session, the Jev path from the scaffold, and
Claude's tokens read from the session's own transcript (`usage_between.py` sums the API usage of every assistant
message between two timestamps, one record per request). Three windows, their markers under
`2026-09-24-comparison-2/*-start.txt` / `*-end.txt`:

| window | what happened | Claude requests | new tokens (input + cache writes + output) | of which output (thinking) | cache reads | wall-clock |
|---|---|---:|---:|---:|---:|---:|
| J1: Jev path, first run | `scaffold.py` twice, both specs read and edited, one exit 2 (below), the login spec run twice and the PIM spec four times until both passed, every result and two step tables read | 7 | **36,685** | 12,819 (6,452) | 2,376,578 | 11 min 47 s |
| J2: Jev path, rerun | both finished specs run once, both results read, the red one's step table read | 2 | **5,424** | 2,415 (1,696) | 714,410 | 3 min 14 s |
| P: Playwright CLI path | the skill read, both flows driven step by step (fourteen CLI commands, `find` instead of whole snapshots, `run-code` waits), one wrong Save recovered | 9 | **21,694** | 6,642 (2,487) | 3,317,630 | 4 min 10 s |

`new` is what a fresh session would pay in full: the tokens that entered the context for the first time or were
generated. The cache reads are this session's 2.4–3.3M tokens of earlier context re-read on every request, priced at a
tenth; a fresh session would carry a fraction of them, so the `new` column is the comparable figure. Two things sat
outside the windows and belong to the Jev path's first run in a fresh session: the read of `SKILL.md` (~5.4k tokens,
done at the start of this session) and the knowledge of these two flows already in the context (the `hrm-login` and
`hrm-pim-add-employee-list` example specs and their traces had been read in the morning's regression work), which made
the spec edits shorter than a first meeting with the app would.

**Break-even.** With the measured figures, (36.7 − 21.7) / (21.7 − 5.4) ≈ 0.9: **from the first rerun on the Jev path
is cheaper in Claude tokens**; with the `SKILL.md` read added to the first run (≈ 42k), ≈ 1.25, the second rerun. The
first section's reported 71.6k / 5.7k / 19.3k gave 3.8. The rerun and CLI figures agree with the report within a few
thousand tokens; the first-run figure halved, and the section above says what the scaffold and the slimmer skill
removed from it.

**What the windows contained, and the hour they ran in.** The demo was in a slow hour (its login page 3.4–4.7 s by
`curl` during J1, 5.0 s at the start of P, 6.4 s at 13:23; module pages 10–15 s), which cost both paths and the Jev path
more:

- J1's first exit 2 was a scaffold defect, fixed in `81ce6a2`: the scaffold's comment spelled the `${ENV_VAR}` form
  when a key looked like a credential, the loader scans the whole spec for placeholders, and the login spec would not
  load ("missing environment variables: ENV_VAR"). Then the login run ended `blocked` on the demo's empty shell (the
  form not yet rendered; a `setup` `wait_for` on the Username box fixed it, as `hrm-login` has), and passed: 7 Jev
  requests, 37 s. The PIM spec needed four runs: `low_confidence` after Jev typed the first name into the sidebar
  filter at 0.81 (above the deferral gate) and gave up on the form still covered 17 s later; `low_confidence` after it
  clicked a table row ("Kathleen Brooks") while the autocomplete still said "Searching...." and then refused Search
  (a note about the rows and the suggestion list followed); `budget_exhausted` at the 30-step default with the right
  suggestion clicked at step 29 and Search at 30 (budget 40 / 420 s followed); then **pass**, 28 requests, 106.5k Jev
  input tokens, 111 s, "(1) Record Found". Both specs are `specs/compare/scaffold-login.json` and
  `scaffold-pim-add-and-find.json` as they were when they passed; every run's `result.json` is under
  `2026-09-24-comparison-2/`.
- J2: the login rerun passed (7 requests, 41 s); the PIM rerun ended `low_confidence` the second way above (the row
  "mandaa Brooks" at 0.81 / 0.57 while the suggestions were loading). In a normal hour the same flow passes 3/3
  (`hrm-pim-add-employee-list`, round 3 and the end of the `b487e2e` suite, 19–26 s a run); in this hour the
  suggestion list took seconds and a clickable row with a name is the tempting thing on screen. A rerun that is red
  costs its reading, and the window includes it.
- P: the CLI's first `find` on the login page matched nothing (the empty shell; a `run-code` `waitForSelector`
  followed), its click on PIM hit its own 5 s timeout while the navigation completed (the same shape the runner now
  records as `SLOW-NAV`), and its first Save was rejected with "Employee Id already exists": the `hrm-*` suite running
  on the same demo had opened an Add Employee form in the same second (the race `hrm-add-employee` documents), so a
  fresh id was typed and the second Save reached Personal Details. Eight snapshot files, 20 KB, against the first
  section's ten files and 126 KB: `find` returns the matching nodes with three lines of context, and a page that is
  read that way costs a few hundred tokens instead of three thousand.

**Browser time** (the passing runs): the Jev path's login 37–41 s and PIM 111 s in this hour (6.5 s and 16 s in the
first section's normal hour); the CLI path's two flows 4 min 10 s including Claude's turnaround, with one wrong Save.
The Jev path's tokens are Jev's: 12.5k input a login run, 106.5k a PIM run, billed at TypeSafe.

**What to take from it.** The measured first-run cost is half the reported one and the reruns cost what the report
said; the break-even moved from the fourth rerun to the first or second. The hour's slowness is in both paths' wall-clock
and in the Jev path's retries, and a normal-hour repeat (the two `specs/compare/scaffold-*.json` specs, the same three
windows) is the next measurement; it costs the tokens of J2 plus one CLI drive.

## Third measurement (2026-09-24, 14:45–14:48): the normal-hour repeat of J2 and P

The repeat the second section asked for: the demo answering its login page in 0.6–0.8 s, the same two flows, the Jev
path from `specs/compare/scaffold-*.json` as they passed (no first run from the scaffold this time: the specs exist, so
J1 is the second section's figure), the runner at `6deea29`, and Claude's tokens read from this session's transcript
with `usage_between.py`. Both windows fell inside single tool calls, so the markers alone (`2026-09-24-comparison-3/`)
bracket no request; the table assigns requests by what each turn did (the per-request list is in the section below).

| window | what happened | Claude requests | new tokens (input + cache writes + output) | of which output | wall-clock |
|---|---|---:|---:|---:|---:|
| J2: Jev path, rerun | both finished specs run once from the clean export, both results read (the launch turn and the reading turn) | 2 | **8,112** | 1,846 | 49 s (the runs: login 7.3 s, PIM 40.9 s) |
| P: Playwright CLI path | the skill read, both flows driven in six turns (nineteen CLI commands: `find` instead of whole snapshots, `run-code` waits, role locators), one `run-code` retried (a Node-side reference) | 6 | **14,951** | 4,145 | 88 s including Claude's turnaround |

Both Jev runs passed at the first attempt: `scaffold-login` 5 requests, 10.5k Jev input tokens, `dashboard_open`,
evidence "PIM"; `scaffold-pim-add-and-find` 23 requests, 97.4k Jev input tokens, `one_record_found`, evidence "(1)
Record Found" (`cmp-*-rerun-result.json`). The CLI path's five snapshot files came to 40 KB.

**Reading.** In a normal hour the CLI path costs two thirds of what it cost in the slow hour (15.0k against 21.7k: no
wrong Save to recover, no snapshot of a half-loaded page, fewer commands), and the Jev rerun costs a little more than
before (8.1k against 5.4k: the launch turn carried the previous tool result into the cache, ~3k of it; the two reads of
the results are the rest). With the second section's first run, the break-even moves to (36.7 − 15.0) / (15.0 − 8.1) ≈
3.1, **the fourth run of a flow**, or 2.3 with the second section's rerun figure: between the first-rerun break-even of
the slow hour and the fourth of the original report. The wall-clock gap holds: 48 s of browser time on the Jev path
against 88 s of CLI turns, and the Jev path's result is a typed verdict with an evidence line.

Per request, from the transcript (new tokens, output): J2 launch 11:45:30Z 5,781 / 1,221; J2 read (also opening P and
loading the skill) 11:46:28Z 2,331 / 625; P: 11:46:37Z 6,007 / 405 (the skill's ~5k in the cache write), 11:46:50Z
1,758 / 471, 11:47:05Z 1,521 / 751, 11:47:17Z 1,690 / 554, 11:47:36Z 1,742 / 923, 11:47:56Z 2,233 / 1,041 (the close).
