# Changelog

Notable changes to the jev-browser-test skill. Versions follow [semantic versioning](https://semver.org); the version
is the one in `.claude-plugin/plugin.json`, and merging a new one to `main` tags and releases it.

## [0.6.0] - 2026-11-17

The defaults for 0.5.0's three Jev-driven options, decided from live A/B runs (the protocol and every number are on
the `dev-docs` branch, `docs/superpowers/measurements/2026-11-17-*`), and two defects the live runs of HOVER and
UPLOAD_FILE found.

### Changed
- **`observation.shadow_dom` is on by default** (`false` or `--no-shadow-dom` for the way back; `scaffold.py
  --no-shadow-dom`). The 22 example specs x 3, interleaved: no example page has a shadow root, the two arms' first
  observations are identical wherever the host was stable, nothing moved in every run. Where it matters it decides
  the run: the Polymer shop (controls in nested shadow roots) stalls without it and passes with it; on MDN, whose
  content sits in web components, a light-DOM flow passed 0/5 without and 5/5 with, confidence 0.53 / 0.56. Cost:
  ~12 ms more per observation on a page with 121 shadow hosts. The equivalence 0.5.0 claimed ("a spec that does not
  ask is sent what 0.4.0 sent") now holds for pages without open shadow roots only.

### Fixed
- **HOVER waits for a menu that opens after a delay.** jQuery UI opens a submenu 300 ms after the pointer arrives;
  the settle went quiet at ~110 ms, every hover was flagged `NO-EFFECT` and Jev was told it changed nothing. A hover
  now waits up to 800 ms for the page to change (`executed.reveal`). Live after: HOVER, CLICK, pass, 5/5.
- **Uploads: a drag-and-drop library's orphan file input is not offered beside a real file field.** On
  the-internet's /upload both inputs read `file "file"`, the orphan sorted first and Jev chose it (an empty form,
  500). A boxless file input with no label, no form and no rendered owner is now offered only when the page has no
  other file field, then marked `not in a form or a label`. Live after: 'File Uploaded!'.

### Measured and kept
- **HOVER stays opt-in.** On the 22 examples x 5 Jev never chose it (top probability 0.10), no ending moved, no
  confidence fell, and it cost **+14.6% input tokens** on every step (the `hover_target` question). A spec with a
  hover-only menu turns it on with one line.
- **`evidence` stays `"always"`.** `"failures"` saved 10.5% of requests (one per pass) and 7.4% of tokens, no
  measurable wall-clock (host noise is larger), and costs the quoted line on every pass. Use it on green-most-days
  suites.

## [0.5.1] - 2026-11-17

The first runs of 0.3.0 to 0.5.0 against the live Jev API (the smoke specs, the 22 examples x 3, `dynamic-controls`
x 5). No verdict moved because of the runner: the September runner (`28a5506`) reproduces, request for request, the
two runs that changed. Four example specs no longer matched what their demo sites do, and one 0.4.0 feature failed
on its first real page.

### Fixed
- **Frames: a listed one-line `<iframe>` is observed.** `observation.frames` skipped any frame under 40 x 20 px as
  "not visible"; Stripe's card element is one line in an iframe 323 x 18 px, so a payment form's card field, the
  case the option exists for, contributed nothing. The floor is 10 x 10 (a tracking pixel), and a frame below it says
  so (`smaller than 10 x 10 px`). Live after the fix: Jev typed the number, expiry and CVC into the cross-origin
  frame at 0.75-1.00. Unit test and selftest D2.

