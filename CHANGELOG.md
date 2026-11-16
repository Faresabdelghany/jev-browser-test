# Changelog

Notable changes to the jev-browser-test skill. Versions follow [semantic versioning](https://semver.org); the version
is the one in `.claude-plugin/plugin.json`, and merging a new one to `main` tags and releases it.

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
- `scaffold.py --file KEY=PATH / --hover / --shadow-dom`; a stalled run on a page with an unused file field says so.
- Offline scenarios J, K, L in `selftest_capabilities.py` and 11 more unit tests (173).

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
