# Handoff after 0.7.0 (2026-11-17, afternoon)

Fares chose four items from the morning's handoff (`2026-11-17-handoff-after-live-check-and-0.6.md`, "Open" 1, 2, 5,
6): keep the triage rule and change eval 1, the date placeholder, naming across shadow roots, the suggested verdict.
All four are done. The numbers are in `measurements/README.md`, section "0.7.0".

## State when this was written

- `main` is at `b6dc583` (0.6.0). The work is on the local branch **`feat/dates-shadow-names`**, five commits
  (`45d681b` verdict, `3983b35` dates, `ff5385e` shadow names, `83c61d5` `ab.py --a-runner`, `554b427` 0.7.0
  changelog and version). **Not pushed, no pull request**: pushing, CI on the three systems and the merge (which
  tags and releases `v0.7.0`) are Fares's to start.
- `dev-docs`: this handoff, the eval change, the measurement files and one experiment spec, committed locally on top
  of `74033d5`, not pushed.
- Offline at `554b427`: 191 unit tests, SELFTEST OK (macOS only; Windows and Linux are CI's).

## What changed, in one line each

1. **Eval 1** expects TEST_ISSUE (expectations 1 and 8 rewritten). Re-graded, not rerun: 10/10 on both arms.
2. **`${DATE...}`** with terms, a format and a `calendar` for `+workday`; `hrm-leave-assign` uses
   `${DATE+2d+workday:yyyy-dd-mm}`. Live: pass today ×3 (one in the suite), pass pinned to 17 December.
3. **Names across shadow roots and slots**; entries inside a link across a shadow boundary are the link. A/B: MDN's
   Copy button 1/5 → 5/5; nothing else moved.
4. **Suggested verdict** `test_issue` with `reason.hints` when the control could not be found on a partly unobserved
   page.
5. Not asked for, needed for 3: `ab.py --a-runner` compares two versions of the runner.

## Open

1. **`hrm-leave-assign` cannot pass on the last two to four days of December**: the next working day is in January
   and the demo's Leave List shows the current leave year. The fix would be in the flow (set the list's To Date),
   two more steps for Jev on a form whose date fields open a calendar that eats the next click. Not done.
2. **Naming costs a little certainty on a page full of named buttons.** On MDN Jev's DONE confidence after the goal
   fell 0.60 → 0.47 (10 runs an arm). Nothing moved because the assertion confirms the pass; a spec without
   assertions on such a page would take its confirmation looks at lower confidence. Not measured further.
3. **Ten identical `button "Copy"`** on MDN get no context: the identical-labels pass climbs `parentElement` and
   stops at each shadow root. Following `up()` there is the next step for shadow DOM, and needs its own A/B.
4. MDN's code editor is the one control still unnamed there (a contenteditable inside a component, no label).
5. Unchanged from the morning: `hrm-add-employee`'s first field under `jev-1.14.0` (measure about ten runs before
   touching anything); the invisible captcha frame that reads as a loading layer (wants a second real page);
   selftest scenario F's timing under load; the Stripe demo's dead backend.
6. Eval 1 was re-graded on saved reports. A fresh run of ids 0–2 would confirm 27/28 or better with 0.7.0's SKILL.md
   (three agents, about 100k tokens and a few browser runs each).

## For the next session

- zsh does not split `$VAR` into arguments: a suite over `$(ls specs/examples/*.json ...)` belongs in a bash script
  (the first release check here failed in a second with "spec file(s) not found").
- A log file from an earlier attempt satisfies `until grep -q "^exit" log`: wait on the result file instead.
