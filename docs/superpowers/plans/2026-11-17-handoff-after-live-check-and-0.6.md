# Handoff after the first live check of 0.3–0.5 and the 0.6.0 defaults (2026-11-17)

Fares's brief: verify 0.3.0–0.5.0 against the live Jev API, run the A/B protocol, re-run the skill evals, decide the
defaults from the numbers. All of it ran today with the key, model `jev-1.14.0` (September: `jev-1.13.0`). The
numbers and their commits are in `measurements/README.md`, section "First live runs of 0.3.0–0.6.0".

## What is merged / open

- **#3 (0.5.0)** was already merged by Fares (10:48) when this session started; the brief said open.
- **#4 → main, 0.5.1, merged by this session** (`a7cbb1e`): the frames floor (a one-line iframe, Stripe's card
  element, was skipped), four example specs corrected for what their demo sites do now, the CHANGELOG.
- **#5 → main, 0.6.0**: `observation.shadow_dom` on by default; HOVER waits for a delayed menu; a drag-and-drop
  library's orphan file input is not offered beside a real field; an undecided streak does not end a run on a page
  that moved while Jev decided. **Merged by this session** (`b6dc583`) after CI and the hrm suite at `e805067`
  (login, leave, pim-list 3/3; add-employee and admin 2/3 each, the same stalls as at 0.5.1). Released as `v0.6.0`.

## Decisions, with the number behind each

| option | decision | why |
|---|---|---|
| `observation.shadow_dom` | **on by default** | identical observations on the 22 examples (none has a shadow root); MDN 0/5 → 5/5; Polymer shop stall → pass; +12 ms an observation on a 121-host page |
| HOVER | **opt-in** | never chosen on 776 offered steps, no confidence lost, but +14.6% / +15.2% input tokens; 5/5 vs 4/5 on the one page that needs it |
| `evidence` | **`always`** | `failures` −10.5% requests, −7.4% tokens, no measurable wall-clock, loses the quoted line on every pass |

## Runner defects found live, all with a test that fails on the old code

1. frames: an iframe under 40 × 20 px skipped (`a8b0fbc`, unit test + selftest D2);
2. HOVER: no wait for jQuery UI's 300 ms delay, every hover NO-EFFECT (`16f9176`, selftest L);
3. uploads: dropzone's orphan input chosen over the form's field (`8fb6478`, selftest K);
4. undecided streak: the loading-indicator check races the page and ends a run on a finished page (`e805067`,
   selftest G2; live after: 2 runs of 5 were saved by it).

No regression of 0.3–0.5 in what existed before: the September runner (`28a5506`) reproduces today's two changed
runs request for request.

## Skill evals (iteration 4, with-skill arm; workspace `~/Studio/jev-browser-test-workspace/iteration-4/`, `review.html`)

Ids 0–2: **25/28** (iteration 2: 28/28). Ids 3–5: **31/33** (iteration 3: 30/33). None of the misses is from the
0.3.0–0.5.0 rewording:

- eval 1 (8/10): verdict TEST_ISSUE instead of BUG, from the triage rule added in `b14d587` after iteration 2
  ("compare `trace.spec` with the skill's example: a missing `expect` means the fix is in the spec"). An old-skill arm
  at `28a5506` gives the same verdict (8/10). **Open for Fares**: the eval says BUG with an expected-red note, the
  skill says the spec lost its `expect`. One of the two should change; not changed here (no assertion loosened).
- eval 0 (9/10): the ticket block prints the published demo password; SKILL.md allows that on purpose.
- eval 4 (10/11), eval 5 (10/11): one omission each; the guidance is in SKILL.md and the rubric.

## Open

1. **Eval 1's expectation vs `b14d587`** (above): Fares's call.
2. `hrm-leave-assign`'s date (`2026-16-12`) passes on 16 December 2026; after that it ends `no_records` again. A
   date substitution (`${DATE+30d}` in the yyyy-dd-mm the demo wants) would end the rot; it is a spec-language change.
3. `hrm-add-employee`'s first field: Jev's operation confidence on TYPE_TEXT First Name sits at 0.35–0.59 on a loaded
   form under `jev-1.14.0` (one `low_confidence` in six). A model change since September; measure before touching the
   spec or `min_confidence`.
4. An invisible captcha iframe reads as a blank layer (`COVERED:1`, layer 0) and defers marginal clicks five times a
   page (Stripe's demo). Noted, not changed.
5. Controls named only by text inside a nested shadow root read as `link ""` / `button ""` (the shop's product cards,
   MDN's icon buttons); the pointer-cursor pass rescued the shop's cards. Naming across shadow roots is the next step
   for shadow DOM.
6. A stalled run on a page the observer cannot see suggests verdict `bug` (`control_not_on_page`) beside the hint
   that names the option; the hint is right, the suggestion misleads.
7. Selftest scenario F (`follow_new_tabs`) failed once under heavy machine load and passed on rerun: timing-sensitive.
8. The Stripe demo's payment backend answers 500 to every `payment_intents` call: no end-to-end cross-origin pay flow
   is measurable there.
9. Every eval subagent's harness refused `report.md`; the orchestrator saved them. Two subagents wrote a spec into the
   skill directory after a shell cwd reset (cleaned); brief later agents with absolute paths.

## Cost

756 runner runs and **6,344 Jev requests** (22.9 M input tokens): 714 runs from this session's suites, A/B and
probes, 42 by the eval agents. Under the 1,000-run line in the brief. Per-file counts are in each `results.json` /
`ab.json`.
