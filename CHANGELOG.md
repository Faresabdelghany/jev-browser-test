# Changelog

Notable changes to the jev-browser-test skill. Versions follow [semantic versioning](https://semver.org); the version
is the one in `.claude-plugin/plugin.json`, and merging a new one to `main` tags and releases it.

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
