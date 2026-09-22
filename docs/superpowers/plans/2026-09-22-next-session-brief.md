# Brief for the next session — after the review round (2026-09-22)

You are continuing work on the `jev-browser-test` repo. The design is implemented, measured and pushed;
this session validates it on a real application and closes the small items the review round left.
Read this brief, then the handoff it points to, then start. Do not re-brainstorm the design. Ask only
when this brief and the code genuinely conflict, or for the real-app details in block B.

## 1. Where things are

- Repo: `/Users/fares/Downloads/jev-browser-test` (git, branch `main`, remote
  `https://github.com/Faresabdelghany/jev-browser-test`, **public**). Start with `git pull`; HEAD should be
  at or after `3c5c665`.
- Read first: `docs/superpowers/plans/2026-09-22-handoff-after-track3.md` (state, numbers, deviations 1–9),
  `docs/superpowers/measurements/README.md` (how every number is derived), then `SKILL.md`,
  `references/runner-design.md`, `references/spec-format.md`, `references/trace-format.md`,
  `references/verdict-rubric.md`. The original rulebook,
  `docs/superpowers/plans/2026-09-21-implementation-brief.md`, still applies (its §1 environment, §2
  shape of the skill, §4 non-negotiables).
- State at `3c5c665`: unit tests 74 (`.venv/bin/python scripts/unit_tests.py`), selftest OK
  (`.venv/bin/python scripts/selftest.py`, 22 run scenarios plus observer / settle / CDP / dotenv checks,
  ~37 s). Both green at HEAD.
- Commands: `.venv/bin/python scripts/spec.py <spec>` validates; `.venv/bin/python scripts/run_test.py
  <spec>` is one live run (~6 Jev requests); `.venv/bin/python scripts/summarize_trace.py <run
  dir>/trace.json --result` is the first triage step; `.venv/bin/python scripts/run_suite.py <specs...>
  --repeat N --workers W` is the hands-off suite (launch it with the Bash tool's `run_in_background`, read
  `results.json` when it finishes); `.venv/bin/python scripts/bench.py <specs...> --repeat 5 --json
  <file>` measures.
- Measurements that cite a commit are taken from a clean export, never from the working tree: commit,
  push, `git archive <sha> | tar -x -C <scratchpad>/export-<sha>`, copy `.env` in, run there with the
  repo's `.venv/bin/python` and `GIT_COMMIT=<sha>` set, bench then suite (not at once), write the files
  into `docs/superpowers/measurements/` as `<date>-<what>-<file>.json` and add a section to its README.
- Pushing: `gh auth switch --user Faresabdelghany; git push origin main; gh auth switch`. End every commit
  message with the attribution line your session's system reminder specifies.

## 2. What this session does, in order

### Block A — offline fixes the review left (one commit each, unit tests with the fake runner)

A1. `scripts/run_suite.py`: a run with no `trace.json` and runner exit code 2 is an **environment
    failure**, not an outcome. Record it (`status: "error"`, the stderr tail) but exclude it from the
    outcome distribution and the agreement rate, list it per spec as `environment_failures`, and never
    let it alone turn a spec `flaky`. A spec whose every run failed that way ends `undetermined` with
    that reason; the suite exits 2 when every run of every spec did. Update the docstring and the
    "Suite results" section of `references/trace-format.md`. Today one launch failure among passes reads
    `flaky` (handoff deviation 9).
A2. `scripts/run_suite.py` and `scripts/report.py`: write `out_dir`, `result`, `trace` and `spec` paths
    in `results.json` / `results.md` **relative to the output directory** (the committed
    `2026-09-22-review-fixes-suite.*` files carry dead absolute scratchpad paths); `report.py` resolves
    them against the `results.json` location. Unit test both. Do not rewrite the committed files.
A3. `scripts/spec.py` `validate`: a **warning** (stderr, not a problem, exit code unchanged) when a
    `secrets` entry resolves to a value shorter than 6 characters, naming the key: `mask_secrets`
    replaces every occurrence, so a secret like `1` or `2024` rewrites unrelated UI text Jev decides on.
    Document in `references/spec-format.md` under `secrets`. Unit test.
A4. Push block A.

### Block B — the real application (the reason for this session)

