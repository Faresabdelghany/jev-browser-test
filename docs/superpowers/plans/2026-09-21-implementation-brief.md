# Implementation brief — hand this to a fresh session

You are implementing an approved design in the `jev-browser-test` repo. Read this whole brief, then read
the spec it points to, then start. Do not re-brainstorm the design; it was reviewed and approved on
2026-09-21. Ask only when the spec and this brief genuinely conflict.

## 1. Where things are

- Repo: `/Users/fares/Downloads/jev-browser-test` (git, branch `main`, remote
  `https://github.com/Faresabdelghany/jev-browser-test`, **public**). Start with `git pull`.
- Spec (the source of truth for *what* to build):
  `docs/superpowers/specs/2026-09-21-ultrafast-loop-and-results-contract-design.md`. Sections: §2 baseline
  numbers, §3 what to keep, §4 Track 1 (items 4.1–4.11), §5 Track 2, §6 Track 3, §9 decisions.
- Reference implementation the loop is modelled on: `https://github.com/browser-use/jev-ultrafast`
  (read at commit `1231850`). Clone it into the scratchpad if you need to look at `agent.py`, `model.py`,
  `questions.py`, `snapshot.js`, `browser.py`, `docs/design.md`.
- Jev docs: `https://docs.typesafe.ai/llms.txt` (index), `/api.md`, `/primitives/choice.md`,
  `/confidence.md`, `/patterns/fan-out.md`, `/cookbooks/consistency_choice_cookbook.md`,
  `/cookbooks/semantic_find.md`. Facts already verified and relied on by the spec: Choice ≤ 255 options;
  Choice/Score return `confidence` (distribution concentration), Noul does not; adding questions to one
  request barely changes latency; input is text only.
- Environment: `.venv/` exists with Playwright 1.63 + Chromium (`.venv/bin/python`). `.env` holds
  `TYPESAFE_API_KEY` and is git-ignored; `run_test.py` and `spec.py` load `./.env` themselves. If `.venv`
  is missing: `python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt &&
  .venv/bin/playwright install chromium`.
- Commands you will use constantly:
  - `.venv/bin/python scripts/selftest.py` — offline harness (fake Jev, local fixture pages). Must end
    `SELFTEST OK`, exit 0. Run it after every task.
  - `.venv/bin/python scripts/spec.py specs/smoke-login.json` — validate a spec.
  - `.venv/bin/python scripts/run_test.py specs/smoke-login.json` — live run (costs Jev credit; a run is
    ~4–6 requests). `specs/smoke-login.json` must end `passed`; `specs/smoke-login-badpw.json` must end
    with the bad-credentials outcome (today: `never_violated`).
  - `.venv/bin/python scripts/summarize_trace.py runs/<id>/<ts>/trace.json [--step N]`.
- Pushing: the repo owner account is `Faresabdelghany`; the active `gh` account is usually the work
  account. Push with `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`
  (with two accounts logged in, the bare `gh auth switch` toggles back to the other one).
