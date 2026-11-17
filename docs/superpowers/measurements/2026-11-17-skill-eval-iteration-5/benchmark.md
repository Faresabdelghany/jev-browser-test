# Skill eval iteration 5: rerun an existing suite

Eval 6 (`rerun-existing-suite`), one run a configuration, 2026-11-17. The same prompt, the same eight specs, a work
folder in which the suite had been run once before with the skill version under test.

| | before (skill v0.7.0) | after (skill 0.13.0) |
|---|---:|---:|
| Agent wall-clock | 55.6 s | 28.7 s |
| Agent tokens | 73,950 | 68,189 |
| Tool calls | 7 | 4 |
| Files opened | SKILL.md, references/suites.md, yesterday's results.md and log, today's results.md | SKILL.md |
| The suite run it started | `run_suite.py ... --workers 2`: 17.2 s, 55 Jev requests, 117,897 input tokens | `rerun.py specs/`: 7.1 s, 17 Jev requests, 39,010 input tokens |
| Expectations met | 5 of 6 (the answer is a table of seventeen lines) | 6 of 6 |

Both answers are right: nothing differs from yesterday. The marks are mine, not an independent grader's.

What the numbers are made of. About 60k of either run's tokens is what an agent spends before it does anything
(its own instructions and SKILL.md, which is read whole); the rerun instructions cut what comes after that from
about 14k to about 8k. The time is the suite (17.2 → 7.1 s) and three fewer turns.

## A new test through Claude (eval 0, `ticket-sort-bug`), for comparison

| | iteration 4 (skill 0.6.0) | this iteration (skill 0.13.0) |
|---|---:|---:|
| Agent wall-clock | 220.1 s | 177.7 s |
| Agent tokens | 104,316 | 129,880 |
| Browser runs | | 2 (the ticket's account, and a control) |

One run each. The answer is right (BUG, the list is not reordered for `problem_user`, Backpack $29.99 first; the
same spec passes for `standard_user`), and the spec it left keeps the login in a `login` block. The time is lower
and the tokens are higher: SKILL.md went from 302 to 374 lines over the six steps and the spec reference grew with
them, and an agent that writes a spec reads both.
