# Handoff after the speed work (2026-11-17, night)

Fares asked for six steps to make the skill much faster without making it less correct, one branch and one pull
request a step, every new behaviour off by default until a live A/B earns it. All six are open as a stack. The
numbers are in `measurements/README.md`, sections "0.8.0" to "0.13.0".

## State

Six pull requests, each based on the one before, none merged (merging is Fares's):

| # | branch | version | what |
|---|---|---|---|
| 7 | `feat/replay` → `main` | 0.8.0 | replay: a passing run saves its path, the next walks it without Jev |
| 8 | `feat/form-batch` → #7 | 0.9.0 | one request per form (`--batch-fields`) |
| 9 | `feat/network-settle` → #8 | 0.10.0 | network-aware settle (`--settle network`) |
| 10 | `feat/sessions-cache` → #9 | 0.11.0 | `login` blocks, saved sessions, the HTTP cache |
| 11 | `feat/per-host-workers` → #10 | 0.12.0 | `--per-host`, `--host-limit`, `host_limit`, the scheduler |
| 12 | `feat/rerun-command` → #11 | 0.13.0 | `scripts/rerun.py`, replay resuming after a handover |

Merge in order. Each merge to `main` tags and releases its version; when a base branch is deleted on merge, GitHub
points the next pull request at `main`. CI was green on #7 to #10 when this was written; #11 and #12 were running.

- #11 has a merge commit (`feat/sessions-cache` merged in after the session fix): a force-push of the rebased
  branch was refused by the session's permissions, so the fix arrived by merge.
- #12 carries two fixes that belong to replay (step 1): the path resuming after a handover, and the deciding look
  taken after the assertions hold. They were found while measuring the six steps together and were put on top
  rather than rewriting five pushed branches. If #7 is merged alone, replay works and is slower than it could be on
  pages whose furniture loads at its own pace.
- The main checkout (`~/Studio/jev-browser-test`) is on `feat/replay`. Each later step has its own worktree:
  `~/Studio/jev-step2` … `jev-step6`, and `~/Studio/jev-v070` is the 0.7.0 tag for the "before" measurements.
  Remove them with `git worktree remove` once the stack is merged. `.jev/` in the main checkout is the last
  measurement's state (paths, sessions, caches); delete it freely.
- `dev-docs` is pushed: this handoff, eval 6, the measurement files of every step.

## What was decided, and on what

| | default | why |
|---|---|---|
| replay | off for `run_test.py` and `run_suite.py`, **on in `rerun.py`** | the same verdicts over 22 specs × 3 and requests 190 → 53; a first run should be Jev's from step 1 |
| `replay.verify` | `"jev"` | one request a spec keeps Jev's judgment of the ending; `"assert"` reaches zero requests and is as strong as the assertions |
| form batch | off | 2 requests and 0.5 s off a plain three-field form, nothing (and 9% more tokens) on a form that reacts |
| network settle | off | per-action median 249 → 100 ms and a fifth fewer requests on OrangeHRM, wall-clock unchanged there; −6% on public pages |
| saved sessions | off for single runs, **on in `rerun.py`** | 11 s of logins over four OrangeHRM specs; a session file is a logged-in browser on disk |
| HTTP cache | off, a flag in `rerun.py` too | page loads 19.0 → 7.7 s on the public specs; a first-visit load is sometimes what is under test |
| `--per-host` | 2 | what `--workers 2` protected a shared host with; **`--workers N` alone no longer puts N on one host** |

## Targets

- 198 s → about 110 s on one worker: **missed**. 136 to 159 s by default, 127 to 134 s with every option, 112 s once
  with the assertions deciding the endings.
- `shop-checkout` again in about 3 s: met (2.9 s; 2.0 s with every option).
- Jev tokens near zero on green reruns: met only with `--replay-verify assert` (0 to 8k); 74k to 84k by default.
- OrangeHRM "well under 560 ms per step" (step 3): the typing step, yes (100 ms); the flow's wall-clock, no.

## Open

1. **A new test through Claude costs more tokens than before** (104k → 130k, one run each): SKILL.md grew from 302
   to 374 lines. The paragraphs added to "2. Run" and "What makes a run fast" could move to the references, with
   one line each left in SKILL.md; then measure eval 0 again.
2. **The five OrangeHRM specs are the suite's floor** (59 to 116 s as a chain, one at a time). What is left there is
   the application answering and two specs that seed an employee in `setup` (6 to 14 s). A seeded record shared by
   the suite would need the specs to stop creating their own, which changes what they test.
3. **`hrm-add-employee`'s first field** went `low_confidence` in about one run in ten all day, in every arm. Still
   the morning's open item; replay hides it on reruns (the saved path has the decision).
4. **`employee_id_taken`** ended runs on the shared demo five times in arms with an option on and twice in arms
   without, over some two hundred OrangeHRM runs. No mechanism was found; if it matters, twenty runs an arm of
   `hrm-pim-add-employee-list` with and without `--http-cache` would say.
5. **`toolshop-search-cart`**: the practice site answered "0 products found for 'Pliers'" for stretches of the
   evening, with and without any option. The site, as far as the traces show; worth one look on another day.
6. **Saucedemo's session cookie lasts ten minutes**, so a saved shop session is usually expired by the next suite
   and costs a probe (0.4 s) before the fresh login. Harmless since the fix in #10; `session.max_age_s` in those
   specs could say 540.
7. **The settled-page shortcut** (ask Jev again after 300 ms when nothing is in flight) was measured and dropped:
   it made item 3 worse. The numbers are in section "0.10.0".
8. The stretch goal (export a passing spec as a plain Playwright test) was not started; it was to be asked first. A
   saved path already holds what such an export needs (operation, target description, value key per step).
9. Unchanged from the afternoon: the leave spec's last days of December, the ten identical `Copy` buttons on MDN,
   the captcha frame, selftest F's timing.

## For the next session

- The unit job in CI has no Playwright: a unit test that calls `run_test.main()` needs
  `mock.patch.dict("sys.modules", {"playwright": mock.MagicMock()})`. Run `python3 scripts/unit_tests.py` (the
  system interpreter has none either) before pushing.
- Do not edit a checkout's `scripts/` while a measurement runs from it: every run is a new process and reads the
  files as they are that second. Each step was developed in its own worktree for that reason.
- OrangeHRM's demo moves a five-spec chain by 40 s within an hour. Compare arms interleaved (`ab.py`), never one
  suite against another.
- A force-push is refused in this setup; bring a fix into an already-pushed stacked branch with a merge.
