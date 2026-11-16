# Handoff after the 0.3.0 and 0.4.0 pull requests (2026-11-16)

Fares asked for the review's quick wins and capability gaps. Both are open as pull requests; nothing is merged and
`main` is still at `28a5506`. This session had no TypeSafe key and no access to the demo sites: **every runner change
was verified offline only** (unit tests, the self-test with a scripted Jev, CI on Linux, macOS and Windows).

## The two pull requests

- **#1 `chore/quick-wins` → main, version 0.3.0.** MIT `LICENSE`, `CHANGELOG.md`, CI (`.github/workflows/ci.yml`), a
  release workflow that tags `v<version>` when main carries an untagged version, `run_suite.py --workers` default 2,
  `SKILL.md` 3,910 → 3,330 words, and `docs/` + `evals/` moved to this branch (`dev-docs`).
- **#2 `feat/capabilities` → `chore/quick-wins`, version 0.4.0.** Browser diagnostics, `teardown`, scripted
  `upload` / `hover` / `drag` / `check` and `"frame"` on a step, `observation.frames`, `browser.device`,
  `browser.follow_new_tabs`, `--junit`, Windows, the loading-indicator rule (open item 1 of the 2026-09-24 handoff),
  `selftest_capabilities.py`. `CHANGELOG.md` on that branch has the list.

## Where this branch fits

`docs/superpowers/` and `evals/` live here now. Beside a clone of main:

```bash
git fetch origin dev-docs && git worktree add dev origin/dev-docs -B dev-docs    # -> dev/docs, dev/evals
```

The eval prompts name their inputs as `evals/files/...`: run them from `dev/`.

## To do before merging, with a key

1. **Examples suite on #2's branch**, one worker for the `hrm-*` specs, and compare with
   `measurements/2026-09-24-examples-suite-b92b24f-seventeen.md`. No verdict should move: nothing new reaches Jev
   unless a spec opts in. Expect new flags only (`JS-ERROR`, `HTTP-4xx`, `HTTP-5xx`, `LOADING-IND`).
2. **`dynamic-controls` x 5.** The indicator rule should turn the 1/2 and 2/3 into passes: `LOADING-IND:1` on the
   undecided looks beside 'Wait for it...', five looks instead of three. If it still fails, the trace says whether
   the indicator was found (`step.loading_indicators`).
3. **Skill evals 0–5** on #1's `SKILL.md` and again on #2's. The triage section now points at the rubric instead of
   repeating it; evals 1 and 4 are the ones that would show a regression. Iteration 3's 30/33 is the reference.
4. **One live frames run.** A page with a real cross-origin iframe (a payment sandbox), `observation.frames` set.
   Offline it works against a same-origin frame on 127.0.0.1; what Jev makes of the `frame: <title>` context is
   unmeasured.
5. Tag the old state if wanted: `git tag v0.2.0 28a5506 && git push origin v0.2.0` (the session could not push tags).

## Decisions made, and why

- **Diagnostics never reach Jev.** They are evidence and two assertions. Putting console errors in the state would
  change every decision's input; measure before trying.
- **A loading indicator earns undecided looks only** (`run_test.loading_indicated`): not `page_busy`, no deferral, no
  longer confirmation. An indicator can be decoration that never goes away, and those waits run up to
  `navigation_timeout_ms`. The check is its own script (`observe.INDICATORS_JS`), run only on an undecided step:
  inside the observation it cost +24 ms on a 5,448-node page (63 → 88 ms); outside it the observation measures the
  same as before (61 vs 62 ms median, 120 interleaved runs).
- **Frames are opt-in per selector.** With none listed the observation is unchanged; an advert's iframe must not
  add choices. The run counts visible iframes and shadow hosts and a stalled run's summary names the option.
- **Shadow DOM, uploads, hover and drag are scripted, not Jev-driven.** Jev-driven versions mean new operations in
  the `operation` Choice (HOVER, UPLOAD_FILE) or a deep-traversal observer; both change what every step asks and
  need the A/B the rules got (`2026-09-22-track1-ab-*`).

## Open

1. Jev-driven shadow DOM: `OBSERVE_JS` uses `document.querySelectorAll`, `elementFromPoint`, `closest` and a
   TreeWalker, none of which cross a shadow boundary; about ten touch points, and `coveredAt` would read a control
   as covered by its own host until `elementFromPoint` descends into `shadowRoot`.
2. Jev-driven upload: offer `UPLOAD_FILE` only when the spec declares `files`, so existing specs are not asked.
3. Evidence lines from a frame: `adjudication_request` takes `extra_lines`; a listed frame's `LINES_JS` could feed it.
4. `follow_new_tabs` looks for the new tab once, after the action's settle. A tab that opens later is not followed.
5. Speed: nothing here made a run faster. The observation is 3 ms on a login page and ~60 ms on a 5,000-node page
   (the `cursor: pointer` scan), against ~300 ms per Jev request. The request count is still the lever: an option
   to skip the evidence request on a pass confirmed by assertions would save one request of five on the demo login.
6. The earlier handoff's items 2–4 (the `dynamic-controls` pass wording, the demo's switchable modules, eval
   prompts probed live first) are untouched.
