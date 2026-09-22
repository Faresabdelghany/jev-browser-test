# Handoff after blocks G and E of the post-trial brief (2026-09-22)

This session worked from `2026-09-22-next-session-brief-after-real-app.md`. It did **block G** (evidence lines
for compound outcome statements) and **block E** (a live `flaky`), in that order and ahead of the brief's
order, because **blocks D and F each wait on a decision from Fares** (D: promote the trial specs to committed
examples; F: only if tokens or time matter) and the session ran without him. G went first so that everything
measured afterwards, including D2's suite if D is a yes, runs the final code; E ran from a clean export of
G's commit. D and F are untouched: the brief's sections for them stand as written, and the questions are at
the end of this file. The rulebook is still `2026-09-21-implementation-brief.md`. Start with `git pull`.

## State of the repo

- Unit tests 80 (`.venv/bin/python scripts/unit_tests.py`), selftest OK (`.venv/bin/python scripts/selftest.py`,
  26 run scenarios plus the observer, settle, CDP-attach and dotenv checks, 42.5 s). Both green at HEAD.
- Commits of the session, in order (`d66f2ca..HEAD`): `20833f2` block G (code, tests, docs, one commit) ·
  `38b1f4b` block E (the measurement files and a README section) · this handoff.
- **Untracked, local only** (git-ignored, this checkout only): the nine trial specs in `specs/local/` plus a
  tenth written this session, `menu-random` (below); `todo-add-filter.json`'s pass statement is now two
  sentences (below). Results under `runs/`: `trial-1..3` (the trial), `g3-todo` (block G's live check). The
  trial handoff's table still describes every flow well enough to rewrite a lost spec.
- `.env` holds only `TYPESAFE_API_KEY`; the demo credentials of the shop specs are inline in their `setup`.
- Claude Desktop's copy of the skill is behind the repo (the last import predates the trial's six code
  commits and this session's one).

## Block G — evidence lines for compound statements (`20833f2`)

The trial's finding: a `when` naming several facts got no evidence line (todo spec 2 of 3 runs, modal 3 of 3,
loader 2 of 3) while `present` stayed high, because no single page line states all of it.

What changed:

- `policy.split_statement` splits a statement on `". "`, `"; "` and `", and "` into at most four sentences
  (the tail stays joined to the fourth; empty pieces dropped). A bare `" and "` is **not** a seam: every
  smoke and trial statement as written is one sentence, so their adjudication request is byte-identical to
  before (unit-tested: the one-sentence request has exactly the two keys it had).
- `policy.build_adjudication` asks one `evidence_line_<n>` Choice per sentence in the **same** request, each
  over the same numbered lines, with the sentence in the question's instructions; `evidence_present` stays
  a Noul over the whole statement. One adjudication request per run, as before; the cost is one copy of the
  lines per sentence.
- `run_test.adjudicate` reads every sentence's answer (`policy.evidence_line_keys`), keeps them all under
  `trace.adjudication.sentences` (`sentence`, `line_id`, `line`, `confidence` each) and quotes the pick
  `policy.quoted_pick` selects: **the most confident sentence that found a line**, the first in sentence
  order on a tie; a `none`, however sure, never beats a line; nothing found → the first valid answer.
- `spec.is_reserved_question`: `evidence_line_<n>` joins the reserved check / outcome names.
- Selftest scenario 18: a two-sentence statement whose first sentence names nothing on the fixture (`none`)
  and whose second names the header line; one request; `evidence.line` is the header. Unit tests for the
  split, the per-sentence request, the quoting rule and the reserved names.
- Docs: `references/runner-design.md` (the paragraph on adjudication), `references/trace-format.md` (the
  `sentences` field), `references/spec-format.md` (how to write a compound `when`; the reserved names),
  SKILL.md troubleshooting (a row for `evidence.line` null with a right outcome), design spec §5.4 (an
  amendment paragraph).

The live check (G3), `todo-add-filter` × 3 from the working tree before the commit (`runs/g3-todo`, not
committed): the spec's statement rewritten as "The Active filter is selected and the list shows only 'walk
the dog'. The footer says '1 item left'" (the brief's seams touch no trial statement as written, so one had
to be rewritten to exercise the split; the todo spec was the one the brief named). Result: pass 3/3,
agreement 100%, **an evidence line in 3 of 3 runs** (trial: 1 of 3). The picks, per run:

| run | sentence 1 ("… selected and the list shows only 'walk the dog'") | sentence 2 ("The footer says '1 item left'") |
|---|---|---|
| 1 | "walk the dog", confidence 0.27 | "1 item left", 1.0 |
| 2 | "All Active Completed" (the filter bar), 0.31 | "1 item left", 1.0 |
| 3 | "walk the dog", 0.28 | "1 item left", 1.0 |

