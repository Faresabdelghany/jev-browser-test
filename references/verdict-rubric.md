# Verdict rubric

Every run ends in exactly one verdict. The point of the rubric is to stop two failure modes: calling every
red run a bug (the developer stops trusting the reports) and calling every red run flaky (real bugs get
buried).

## Read result.json first

`python scripts/summarize_trace.py runs/<id>/<ts>/trace.json --result`. Three cases:

- **A declared outcome** (`outcome` is one of the spec's names): the verdict was decided when the spec was
  written; `verdict` is it (`pass` → PASS, `bug` → BUG, `test_issue` → TEST_ISSUE, `needs_human` →
  NEEDS_HUMAN). Sanity-check it in one glance: `evidence.line` should be the app's own words for that
  ending, `evidence.screenshot` should show it, `path_confidence` should be above `min_confidence` (the
  weakest decision on the way; a low value means the path there was shaky even if the ending is clear). If
  the outcome name does not match what you see, the spec mislabelled it: fix the `when` or the `verdict`
  (a one-line change) and rerun, and say so in the report.
- **`undetermined` with a suggestion** (`reason.suggested_verdict` set): start from the suggestion and
  confirm it with the rubric below; the typed reason (`reason.blocked_reason`, `reason.stuck_reason`) and
  `reason.status` tell you where to look in the trace.
- **`expected` present** (the spec declares `expect`): the verdict is "as declared" when `expected.matched`
  is true (report the real outcome and say it is the documented behaviour; exit 0, suite verdict `expected`),
  and a **change in behaviour** when it is false: `expected.mismatches` names what differs, and that difference
  is the finding (a fixed bug, a new one, a drifted page).
- **`reason.phase` set** (`navigation` or `setup`): the page was never observed. Not a verdict at all: a start
  URL that did not load in `navigation_timeout_ms` is the environment (suggested `flaky`: rerun, raise the
  timeout, stop running the suite on several workers against a slow host), a failed setup step is the spec's
  selector or wait (`test_issue`). Say so in one line and do not read the (empty) step table for meaning.
- **`undetermined` without a suggestion** (`done_unverified`, `assert_failed`, an `other` reason): the
  judgment below applies in full. For `assert_failed`, `reason.failed_assertions` carries the actual values:
  decide whether the assertion or the app is wrong, and never loosen an assertion to get green without
  saying so.

Jev only reports probabilities; deciding what they *mean* is Claude's job, and the outcome names keep that
job honest: a wrong verdict is visible as a wrong label, not hidden in a threshold.

## The five verdicts

**PASS** — `status == passed`: a pass outcome was seen and confirmed (`confirmed_by`: `assertions`, every
assertion held on the very page the pass was seen on; or `recheck`, a settle, a second observation and Jev
again), every assertion held, and a glance at `evidence.line` and `final.png` agrees. If `passed_without_actions` is set, do not report a
pass yet: the start page already showed the pass outcome, so the outcome or checks are too weak to prove
the flow works. Tighten them and rerun.

**BUG** (product defect) — the app did not behave as a user would expect, and the test's actions were
reasonable. Evidence needed before saying "bug":
- The step where behavior diverged (`n`, the action, its confidence ≥ `min_confidence`).
- What was expected vs. what the next step's page showed (checks, screenshot).
- The action would make sense to a human on that page (look at the offered element table: was there a
  better element Jev ignored? If so this is a test issue, see below).
Typical signatures: an outcome declared `bug` with the error in `evidence.line`; `stuck` with
`stuck_reason: control_had_no_effect` on a button that visibly does nothing; `done_unverified` where the
success page is missing content it should have; `blocked` with `blocked_reason: control_not_on_page`
because a control the flow requires is not rendered at all.

**TEST_ISSUE** — the spec, not the app, is at fault. Fix the spec and rerun before reporting anything.
Signatures: `blocked` right after a text field appears with no matching `data` value; checks phrased
so they can never be true ("the API returned 200"); goal ambiguous enough that Jev wandered
(`budget_exhausted` with sensible-looking actions); a cookie/consent banner or login wall that belongs in
`setup`; `low_confidence` on a page where the goal does not say which of several similar options to pick,
or where Jev split its `type_value` answer between two `data` keys (rename the keys to match the field labels
the app shows, e.g. `username`/`password` for fields labelled Username/Password); a `never` check that
plateaus just under `never_true` for several steps (the statement half-matches the page text: reuse the
app's exact words rather than lowering the threshold).
Up to two spec revisions are reasonable inside one task; if it still fails, report it as NEEDS_HUMAN with
what was tried.

**FLAKY / ENVIRONMENT** — `status == error`, `unstable_page` (the page kept changing while Jev decided, so
nothing was executed; each step's `stale` names what moved), timeouts, `executed.ok == false` on
network-heavy steps, or a result that differs across reruns. Rerun once (twice for a suspected flake).
Report as flaky only after a rerun disagrees with the first result, and include both traces. Never
diagnose flakiness from a single run.
Two different things read `flaky` in a suite, and the report must say which: **the environment** (a load
timeout, a stale page, an error run among passes) and **an application that varies by design** (every
disagreeing run ended in a *confident declared outcome* with a *different evidence line*: a notification
that is random, an A/B page). The second is not noise to retry away: if the spec asserts one ending of a
legitimate variation, the spec is wrong (TEST_ISSUE: assert what the page guarantees, `text_in` on the
element and an either/or pass outcome); if the product's contract forbids the variation, it is a BUG with a
measured rate. Keep environment failures out of that judgment: the suite already lists them apart.

**NEEDS_HUMAN** — the evidence is genuinely ambiguous: confidence is low and both a bug and a test issue
are plausible; the failure depends on domain knowledge the spec did not capture; the flow involves money,
deletion or sending messages and the runner stopped before a side effect. Say precisely what a human should
look at (step number, screenshot, the specific question).

## Triage-only mode: what to run, and what not to

When you are handed a run folder (`result.json`, `trace.json`, screenshots) the answer is in it. In order:

1. Read `result.json`, then the step table, then the pictures. Do not launch a browser first.
2. "Is it flaky?" is answered from the trace's **flake signatures** before any rerun: `stale` steps,
   `executed.ok == false`, `retried`, `usage.reconnects > 0`, a `settle` that ended on `cap` at the decisive step,
   `reason.phase`, an `error` status. None present and a confident declared outcome or a typed reason with a
   suggestion → the run is deterministic evidence; say so and do not rerun. Rerun (once) only when a signature is
   present, when the user explicitly asks for a rerun, or after a spec fix you made.
3. The cheapest way to separate TEST_ISSUE from BUG is a **control run**: the same spec with a known-good account
   or the sibling spec that is known to pass (`shop-checkout.json` beside `shop-checkout-error-account.json`). One
   run, ~10 Jev calls, and it settles whether the flow or the app is at fault. Prefer it to fetching the app's
   source code, which is not asked for and rarely changes the verdict.
4. Bound the work: one triage is one reading, at most one rerun and one control. A triage that takes longer than
   the run it judges has gone wrong.

## How to look at a run (in this order)

0. `result.json` (see above): outcome, verdict or suggestion, evidence line, assertions.
1. Summary line: status, actions, duration, `passed_without_actions` warning.
2. Step table: read the operations as a story. Does the sequence make sense for the goal?
3. Flags column: `LOW-CONF`, `ACTION-FAILED`, `FORCED-CLICK`, `DISPATCHED-CLICK`, `REPEAT×n`, `NEVER:*`,
   `STALE` (the page changed while Jev decided; nothing was executed, the loop observed again),
   `NO-TARGET-ANSWER`, `INVALID-ANSWER` (a Jev answer failed validation; the reason is in `step.invalid_answer`),
   `RETRIED` (the request was re-sent once), `ERROR`.
4. The step **after** the last sensible action: its checks and screenshot show what the app actually did.
   With the default `screenshots: "key"` only the terminal and flagged steps have a picture; the step
   before a divergence usually has none, but its element table and probabilities are in the trace
   (`--step N`). Rerun with `--screenshots all` when a human needs to see that page.
5. `--step N` for the divergence point: was the chosen element the right one? What else was offered?
6. `final.png`.

Do not rerun a run just because it is red. Read it first; a rerun that passes tells you nothing about
*why* the first one failed, and a `never_violated` with a clear error on screen is more informative the
first time.

## Confidence semantics

- `operation.confidence` / `target.confidence` are Jev's calibrated certainty about *its own decision*.
  Low values mean the page gave it several plausible moves, not that the app is broken.
- Check values are probabilities that a statement is true of the visible page. 0.55 on a `done_when`
  check is not "half passed": it means the page does not clearly show the outcome. Treat it as false and
  look at the screenshot.
- A step with high action confidence followed by a `never` firing is the strongest bug signal this tool
  produces: Jev was sure what to do, did it, and the app errored.

## Report template

Keep it short; the trace is the appendix. Use this shape (plain prose is fine for a PASS):

```
**Verdict:** BUG | PASS | TEST_ISSUE | FLAKY | NEEDS_HUMAN
**Flow:** <spec id> — <goal in one line>
**Result:** outcome <name> (<verdict> | undetermined, <reason.status>), <n> actions, <duration>s, <jev requests> Jev calls
**Expected result:** matched | NOT matched (<expected.mismatches>)                                       ← specs with `expect` only

**What happened:** <2–4 sentences: the story of the run (result.story), ending with where it diverged>
**Evidence:** "<evidence.line>" at step <n> (probability <p>, path confidence <c>), screenshot steps/<nnn>.png
**Expected:** <what a user should have seen>

**Next step:** <fix in the app | spec change made and rerun result | what a human should check>
**Fix:** <files changed, one line on the cause> — re-run: <status>, <n> actions (was <status>)   ← BUG only
Trace: runs/<id>/<ts>/trace.json (failing), runs/<id>/<ts2>/trace.json (after fix)
```

A BUG report without a fix attempt is incomplete when the repository is available: the spec is a
reproduction, so use it. The one hard rule: the fix must make the *app* behave as a user expects, never
make the *spec* easier to satisfy. If you find yourself loosening a check, an outcome statement or an
assertion to get green, stop — that is a TEST_ISSUE wearing a BUG's clothes, or a real bug you have not
understood yet.

If the user has an issue tracker connected (Linear, Jira, GitHub) and the verdict is BUG, offer to file it
with the evidence block and attach `final.png` and the divergence screenshot. Do not file without asking.