Everything so far was validated on the demo login page, which cannot produce `flaky`, `stuck_reason`,
`outcome_unconfirmed`, a `blocked` flow or a failing whole-document assertion for a real reason.

B1. Fares gives you the application's URL, the flows to cover (2–3, e.g. login, a create form, a
    search/list), and the names of the environment variables that hold the credentials. If any of that
    is missing, ask before writing a spec. Credentials go into `.env` as variables referenced from the
    spec with `${VAR}` and listed under `secrets`; nothing app-specific is ever written into a tracked
    file.
B2. Put the specs under `specs/local/` and add `specs/local/` to `.gitignore` in its own commit **before**
    writing them. `git status --short` must never show them. No URL, company name, account handle or
    flow of the real app appears in any tracked file, commit message or measurement file; findings are
    written generically ("a form whose submit button is disabled until every field validates").
B3. Validate each spec, do one live `run_test.py` per spec and read `result.json`; fix the spec until the
    pass path is `confirmed` with all assertions ok, or the run ends in a declared non-pass outcome for a
    real reason.
B4. Run `run_suite.py specs/local/*.json --repeat 3 --workers 2` in the background. Read `results.json`.
    For every run that is not a unanimous pass, `summarize_trace.py <run dir>/trace.json --result` and
    classify with `references/verdict-rubric.md`: product bug, test issue (spec wording, missing `data`,
    threshold), runner defect, or flaky.
B5. For each **runner defect**, reproduce it offline first: a local fixture page in `selftest.py` (generic
    content) that fails the same way, then the fix, then the selftest green, one commit per defect.
    Typical suspects the demo could not exercise: settle ending `cap` on pages with timers, the
    adjudication line not offered on long pages, whole-document assertions vs. masked values,
    `stuck_reason` after a no-op click, options wait on real autocompletes, popups/new tabs.
B6. Re-run the suite after the fixes (background, `--repeat 3`) and record, generically, what changed.
    Do not commit `runs/`.
B7. Push block B (the fixes and their tests; the specs stay local).

### Block C — only if Fares says tokens or time matter (skip otherwise)

The contract costs ~74% more input tokens per run (handoff deviation 1). Measure each lever from a clean
export with `bench.py` (5 repeats, both smoke specs) before and after, keep it only if it wins, and if it
changes what the design spec prescribes (it says `blocked_reason` "always"), record the deviation in the
handoff and in `docs/superpowers/specs/2026-09-21-ultrafast-loop-and-results-contract-design.md` §5:
C1. ask `blocked_reason` only when Jev's operation is BLOCKED or WAIT;
C2. shorter `BLOCKED_REASONS` descriptions;
C3. send each adjudication line once (today `state.lines` and the criteria both carry them).

## 3. Non-negotiables (unchanged, plus the ones this round added)

- Stdlib + Playwright only. Every behavioural change lands with a selftest scenario or unit test; both
  suites green after every task. Keep the `run_test.run(spec, jev, out_dir)` seam and the fake Jev.
- Keep `spec.data`: Jev only chooses among prepared strings; a model answer is never a selector,
  coordinate or code. Targets are indices into the observed table.
- Never commit `.env`, `runs/`, `.venv/`, `.remember/`, `specs/local/`. No employer-specific content in
  tracked files, commit messages or measurement files (URLs, flows, company names, account handles).
- Every number in the docs comes from a committed `bench.py` / `run_suite.py` file taken from a clean
  export with `GIT_COMMIT` set.
- Small commits, one per task, push after each block. Implement directly; do not launch multi-agent review
  workflows. Live runs only where a block needs them; 5 repeats per spec is the ceiling for a measurement,
  3 for the real-app suite.
- Behaviour to keep in mind (handoff deviation 8): with a declared `outcomes` block `done_when` / `never`
  are inert, and a pass first seen on the budget's final look ends `budget_exhausted` with
  `reason.pending_outcome`.

## 4. When you finish (or stop)

Write `docs/superpowers/plans/<date>-handoff-after-real-app.md` in the shape of the current handoff:
state of the repo (test counts, HEAD), commits of the session, what the real app showed (generic), the
runner defects found and fixed, the ones left, and the numbers with their files. Push it. Report to Fares
in a few lines: what passed, what was found, what was left out and why.