### Changed (example specs)
- `dynamic-controls`: the redesigned demo has one message line, so 'It's gone!' is replaced by 'It's enabled!'; the
  pass is worded on the finished page and the removal asserted by the checkbox's absence and the Add caption.
  5/5 after (3/3 `done_unverified` before, every run's flow identical). The 0.4.0 loading-indicator rule fired in
  all five (`LOADING-IND`), one run on three undecided looks in a row that used to end `low_confidence`.
- `forgot-password`: the demo no longer answers 500; `expect: server_error` removed, the spec is a pass.
- `modal-close`, `add-remove-elements`: the pass needs the flow's own click (`after: Close` / `after: Delete`);
  both had passed by a shortcut (no action; one Add instead of two and a Delete).
- `hrm-leave-assign`: the leave date had passed (listed Taken, not Scheduled); now 2026-16-12.

## [0.5.0] - 2026-11-16

Jev can now drive the three interactions 0.4.0 could only script. Each is **off until the spec asks**: a spec that
does not ask is sent the questions and the observation it always was (compared field by field against 0.4.0 on 80
page states: identical).

### Added
- **Shadow DOM: `observation.shadow_dom`** (`--shadow-dom`). The controls and the text inside open shadow roots,
  nested ones included, are observed like the rest of the page; Jev types and clicks there; the evidence line and
  the assertions read there too. A page without shadow DOM is observed exactly as before with it on.
- **Uploads: `files`.** `{"cv": "fixtures/cv.pdf"}` offers the operation `UPLOAD_FILE` wherever the page has a file
  field, including one hidden behind a styled button. Jev picks the field and the file's name; only the name reaches
  Jev, never the path. A field that holds a file reads `(file: cv.pdf)`.
- **Hover: `extra_operations: ["HOVER"]`** (`--hover`). Jev may hover a link, button, tab or menu item to open a menu
  that only shows on hover, then click what it reveals.
- **`scripts/ab.py`**: runs a set of specs with and without an option, interleaved so both arms see the same hour of
  a shared host, and reports per spec whether the ending moved and whether decisions got less certain. It is how
  "could this be the default" gets answered.
- **`evidence: "failures"`** (`--evidence failures`): a pass whose assertions all hold is not asked for its evidence
  line, which saves one Jev request on every such pass (three requests become two on the simplest flow). Anything
  red, and a pass with no assertions, still gets its line. Off by default.
- **A `Live` workflow** (`.github/workflows/live.yml`): runs a plan (`.github/live/plan.sh`) against the real Jev API
  on GitHub's runners when a `live/<name>` branch is pushed, using the repository secret `TYPESAFE_API_KEY`, and
  publishes the summaries to the `live-results` branch. Without the secret it runs nothing.
- `scaffold.py --file KEY=PATH / --hover / --shadow-dom`; a stalled run on a page with an unused file field says so.
- Offline scenarios J, K, L, M in `selftest_capabilities.py` and 12 more unit tests (174).

### Changed
- With `files` declared, a file field is an upload target and no longer a click target (a click would open a system
  dialog nothing in the run can answer). Without `files` nothing changes.

### Not in this release
- **None of the three was run against the live Jev API.** Offline, a scripted stand-in chooses HOVER and UPLOAD_FILE
  when they are offered; whether Jev does, and what offering HOVER costs the steps that do not need it, is what
  `ab.py` and the experiment specs on the `dev-docs` branch are for.
- Drag and drop is still scripted only. Closed shadow roots, and toasts announced inside a shadow root, are not seen.

## [0.4.0] - 2026-11-16

No existing spec changes behaviour: every new capability is a new field or flag, off until a spec uses it, with two
exceptions that only add information (browser diagnostics are always recorded, and a page with a loading indicator
gets two more undecided looks before `low_confidence`).

### Added
- **Browser diagnostics.** Every run records uncaught JavaScript exceptions, `console.error` messages, failed
  requests and 4xx / 5xx responses, each with the step it preceded: `trace.diagnostics`, a short `result.diagnostics`,
  and the flags `JS-ERROR`, `HTTP-5xx`, `HTTP-4xx`, `REQ-FAILED`, `CONSOLE-ERR` in the step table. Nothing reaches Jev.
  Two assertions make them part of a pass: `{"no_page_errors": true}` and `{"no_failed_requests": true}`.
- **`teardown`.** Scripted steps after the verdict, whatever it was, to delete what the run created. Best effort:
  a failing step is reported in `result.teardown` and never changes the outcome, the verdict or the exit code.
- **Scripted steps for what Jev is not offered:** `upload`, `hover`, `check` / `uncheck`, `drag`, and `"frame"` on any
  step to act inside an iframe. Selectors reach into open shadow roots.
- **Frames.** `observation.frames` lists the iframes whose controls join the element table, so Jev can fill a card
  form or an embedded widget; `text_in` takes `frame`. Unlisted frames contribute nothing.
- **Device emulation.** `browser.device` / `--device "iPhone 13"`: a phone's viewport, touch and user agent.
- **New tabs.** `browser.follow_new_tabs` carries the run on in a tab the flow opens; without it the step is flagged
  `NEW-TAB(not followed)`.
- **JUnit output.** `--junit FILE` on `run_suite.py` and `run_test.py`: a pass is green, a verdict is a `<failure>`
  typed by it (`bug`, `flaky`, ...), an environment problem is an `<error>`.
- **Windows.** The scripts run there: UTF-8 output whatever the console's code page, portable file URLs in the
  self-test, `SKILL.md` pre-approves `.venv/Scripts/python.exe` too, and CI runs on `windows-latest`.
- `scaffold.py --teardown / --frame / --device / --follow-new-tabs`, and the new steps in `--setup`.
- A stalled run on a page with an unlisted iframe, or with controls inside shadow DOM, says so under its step table.
- `selftest_capabilities.py`: an offline scenario for each of the above (run by `selftest.py`), and 19 more unit tests.

### Changed
- **Loading indicators that cover nothing** (a spinner, an indeterminate progress bar, a 'Loading...' line) earn an
  undecided look the two extra turns a blank loading layer already got, and nothing else: no deferral, no longer
  confirmation. Open item 1 of the 2026-09-24 handoff; flag `LOADING-IND`.
- Screenshot paths in a trace are `steps/NNN.png` on every operating system.

### Not in this release
- Controls inside shadow DOM, file inputs, hover menus and drags are still not offered to **Jev**; they are
  scripted. Frames are opt-in per frame, and the evidence line is quoted from the main frame.
- None of this was run against the live Jev API: the offline self-test drives the runner with a scripted stand-in.

## [0.3.0] - 2026-11-16

### Added
- `LICENSE`: the skill is MIT-licensed.
- This changelog, and a release workflow that tags `v<version>` and publishes a GitHub release when `main` carries a
  version that has no tag yet.
- CI on every push and pull request: the unit tests on Linux and macOS (Python 3.10 and 3.13), the offline self-test
  with a real Chromium, and a check that `plugin.json`, `marketplace.json` and this file name the same version.

### Changed
- **The install is about 1 MB, was 4.3 MB.** `docs/` (design notes, session handoffs, measurements) and `evals/` moved to
  the [`dev-docs`](https://github.com/Faresabdelghany/jev-browser-test/tree/dev-docs) branch; `main` keeps what the
  skill needs at run time. The README says how to check that branch out beside the skill.
- **`SKILL.md` is 15% shorter** (3,330 words, was 3,910), with no instruction dropped: the full flag glossary now
  lives in `references/verdict-rubric.md`, the long-page and type-ahead recipes in `references/spec-format.md`, and
  the triage section points at the rubric's own instead of repeating it.
- `run_suite.py` starts 2 workers by default (was 4), the most `SKILL.md` allows against a shared host. Pass
  `--workers N` for an application you host yourself.

### Fixed
- `selftest.py`'s remote-debugging scenario starts its hand-launched browser without the sandbox, as Playwright does
  for every browser it launches itself: with it, Chromium does not start as root (a container) or on GitHub's Ubuntu
  runners, and the scenario failed there.

## [0.2.0] - 2026-09-24

The state of `main` at commit `28a5506`, before versions were tagged.

- The results contract: a spec declares its outcomes with their verdicts, a run returns exactly one of them with the
  page's own line as evidence, or `undetermined` with a typed reason and a suggested verdict (`result.json`).
- `scaffold.py` (URL + goal + data → a valid spec), `run_suite.py` (specs × repeats, a computed `flaky` verdict),
  `report.py` (a self-contained `report.html`), `bench.py`, the offline `selftest.py` and 142 unit tests.
- Speed: one Jev request per decision, a pre-connected client, waits that end when the page changes, a pass confirmed
  by its assertions in code.
- The observer: below-the-fold controls, icon-only controls named from their class, identical labels told apart by
  their card or row, blank loading layers told from dialogs, autocomplete loading rows, toasts and ARIA live
  messages recorded as evidence.
- `${RUN_STAMP}` for data the application keeps, `--headed` / `--headless`, attaching to a running browser over CDP.
- Twenty-two example specs against public sites, and the install formats (personal skill, project skill, plugin).
