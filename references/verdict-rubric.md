# Verdict rubric

Jev only reports probabilities; deciding what they *mean* is Claude's job. Every run ends in exactly one
verdict. The point of the rubric is to stop two failure modes: calling every red run a bug (the developer
stops trusting the reports) and calling every red run flaky (real bugs get buried).

## The five verdicts

**PASS** — `status == passed`, and a glance at `final.png` agrees with the checks. If
`passed_without_actions` is set, do not report a pass yet: the start page already satisfied `done_when`,
so the checks are too weak to prove the flow works. Tighten them and rerun.

**BUG** (product defect) — the app did not behave as a user would expect, and the test's actions were
reasonable. Evidence needed before saying "bug":
- The step where behavior diverged (`n`, the action, its confidence ≥ `min_confidence`).
- What was expected vs. what the next step's page showed (checks, screenshot).
- The action would make sense to a human on that page (look at the offered element table: was there a
  better element Jev ignored? If so this is a test issue, see below).
Typical signatures: `never_violated` with a real error on screen; `stuck` on a button that visibly does
nothing; `done_unverified` where the success page is missing content it should have; `blocked` because
a control the flow requires is not rendered at all.

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

**NEEDS_HUMAN** — the evidence is genuinely ambiguous: confidence is low and both a bug and a test issue
are plausible; the failure depends on domain knowledge the spec did not capture; the flow involves money,
deletion or sending messages and the runner stopped before a side effect. Say precisely what a human should
look at (step number, screenshot, the specific question).

## How to look at a run (in this order)

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
**Result:** <status>, <n> actions, <duration>s, <jev requests> Jev calls

**What happened:** <2–4 sentences: the story of the run, ending with where it diverged>
**Evidence:** step <n> <action> (conf <x>) → step <n+1>: <check>=<p>, screenshot steps/<nnn>.png
**Expected:** <what a user should have seen>

**Next step:** <fix in the app | spec change made and rerun result | what a human should check>
**Fix:** <files changed, one line on the cause> — re-run: <status>, <n> actions (was <status>)   ← BUG only
Trace: runs/<id>/<ts>/trace.json (failing), runs/<id>/<ts2>/trace.json (after fix)
```

A BUG report without a fix attempt is incomplete when the repository is available: the spec is a
reproduction, so use it. The one hard rule: the fix must make the *app* behave as a user expects, never
make the *spec* easier to satisfy. If you find yourself loosening a check to get green, stop — that is a
TEST_ISSUE wearing a BUG's clothes, or a real bug you have not understood yet.

If the user has an issue tracker connected (Linear, Jira, GitHub) and the verdict is BUG, offer to file it
with the evidence block and attach `final.png` and the divergence screenshot. Do not file without asking.