Under the brief's rule ("keep the first line found") the quoted line would have been the hesitant one, once
the filter bar. The quoting rule was changed to the most confident sentence after seeing this and its effect
re-derived from the same three traces: "1 item left" (1.0) in 3 of 3. It was not re-run live: the picks
come from the same request, only the choice among them changed, and the selftest scenario covers the rule.
Medians 9 requests / 19,349 input tokens / 7,136 ms against the trial's 9 / 19,078 / 6,083 on the same spec:
the second Choice adds about 270 input tokens on this eight-line page (the wall difference is the site's
day-to-day variance; the trial's own runs spread 5,9–7,2 s).

No `bench.py` run for G: no number in README / SKILL.md / references changes, because the smoke specs'
requests are unchanged by construction. D2's suite, if D is a yes, is the first committed measurement that
includes G.

## Block E — a live `flaky` (`38b1f4b`)

`notify-random` × 5, 2 workers, from a `git archive 20833f2` export in the scratchpad with `GIT_COMMIT` set
and the local spec copied in: **`flaky`**, `action_successful` (pass) 3, `action_unsuccessful` (bug) 2,
agreement 60%, `all_pass: false`, no environment failure, every run in a declared outcome (the previous 6
runs had all succeeded). Evidence lines "Action successful" 3/3 and "Action unsuccesful, please try again"
2/2, the page's own words. A bug run is one step and one request shorter than a pass run (3 / 3,205 input
tokens against 4 / 4,531): terminal at first sighting, no settle-and-recheck. Files
`docs/superpowers/measurements/2026-09-22-live-flaky-suite.json` / `.md`, README section "A live `flaky`".
The measurement cites an untracked spec, as the brief anticipated ("or its example twin"); the committed
files contain no URL and the README describes the page generically, pending D.

E1's second page was not needed. A spec for it exists anyway, written before the first five runs came back:
`specs/local/menu-random.json`, the practice site's menu that drops one of its five entries on some loads
(pass `all_entries` "every entry is listed", bug `entry_missing` "an entry is missing", one assertion on the
entry's link, `max_steps` 4, nothing to click). Peeked with the observer alone (no Jev, a rewritten
`scratchpad/peek.py`, gone with the scratchpad): the entry showed on 1 of 4 loads. **Never run with Jev.**

## Findings left as they are

- A sentence that still joins two facts with a bare "and" draws a hesitant pick (0.27–0.31 above). The split
  deliberately does not touch bare "and": the smoke statements would split and their evidence lines change
  ("Secure Area" is a line too). The remedy is the author's: one visible string per sentence
  (`references/spec-format.md`).
- The checkout specs' pass statement ("The page heading says 'Checkout: Complete!' and the text 'Thank you for
  your order!' is shown") is one sentence and still quotes the heading (trial finding). As two sentences it
  would quote whichever Jev is surer of. Not changed: local specs, D's decision.
- The modal spec's statement is an absence: no line can state it, `present` is its evidence. Documented, not
  changed.
- Long pages, WAIT cadence, the `blocked_reason` levers: block F, untouched.

## Numbers with their files

- The live `flaky`: `2026-09-22-live-flaky-suite.json` / `.md` (`git_commit: 20833f2`), README section.
- Block G's live check: `runs/g3-todo/results.json` and its three traces, **not committed** (working tree,
  before the quoting-rule change); the numbers above are the only place they are recorded.
- Everything else in README / SKILL.md / references is unchanged and still comes from the files the
  measurements README lists.

## Deviations and things to know

1. **Order.** G and E before D and F: D needs a yes, F needs "tokens or time matter", and neither could be
   asked mid-session. Nothing in G or E depends on D's answer.
2. **The quoting rule** is "the most confident sentence", not the brief's "first line found", after the live
   picks above; a deviation from the letter of G1 in the service of its purpose (an evidence line that
   states the outcome). The design spec §5.4 amendment says so.
3. **G3 ran before the commit and before the rule change**, from the working tree; the rule's effect was
   re-derived from those traces, not re-run. Three runs, not a measurement.
4. **A local spec was rewritten** (`todo-add-filter`, two sentences) to exercise the split live; the brief's
   seams match no trial statement as written. If D promotes the specs, this is the wording that goes in.
5. **E2 cites an untracked spec** and describes the page generically; the committed results carry no URL,
   only the two notification texts. If D is a yes, D3 replaces the generic wording.
6. **No bench for G** (see above). 8 live runs this session (3 + 5), about 47 Jev requests.
7. **`menu-random`** exists locally and was never run with Jev; it is not one of the nine trial specs, so D as
   written does not include it. Cheap to include (4 requests a run) if wanted.

## Open for Fares (the brief's own gates)

- **Block D, yes or no:** promote the nine trial specs (public demo and practice sites, public demo
  credentials inline) from `specs/local/` to `specs/examples/`, run the suite × 3 from a clean export and
  commit it as `<date>-examples-suite.json` / `.md`, name the sites in README.md, SKILL.md and the trial
  handoff. Say also whether `menu-random` joins them.
- **Block F:** only if tokens or time matter. The five levers and their measurement recipe are in the brief.

## Reminders

- Push recipe: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`.
- After an observer change, dump the real page's table without Jev before spending a run (`observe.observe`
  + `render_table` + `LINES_JS` in a ten-line script).
- Re-import the skill into Claude Desktop from the repo, or stop exporting over this folder.
