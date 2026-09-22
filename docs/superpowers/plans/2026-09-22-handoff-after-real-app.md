# Handoff after the real-application trial (2026-09-22)

This session did blocks A and B of `2026-09-22-next-session-brief.md`: the three offline fixes the review
round left, then a trial of the skill against real applications. Block C (token levers) was skipped, as the
brief said to unless Fares asked for it; he did not. The brief's premise for block B changed on the way:
instead of a private application with credentials in `.env`, Fares asked for public flows of my choosing
("we are building skill … choose the flow that you like to test, you have all internet"), so the trial ran
against public demo and practice sites. The brief (`2026-09-21-implementation-brief.md`) stays the rulebook
for commands, non-negotiables and the push recipe. Start with `git pull`.

## State of the repo

Selftest (`.venv/bin/python scripts/selftest.py`, 25 run scenarios plus the observer, settle, CDP-attach and
dotenv checks, 38.9 s) and unit tests (`.venv/bin/python scripts/unit_tests.py`, 76 tests) are green at HEAD.
`.env`, `.venv`, `runs/` and `specs/local/` are local and git-ignored. Every number in README / SKILL.md /
references comes from a file under `docs/superpowers/measurements/`, except the trial's own numbers below
(deviation 1).

Commits of the session, in order (`d896cc4..HEAD`):

- Block A, one commit per fix, pushed as `d896cc4..99f4a6a`: `9eab4fe` a run that wrote no `trace.json` is an
  environment failure, listed per spec, out of the outcome distribution and the agreement rate, never alone
  `flaky`; a spec with only such runs is `undetermined` with `reason`, the suite exits 2 only when every run
  of every spec failed that way · `99b0f0e` `results.json` / `results.md` carry `spec`, `out_dir`, `trace`
  (new) and `result` relative to the suite directory; `report.py` takes a suite directory or its
  `results.json` and renders one `report.html` per run, resolving the paths against it · `99f4a6a`
  `spec.py` and the runner warn on stderr when a `secrets` value resolves to fewer than 6 characters (exit
  codes unchanged, the value never echoed).
- Block B: `f982c9b` `specs/local/` git-ignored · `d833f95` observer pass 4: identical labels are told apart
  by the card or entry that contains them · `cf24586` a WAIT is not a repeated action; a budget spent waiting
  reports `still_loading` · `eecf79e` a BLOCKED right after a no-op action is suggested from that step's
  `stuck_reason` · `15e0214` measurement at `eecf79e` from a clean export · this handoff.

## What the real applications showed

Nine specs, all under `specs/local/` (git-ignored; they exist only in this checkout, see the memory note
and deviation 1), against public sites:

| spec | flow | exercises |
|---|---|---|
| `shop-checkout` | e-commerce demo: login in `setup`, add a named product from a grid of six cards, cart, a three-field form, overview, finish, confirmation | identical buttons, multi-page path, three `data` values, `setup` login |
| `shop-add-second-item` | the same grid: add the *second* card's product and open the cart | a probe that makes a wrong pick visible as an outcome |
| `shop-checkout-problem-account` | the checkout with a test account the site documents as broken (a form field that drops its input) | a declared `bug` outcome for a real reason |
| `shop-checkout-error-account` | the checkout with a second documented-broken account (a Finish button that does nothing) | `stuck_reason` after a no-op click |
| `wiki-search` | an encyclopedia's search box: type the term, the suggestions open, reach the article | a real autocomplete (`settle` ends `options`), a very long page |
| `todo-add-filter` | a todo demo: add two items, complete one, open the Active filter | TYPE_TEXT then PRESS_ENTER, two values into one field, a hidden checkbox under a styled box, hash routing |
| `load-wait` | a practice page: press Start, a loader runs for 5 s, then a text appears | settle and WAIT on a page with a timer |
| `notify-random` | a practice page whose notification is a random success or failure | the `flaky` verdict on a page that is random by design |
| `modal-close` | a practice page with a modal on load | an overlay that hides the whole page |

