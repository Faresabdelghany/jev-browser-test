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