- Commit attribution: end every commit message with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  (or whatever attribution line your session's system reminder specifies).

## 2. What the skill is (so your changes keep its shape)

Claude writes a spec (goal, prepared `data` strings, checks, and — after Track 2 — the outcomes it will
accept back). The runner drives a real browser: each step Playwright builds a numbered table of visible
interactive elements, one TypeSafe request asks Jev for `operation` + speculative per-operation targets +
the checks as Nouls, the runner executes only the target matching the chosen operation, observes again.
No text model anywhere: Jev only chooses among prepared strings. The trace is evidence; Claude judges.

Read these before touching code: `SKILL.md`, `references/runner-design.md`, `references/spec-format.md`,
`references/trace-format.md`, `references/verdict-rubric.md`, then `scripts/run_test.py` (the loop),
`scripts/policy.py` (state + questions), `scripts/observe.py` (element table), `scripts/jev_client.py`,
`scripts/spec.py`, `scripts/selftest.py` (the harness — note `FakeJev.system_one` reads
`state["visible_text"]`, `state["actions_so_far"]` and `state["interactive_elements"]`; when the state
becomes structured in Track 1 those reads must move to `recent_actions` / `elements`).

## 3. Scope and order

Implement **Track 1, then Track 2, then Track 3**, exactly as specified. Each track ends with its
measurement, doc updates, and a push. Within Track 1 the order is 4.1 → 4.7 first, then 4.8 → 4.10:

1. **4.1 Persistent connection** (`jev_client.py`): one `http.client.HTTPSConnection` kept on the client;
   on `RemoteDisconnected` / `BrokenPipeError` / `ConnectionError` / `http.client.HTTPException` reconnect
   and retry once (calls are read-only); keep the 429/5xx backoff; stdlib only. Accept: median
   `latency_ms.jev` ≤ 350 ms on `smoke-login` (measured 304–307 ms warm vs 700–1000 ms fresh).
2. **4.7 Strict answer validation** (`policy.read_choice`, `resolve_target`, loop): valid iff `choice` is
   an offered key, every probability key is offered, values finite in [0,1], sum 1 ± 0.02, `confidence`
   in [0,1], and `choice` has the max probability (within 1e-6). Invalid → `None` +
   `step.invalid_answer = "<reason>"`; a missing/invalid `operation` retries the request once, then
   `error`. `build_questions` must return the offered keys per question in `meta` so validation has them.
3. **4.2 Structured state** (`policy.build_state`): the JSON shape in the spec; history becomes a list of
   dicts; `page_changed` for an action is set when the *next* observation's signature is compared to the
   one the action was decided on; keep the last 10.
4. **4.3 Structured criteria**: target options become objects (`element`, `role`, `current_value`,
   `checked`, `context` — omit empties); `type_value` options `{key, value}` (use the field name `value`
   in both state and criteria; the spec's `preview` in one example is the same thing).
5. **4.4 Rules** (new `scripts/rules.py`: `NEXT_ACTION`, `TARGET`, `CHECK`), attached as
   `instructions: {"goal", "rules"}` on `operation`, `{"goal", "operation", "rules": [NEXT_ACTION, TARGET]}`
   on targets, `{"statement", "rules": CHECK}` on Noul checks. Wording is in spec §4.4; it includes the
   untrusted-page-text guard. `jev_client.choice/noul` currently type `instructions` as `str`; widen to
   `str | dict`.
6. **4.5 Event-based settle** (`run_test.settle`, page-side JS): `domcontentloaded` (short timeout,
   ignored on failure) then a promise that resolves after 2 animation frames **and** `quiet_ms` (100) with no
   DOM mutations, capped at `settle_ms` (now the cap, default 400); after TYPE_TEXT into a
   `combobox`/`searchbox` also wait for a visible `[role=option]` up to 200 ms; if the evaluate throws
   because the document navigated, retry once on the new document. New `browser.quiet_ms` in DEFAULTS +
   validation. WAIT operation: sleep `settle_ms`, then the normal settle.
7. **4.6 Freshness guard** (`observe.py` new fingerprint JS, loop): identity and meaning, **not
   geometry**. At observe time record per kept node `[connected, visible, value, checked, disabled,
   scope_hash]` (scope = nearest `form, dialog, [role=dialog], tr, [role=row], li, label` or parent; hash
   its innerText, capped 2000 chars, with a small string hash in JS) plus `url`, `title`, first 500 chars
   of visible text. Before executing: for CLICK/TYPE_TEXT/SELECT compare only the **target node's** tuple
   + url; for DONE/BLOCKED/PRESS_ENTER compare url, title, text head and all node tuples; for
   SCROLL_*/WAIT skip. Same JS function must produce the tuples in both places. Stale →
   `step.stale = "<reason>"`, `executed = {"action": "WAIT", "reason": "page changed during the decision:
   <reason>"}`, nothing executed, not counted as an action, re-observe. `thresholds.max_stale` (3)
   consecutive → new terminal status `unstable_page`. Never retry a mutation.
8. **4.8 Observer**: `observation.max_elements` default 60 → 200, validated 1..250; `visible_text`
   viewport-first (TreeWalker over text nodes: in-viewport first, then the rest, cap
   `max_text_chars`, default 2000 → 4000). `signature()` keeps using the first 500 chars.
9. **4.9 `browser.cdp_url`**: `chromium.connect_over_cdp`; first existing context or a new one; new page;
   on exit close **only that page**; `storage_state` ignored when attached. Selftest can cover it by
   launching Chromium with `args=["--remote-debugging-port=9333"]` and attaching to
   `http://127.0.0.1:9333`.
10. **4.10 Screenshots** `observation.screenshots: true | false | "key"`, default `"key"`, CLI
    `--screenshots all|key|none` (`--no-screenshots` stays as an alias for none). Capture moves to
    **after Jev's answer, before execution**; in `"key"` mode only for terminal steps or steps with
    `never_violated`, `low_confidence`, `stale`, `repeat_count ≥ 2`; a failed action is captured right
    after the failure; `final.png` always unless none. The loop has ~8 terminal `break` sites — introduce
    one `finish(step, status, executed)` helper rather than duplicating the capture.
11. **4.11 Measurement**: add `scripts/bench.py <spec> --repeat N [--json out]` (runs `run_test.py` as
    a subprocess N times; prints and saves medians of wall, `duration_ms`, Jev ms, browser ms, requests,
    input tokens, decision confidence, plus status counts and stale-step counts). **Before any code
    change**, record the baseline: 5× `smoke-login` and 5× `smoke-login-badpw` →
    `docs/superpowers/measurements/2026-09-21-track1-baseline.json`. After Track 1, repeat →
    `...-track1-after.json`. Acceptance: median wall ≥ 40% lower, outcomes 5/5 unchanged, median decision
    confidence not lower, selftest OK. Then run the target-question phrasing A/B (premise named vs
    implicit) behind a temporary env knob, adopt the winner, remove the knob, record the numbers.

Then **Track 2** (spec §5: `outcomes` Choice with `none_yet` + pre-declared verdicts, `assert` block
checked in code on the final observation, `blocked_reason` always / `stuck_reason` when
`page_changed` is false, `pending_outcome` confirmation for `pass`, first-sighting termination for the
rest, `undetermined` with typed reason + `suggested_verdict` table, new status `outcome`, final
adjudication request selecting the evidence line, `result.json`, synthesized outcomes for old specs so
their pass/fail and exit codes are unchanged, docs + rubric + SKILL.md, selftest cases). Acceptance in
§5.8.

Then **Track 3** (spec §6: `scripts/run_suite.py` with subprocess workers and `--repeat`, `results.json`
+ `results.md` with outcome distribution, agreement rate and a `flaky` suite verdict on disagreement;
SKILL.md guidance to launch it with `run_in_background` and read `results.json`; `scripts/report.py`
producing a single static `report.html`). Acceptance in §6.

## 4. Non-negotiables

- No new runtime dependency: stdlib + Playwright. Tests are `scripts/selftest.py` plus, for pure
  functions, a new stdlib-`unittest` file run as a script (`.venv/bin/python scripts/unit_tests.py`) so
  `scripts/` is on `sys.path` like the other entrypoints.
- Every behavioural change lands with a selftest or unit case. Selftest must be green after every task.
- Keep the `run_test.run(spec, jev, out_dir)` seam: anything with `system_one(state, questions)` and
  `usage_summary()` must still work (that is how the fake Jev plugs in).
- Keep `spec.data` — never add a text-generation model. Never let a model answer become a selector,
  coordinate or code: targets are indices into the observed table only.
- Never commit `.env`, `runs/`, `.venv/`, `.remember/`. `git status --short` must be clean of them.
- No employer-specific content in this repo (URLs, flows, company names, account handles). Generic demo specs only
  (`the-internet.herokuapp.com`).
- Every number in README/docs comes from `bench.py` output, with before/after files committed.
- Small commits, one per task, in the order above. Push after each track completes and its
  measurement is recorded.
- If something in the spec turns out to be wrong in practice (e.g. the `"key"` screenshot default costs
  more triage than it saves), do not silently deviate: finish the task as specified, then write the
  finding and the proposed change in your final report.

## 5. Baseline you are improving on (2026-09-21, `jev-1.13.0`)

`smoke-login`: passed, 3 actions, 8,961 ms wall, 4 Jev calls, Jev 3,355 ms, settle 2,312 ms,
observe+screenshots+navigation 3,294 ms, 3,858 in / 781 out tokens.
`smoke-login-badpw`: never_violated, 3 actions + 2 refused low-confidence steps, 18,412 ms, 6 calls,
Jev 8,162 ms, settle 3,445 ms, other 6,805 ms.
Fresh connection per request 1023 / 717 / 688 ms; persistent 835 / 304 / 307 ms.

## 6. When you finish (or stop)

Report per track: what changed (files), the before/after medians, which acceptance criteria passed or
failed with the actual numbers, anything you deviated from with the reason, and the commits pushed.
Remind the user that the skill's copy in Claude Desktop is now **behind** the repo: exporting from
Desktop over this folder would revert the work, so the Desktop copy should be re-imported from the repo
(or the export stopped) before the next round.