First pass (`runs/trial-1`, 9 specs × 1, 3 workers, 20.4 s, at `f982c9b`): 4 pass, 1 declared bug, **3
`low_confidence`, 1 `stuck`**. The two undetermined endings were runner defects (below), not spec problems.
After the fixes (`runs/trial-2`, 9 × 3, 2 workers, 89.3 s, at `cf24586`): **7 specs unanimous pass, 1
unanimous declared BUG, 1 unanimous `blocked`**, agreement 100% everywhere, no environment failure. The
`blocked` spec had no suggested verdict although Jev had said why; after the third fix its re-run
(`runs/trial-3`, 3 × 1, at `eecf79e`) reads "UNDETERMINED (suggested: bug 3)".

| spec | first pass (`f982c9b`) | after the fixes (`cf24586`, 3 repeats) | requests / input tokens / wall (medians) |
|---|---|---|---:|
| `shop-checkout` | `low_confidence` (target 0.43 / 0.40 / 0.31 over identical buttons) | `order_complete` pass 3/3, first seen at step 9, confidence 0.98 | 11 / 28,911 / 7,242 ms |
| `shop-add-second-item` | `low_confidence` | `bike_light_in_cart` pass 3/3, evidence the product's name | 5 / 13,143 / 4,492 ms |
| `shop-checkout-problem-account` | `form_error` **bug**, evidence "Error: … is required" | `form_error` bug 3/3, first seen at step 8 | 9 / 24,641 / 6,045 ms |
| `shop-checkout-error-account` | `low_confidence` | `blocked` 3/3, `blocked_reason: other`, `stuck_reason: control_had_no_effect` 0.97; suggestion none → **bug** 3/3 after `eecf79e` | 9 / 26,151 / 6,370 ms |
| `wiki-search` | pass | `article_shown` pass 3/3 | 5 / 47,872 / 5,672 ms |
| `todo-add-filter` | pass | `active_filtered` pass 3/3, 3/3 assertions | 9 / 19,078 / 6,083 ms |
| `load-wait` | `stuck` after 3 WAITs at 1.5 s of a 5 s loader | `loaded` pass 3/3 after 6 WAITs | 10 / 12,901 / 10,783 ms |
| `notify-random` | pass | `action_successful` pass 3/3 (no failure in 6 runs) | 4 / 4,531 / 5,322 ms |
| `modal-close` | pass | `modal_closed` pass 3/3 | 5 / 5,523 / 5,990 ms |

Things the demo login could never show, now seen live: a declared `bug` outcome with the app's own error
line as evidence (the broken form account, 4/4 runs); a `stuck_reason` after a no-op click (the dead Finish
button, 6/6 runs, 0.96–0.97); the options wait ending on a real autocomplete (`settle: options`, 3/3); Jev
choosing WAIT while a page loads (0.94–0.99); the confidence gate parking a decision made on a page whose
modal had not finished fading in (step 1 at 0.37–0.44, then the modal, then the pass). Not seen: `flaky`
(the random page succeeded 6/6), `outcome_unconfirmed`, `unstable_page`, an environment failure.

## Runner defects found and fixed (offline reproduction in `selftest.py`, one commit each)

1. **Identical labels** (`d833f95`). Six product cards, six `button "Add to cart"` with nothing to tell them
   apart: the context rule attached a row / list-item text only to unnamed controls and checkboxes, and the
   cards were plain `div`s. Jev split the target 0.47 / 0.21 / 0.18, refused three times, `low_confidence`
   (3 of 9 specs); the one run that clicked read `[14] button "Add to cart"` in its story, unreadable for a
   human too. Pass 4 of the observer groups kept elements sharing role and name without a context, climbs
   their ancestors strictly below the group's lowest common ancestor and keeps the highest level whose texts
   are non-empty and distinct: a price bar is distinct but says nothing, the card with its title does; one
   product's image and title buttons share the card, so they get no context (a first cut without the ceiling
   labelled one product's button with another product's text, caught by observing the live grid without
   Jev). Fixture: three cards with identical buttons, two at the same price, each with an image link and a
   title link sharing a name.
2. **A WAIT counted as a repeated action** (`cf24586`). Repeat detection keyed every executed operation; Jev
   chose WAIT on "Loading…" with `stuck_reason: still_loading`, and the third WAIT ended the run `stuck`
   1.5 s into a 5 s loader (suggested FLAKY, while the page was doing what it should). WAIT is now outside
   repeat detection; a budget that runs out on a streak of WAITs carries the last `still_loading` into
   `result.reason.stuck_reason` (the final look asks none) and is suggested FLAKY instead of the status
   row's TEST_ISSUE. Fixture: a loader that finishes after 1.2 s (passes after 10 WAITs) and one that never
   finishes (`budget_exhausted`, `still_loading`, flaky); the fixture was verified against the pre-fix runner
   (`stuck` after 3 WAITs) with the fix stashed.
3. **BLOCKED after a no-op** (`eecf79e`). Jev clicked the dead Finish button (0.99), saw `page_changed:
   false`, and chose BLOCKED with `blocked_reason: other` (0.62) while the same step's `stuck_reason` read
   `control_had_no_effect` (0.97): `other` has no row and `stuck_reason` only counted for `stuck`, so
   `result.json` suggested nothing. `build_result` now orders the typed answers per ending: `blocked` takes
   `blocked_reason` first and, when it has no row and the BLOCKED came right after an action that changed
   nothing, that step's `stuck_reason`. Live re-run: suggested `bug` 3/3. This applies the design spec's
   §5.3 rule ("the typed reason wins over the status") rather than changing it; `trace-format.md` had
   narrowed it to `stuck` and is updated.

Each fix is documented in `references/runner-design.md`, `references/trace-format.md` and a SKILL.md
troubleshooting row.

## Findings left as they are

- **Evidence lines for compound or absence statements are weak.** The adjudication picked no line for the
  todo spec (2 of 3 runs; its statement names a filter, a list content and a footer text), for the modal
  spec (3 of 3; the statement is about an absence) and for the loader (2 of 3, on a three-line page), and
  for the checkout pass it quotes the heading rather than the thank-you sentence. `present` stays high in
  all of them. A statement naming one visible string gets its line every time (the broken-form error, the
  product name, the article title). Remedy for a spec author: one visible string per `when`; for the runner:
  adjudicate each sentence of a compound statement, or accept `present` alone. Not changed.
- **Long pages cost tokens.** The encyclopedia spec sends ~9.6k input tokens per request (59–79 elements
  plus 4,000 chars of viewport-first text): 47,872 per 5-request run against 4,531 for a small page. Levers:
  `observation.max_text_chars` and the element cap, both per spec, both Block C territory (measure with
  `bench.py` before changing a default).
- **WAIT cadence.** Every WAIT is a request: the 5 s loader cost 6 WAITs (10 requests, 10.8 s). Doubling the
  pause on consecutive WAITs on an unchanged page (400, 800, 1,600 ms…) would cut that; a behaviour change,
  to be measured on the fixture and the live page before adopting. Not implemented.
- **A modal that fades in after the initial settle** is observed a step late: step 1 sees the page without
  it, Jev hesitates (0.37–0.44), the gate parks the decision, step 2 sees the modal. Inherent to the
  event-based settle; the documented remedies apply (`settle_ms`, a `setup` `wait_for`).
- **The broken form.** Jev typed into the field the app drops, saw it stay empty (`current_value` "" in the
  next table) and moved on to the next field rather than re-typing or stopping; the app's error on Continue
  ended the run as the declared bug, so the contract caught it, but a field that ignores input is not
  something Jev flags on its own.
- **`flaky` has no live demonstration yet.** The random page succeeded in every one of 6 runs; the verdict
  remains covered by the unit tests only.
- **No environment failure occurred** in 39 live runs, so A1's path is exercised by the unit tests only.

## Numbers with their files

The runner at `eecf79e` on both smoke specs, from a clean export (`2026-09-22-real-app-session-bench.json`,
`-suite.json` / `.md`; the row-by-row comparison against `9c20838` is in the measurements README): unchanged
by construction, requests and tokens identical (6 / 8,932 and 6 / 9,774), first sighting → confirming step
4 → 5 in 5/5, the same evidence lines, walls 6,376 / 6,359 ms inside the run-to-run spread; the suite 19.4 s
(was 20.8 s), all pass, agreement 100%. The trial's numbers above come from `runs/trial-1/results.json`,
`runs/trial-2/results.json` and `runs/trial-3/results.json`, which are **not** committed (deviation 1).

## Deviations and things to know

1. **The trial's specs and results are untracked.** The brief's rule "nothing app-specific in a tracked file"
   was written for a private application; the sites turned out public, but the rule was kept: the nine
   specs live in `specs/local/` (git-ignored) and their `results.json` carry the sites' own text, so this
   handoff describes the flows generically and cites untracked files, the first numbers in a handoff that do
   not come from a committed file. If the specs should become committed examples (they use public demo
   credentials in `setup`, like the smoke specs use the demo site's), move them to `specs/` and name the
   sites here; the memory note `real-app-trial-public-sites` records where they are.
2. **Fix 2 was coded before its fixture** (while a selftest was running), the reverse of the brief's order;
   the fixture was then run against the pre-fix runner (stashed) and reproduced the live `stuck` exactly
   before the commit. Fixes 1 and 3 followed the order as written.
3. **Fix 1's first cut was wrong on the live page and right on the fixture**: without the common-ancestor
   ceiling it accepted the price bars and labelled another product's text onto image buttons. Observing the
   real grid with the observer alone (no Jev, `scratchpad/peek.py`) caught it; the amended commit and the
   fixture with image/title pairs are what landed. Worth keeping as a habit: after an observer change, dump
   the real page's table before spending a run.
4. **`suggested_verdict` reads more of the typed answers** than before (`still_loading` for a budget spent
   waiting, `control_had_no_effect` for a BLOCKED after a no-op). The design spec's rule is unchanged;
   `trace-format.md`'s suggestion paragraph and the `blocked` / `budget_exhausted` rows say exactly when.
5. **Suite exit code with environment failures**: one launch failure among passes now leaves the spec `pass`
   and the suite at exit 0, with the failure listed per spec and counted in the `results.md` header; only a
   suite where every run failed that way exits 2. A run whose trace is unreadable (killed mid-write) stays an
   undetermined error run in the distribution (it ran).
6. **Public demo credentials are inline in the local specs' `setup`** (the site prints them on its login
   page), not in `.env`; `.env` still holds only `TYPESAFE_API_KEY`.
7. Block C not done; the levers above (WAIT backoff, text cap on long pages, the two `blocked_reason` levers
   from the previous handoff) are the candidates, each to be measured from a clean export with `bench.py`
   before and after.

## Suggested next steps (none required by the brief)

- Decide whether the trial specs become committed examples under `specs/` (they are the richest specs the
  skill has: a multi-page checkout with a declared bug, a real autocomplete, a create-and-filter list).
- A live `flaky`: a page that is random by design failed 0 of 6 times here; more repeats, or a different
  random page, would show the computed verdict on real runs.
- Adjudication for compound statements (one line per sentence) if evidence lines matter to the readers of
  `result.json`.
- Block C, if tokens or time matter: the WAIT backoff and the text cap have measured motivations now.

## Reminders

- The skill's copy in **Claude Desktop is behind the repo** (unchanged since the previous handoff, and this
  session added six code commits). Re-import from the repo, or stop exporting over this folder.
- Push recipe: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`.
- Live runs cost credit: the trial spent 39 runs (about 300 Jev requests) plus 20 for the measurement.
