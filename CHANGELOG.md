# Changelog

Notable changes to the jev-browser-test skill. Versions follow [semantic versioning](https://semver.org); the version
is the one in `.claude-plugin/plugin.json`, and merging a new one to `main` tags and releases it.

## [0.13.0] - 2026-11-17

Step 6 of the speed work: **one command for running specs again**, and the six steps measured together.

### Added
- **`scripts/rerun.py`**: `python scripts/rerun.py specs/` (spec files, folders of them, or an earlier suite's
  folder). Every spec once, with each spec's saved path (replay), a saved login for specs that share one, and four
  runs at a time inside the per-host limits. It prints a few lines and sets the exit code: `GREEN: N of N specs in
  T s ... Nothing to read.`, or one line per spec that is not green (verdict, outcome, the page's line, its run
  folder), then what changed since the last rerun of the same specs (remembered under `.jev/reruns/`) and what the
  replay did. The same lines are in `summary.md` beside `results.json` and `results.md`. A run that ends red after
  saved steps is run again without the path, so a red is always a run in which Jev chose every step.
  `--http-cache`, `--run-arg=--settle=network`, `--replay-verify assert`, `--no-replay`, `--no-sessions`,
  `--workers`, `--per-host`, `--host-limit`, `--repeat`.
- **SKILL.md sends a rerun there and tells Claude to stop reading**: for "run the suite again" the command's output
  is everything; a `result.json` is opened only for a spec that is not green, a trace only if that does not settle
  it.
- **Replay resumes after a handover when Jev's own decision is the saved step** (`result.replay.resumed`,
  `REPLAY-RESUMED`). A page that differs from the recording in something that does not change what to do (a widget
  that loaded earlier this time, one more button) used to hand the whole rest of the run to Jev; now Jev decides that
  step, and if it executes the saved operation on the control the path describes, the path goes on. Jev may take up
  to three other actions first (a banner to dismiss) before the path is given up for the run.

### Fixed
- After the last saved step the assertions were read from the live page a moment after the observation was taken:
  a loader that ended in between left Jev looking at "Loading..." while the assertions held, and the run handed over
  for nothing. The page is now settled and observed again once the assertions hold.

### Measured: the six steps together
Live `jev-1.14.0`, the 22 examples; "before" is 0.7.0, "rerun" is `rerun.py` with its defaults (replay and saved
sessions), "every option" adds `--http-cache --run-arg=--settle=network`. Ranges are the runs of two passes an hour
apart; the OrangeHRM demo alone moved a suite by up to 40 s between them.

| | before (0.7.0) | rerun | rerun, every option |
|---|---:|---:|---:|
| A simple flow again (`login-logout`) | 4.6 s, 6 requests | 3.5 s, 1 request | 2.3 s |
| `shop-checkout` again | 5.2 s, 10 requests | 2.9 s, 1 request | 2.0 s |
| `shop-checkout`, first run | 5.2 s, 10 requests | unchanged (the options are off) | 3.9 s, 8 requests with `--batch-fields --settle network --http-cache` |
| An OrangeHRM flow again (`hrm-pim-add-employee-list`) | 20.3 s, 18 requests | 14.7 s, 1 request | 13.8 s |
| Browser time per action on a fast page (median) | 146 ms | 151 ms | 103 ms |
| All 22 on one worker | 198 s | 136 to 159 s | 127 to 134 s (112 and 144 s with `--replay-verify assert`) |
| All 22 at the highest setting that respects the hosts | 135 s (2 workers, then the hrm specs on 1) | 71 to 81 s on 8 workers (116 s once, the demo's slow stretch) | 69 to 83 s (63 and 71 s with assert) |
| Jev requests for the suite | 194 | 44 to 49 | 26 to 30 with assert |
| Jev input tokens for the suite | 676k | 137k to 165k | 65k to 73k with assert |
| ... of which the specs that walked their path and passed | | 74k to 84k (one deciding request each) | 0 to 8k with assert |
| A new test through Claude (one agent, the sort-bug ticket) | 220 s, 104k tokens (the skill at 0.6.0, iteration 4) | 178 s, 130k tokens | |
| A rerun through Claude (one agent, eight specs) | 55.6 s, 74k tokens, 7 tool calls | 28.7 s, 68k tokens, 4 tool calls | |

The two rows through Claude are one agent run each. A rerun is twice as fast and reads one file where it read
five; its tokens barely move, because about 60k of either run is what an agent spends before it does anything
(its own instructions, and SKILL.md read whole). A new test took less time and **more tokens** than in September's
iteration: SKILL.md and the references grew with these six steps, and an agent writing a spec reads them. Nothing
in this release makes writing a new test cheaper for Claude.

**Targets, plainly.**
- *198 s to about 110 s on one worker: missed.* A rerun of the 22 takes 136 to 159 s on one worker, 127 to 134 s
  with the cache and the network settle as well. One run reached 112 s, with every option on and the assertions
  deciding the endings. What is left is the OrangeHRM specs (59 to 92 s for the five, most of it the application
  answering), browser launches and page loads; the requests are gone (194 → 45).
- *`shop-checkout` again in about 3 s: met.* 2.9 s with the rerun defaults, 2.0 s with every option.
- *Jev tokens near zero on green reruns: met only with `--replay-verify assert`* (0 to 8k for the specs that pass on
  their path). By default the ending of a replayed run is Jev's to decide, one request a spec, and that is 74k to
  84k tokens for 16 to 18 specs: an eighth of what the suite cost, not zero. The specs that do not end in a pass
  (two documented bugs, two expected-red, the random page that rolls its failure) are Jev's from the first step every
  time, 60k to 70k tokens whatever the options.

## [0.12.0] - 2026-11-17

Step 5 of the speed work: **parallel runs with a limit per host**.

### Added
- **`run_suite.py --per-host N`** (default 2) and **`--host-limit 'HOST=N'`** (a host name or a pattern, repeatable).
  `--workers` is now the total over all hosts; each host sees at most its own limit at a time, so the total can rise
  without any shared host seeing more load than before.
- **`host_limit`** in a spec lowers the limit for its host (the smallest value among the host's specs counts; a spec
  cannot raise it). The five OrangeHRM examples declare `"host_limit": 1`: one suite can now hold all 22 examples.
- A scheduler in place of the thread pool's queue: a free worker takes, among the jobs whose host has room, one from
  the host with the most work left per slot, so the host that will finish last never idles.
- `results.json` `hosts`: per host its limit, the most runs it saw at once, and how many specs it has; `results.md`
  names the limits in its header.

### Changed
- **`--workers N` alone no longer puts N runs on one host.** The default `--per-host 2` is what `--workers 2` used
  to protect a shared host with. For an application you host yourself, say so: `--workers 8 --per-host 8`, or
  `--host-limit 'app.example.com=8'` (`references/suites.md`).

### Measured
The 22 examples, once each, live `jev-1.14.0`, no other option on:

| | wall-clock | most runs at once on a host |
|---|---:|---|
| 0.7.0, its safe setting: the 17 public specs on 2 workers, then the 5 OrangeHRM specs on 1 | 38.9 + 96.5 = 135.4 s | 2; 1 |
| one suite, `--workers 8` | 105.4 s and 121.9 s (two runs) | 2 on the-internet and saucedemo, 1 on OrangeHRM, 1 elsewhere |
| one suite, `--workers 4` | 121.0 s | the same limits |

The whole suite now takes as long as its slowest host's queue: the five OrangeHRM specs, one at a time, were 96 s
on their own and 105 to 122 s with the other seventeen running beside them (the 17 alone take 24 s on 6 workers).
More workers cannot shorten that; shorter OrangeHRM flows can, which is what replay and saved sessions do. The
runs that were not green were the usual ones (the documented bug, the two random pages, `hrm-add-employee`'s first
field once) plus `toolshop-search-cart`, whose site answered "0 products found" for a product it has in every
run of that hour, before and after, and `hrm-leave-assign` once (`low_confidence` after 50 s in a slow stretch).

## [0.11.0] - 2026-11-17

Step 4 of the speed work: **log in once, keep the cache**. Both off by default.

### Added
- **`login`**: the scripted steps that only establish who is logged in, kept apart from `setup` (same actions, run
  before it). Without the option below nothing changes.
- **Saved sessions** (`--reuse-sessions`; `run_suite.py --sessions`; spec `"session": true`). The first run that
  logs in saves the browser's storage state and the page the login ended on to `.jev/sessions/<key>.json`; later
  runs of a spec with the same `login` on the same site start from it and skip the login. The session is checked
  before it counts: the page (the one the login ended on, or the page `setup`'s first `goto` names, which is then
  not loaded twice) must answer at its own URL shape and show what the login waited for; otherwise the session is
  deleted and the run logs in. The key covers the site's origin, the login as executed and the device; file names
  are HMACs under a per-directory key; the file holds cookies and localStorage, never what was typed.
  `"session": "never"` opts a spec out. `result.session`, `timing.login_ms`. What the application says to a session
  it no longer accepts (its "log in first" alert, its 404) is dropped with the session and never reaches the run:
  live, the shop's ten-minute cookie ran out between two suites, the alert reached Jev as an announcement on the
  first step after the fresh login, and two runs ended blocked on an application error that was not one.
- **An HTTP cache that outlives the run** (`--http-cache`, `browser.http_cache`). The browser runs on a profile
  under `.jev/http-cache/` from which everything but the cache folders is removed before each launch: the HTTP
  cache carries over, cookies, storage and service workers do not. One slot per concurrent browser.

### Changed
- Eight examples (the four shop specs and four OrangeHRM specs) keep their login in `login` instead of `setup`. The
  two specs that test a login (`hrm-login`, `login-logout`) have none and never reuse a session.

### Measured
Interleaved A/B, 3 runs an arm, live `jev-1.14.0`:

| | without | with |
|---|---:|---:|
| **Sessions**, 4 OrangeHRM specs: logins | 11.1 s | 0 |
| ... page load + login + setup, before the first step | 33.7 s | 21.9 s |
| ... wall-clock, sum of medians | 100.1 s | 95.6 s |
| **Sessions**, 4 shop specs: page load + login | 4.7 s | 2.9 s |
| **HTTP cache**, 17 public specs: page loads | 19.0 s | 7.7 s |
| ... wall-clock, sum of medians | 82.7 s | 69.5 s |
| **HTTP cache**, 5 OrangeHRM specs: page loads | 10.3 s | 4.5 s |
| ... wall-clock, sum of medians | 111.9 s | 108.2 s |

Verdicts: the same in every run of the public specs except the two random pages. On OrangeHRM the flows that
finished ended the same; three runs ended `employee_id_taken` (the demo answering "Employee Id already exists" for
the id it had pre-filled), all three in an arm with an option on, and `hrm-add-employee`'s first-field
`low_confidence` ended one run in each arm. Over the day's other A/Bs `employee_id_taken` ended runs without any
option too (twice), and nothing in a saved session or a cache touches how the demo hands out ids, so it is read as
the shared demo's; three against none in 54 runs is still worth saying.

The cache is the larger gain where pages are light and the host is slow to serve them (the-internet: 1.45 → 0.64 s
a load); a session is the larger one where the login is a slow application's (OrangeHRM: 2.4 to 3.8 s each). On
OrangeHRM the seconds saved before the first step are real, and the flow's wall-clock moves less than that because
the flows there vary by more from run to run.

Both stay opt-in for a single run. A first run should load the application as a visitor does, and a session file
is a logged-in browser on disk: neither should appear because nobody said no.

## [0.10.0] - 2026-11-17

Step 3 of the speed work: a **network-aware settle**. Off by default (`--settle network`,
`"browser": {"settle": "network"}`), and it stays off: it makes steps cheaper and decisions steadier, and it does
not make a slow application faster, which was the target.

### Added
- **`browser.settle: "network"`.** After an action the runner waits for the DOM to be quiet for
  `browser.network_quiet_ms` (50 ms), then for the requests the action started (XHR, fetch, a route's script and
  stylesheet), then for the DOM again, all inside `browser.settle_ms`. The requests are counted from the browser's
  own events; nothing is injected into the page. Not waited for: connections opened before the action (a long
  poll, a stream), sockets and event streams, images and fonts, and analytics or monitoring calls by name. A
  request that outlasts the cap ends the settle there and is reported: `settle.network` on the step has `requests`,
  `ms` and, when some were still in flight, `left`.

### Measured
Interleaved A/B (`ab.py --b-arg=--settle=network`, 5 runs an arm), all 22 examples, live `jev-1.14.0`:

| | 17 public specs | 5 OrangeHRM specs |
|---|---:|---:|
| Verdicts | the same (two random pages vary in both arms; one spec went undetermined once *without* the option) | the same flows pass; 2 undetermined runs without the option, 1 setup timeout with it |
| Browser time per action, median | 153 → 102 ms | 249 → 100 ms |
| Browser time per action, mean | 401 → 283 ms | 542 → 681 ms |
| Decisions gone stale under a moving page | 6 → 0 | 8 → 0 |
| Undecided (low-confidence) steps | 39 → 28 | 46 → 24 |
| Jev requests, sum of medians | 111 → 106 | 82 → 67 |
| Wall-clock, sum of medians | 83.6 → 78.5 s | 109.4 → 117.7 s |

The target was OrangeHRM "well under 560 ms per step". A step that fetches nothing (typing) now settles in about
100 ms there instead of 250; a step that loads something takes as long as the application takes to answer, and
that is most of the mean. The waiting moved (fewer WAITs, fewer refused decisions, fewer requests) and did not
shrink: **wall-clock on OrangeHRM did not improve**. On fast public pages it fell 6%.

Tried and dropped: asking Jev again after 300 ms instead of `settle_ms` when nothing is in flight. On OrangeHRM it
turned one spec's undetermined runs from 1 in 5 into 3 in 5 and saved no time (`references/runner-design.md`).

## [0.9.0] - 2026-11-17

Step 2 of the speed work: **one request per form**. Off by default (`--batch-fields`, `"batch_fields": true`), and
it stays off: the gain is real and small, and only on forms that do not react to typing.

### Added
- **One request per form.** On a page with two or more empty text fields, the request that decides the next action
  also asks, per field, which data value belongs in it (`fill_<index>`, a Choice over the data keys and
  `leave_empty`). After a TYPE_TEXT the runner types the other fields Jev assigned at `thresholds.batch_confidence`
  (0.8) or more, one step each and with no further request. The batch ends, and Jev decides again on the observation
  in hand, the moment the page reacts to what was typed: a toast or live message, a field or button that appears or
  goes, a covering layer, a list of suggestions, any change of the visible text. A value assigned to two fields is
  typed into neither, and a disagreement between Jev's two answers about the field it chose plans nothing.
  `step.fill` has every per-field answer, `step.batch_planned` the plan, batched steps are flagged `BATCHED` and a
  stopped batch `BATCH-ENDED`; `result.batch` counts both.

### Measured
First runs, interleaved A/B (`ab.py --b-arg=--batch-fields`, 5 runs an arm), the eight form-heavy examples, live
`jev-1.14.0`:

| spec (text fields) | verdicts | requests | wall |
|---|---|---:|---:|
| `shop-checkout` (3) | order_complete 5/5 both | 10 → 8 | 5.6 → 5.1 s |
| `shop-checkout-problem-account` (3) | form_error 5/5 both | 9 → 7 | 5.3 → 5.4 s |
| `shop-checkout-error-account` (3) | blocked 5/5 both | 10 → 8 | 6.2 → 5.4 s |
| `web-form-submit` (2, and a select, a checkbox, a radio) | form_submitted 5/5 both | 9 → 7 | 5.0 → 4.0 s |
| `login-logout` (2) | logged_out 5/5 both | 6 → 5 | 5.0 → 4.6 s |
| `hrm-add-employee` (2) | see below | 12 → 10 | 23.1 → 19.0 s |
| `hrm-pim-add-employee-list` (2, then a type-ahead) | employee_listed 5/5 both | 18 → 17 | 20.2 → 19.8 s |
| `hrm-admin-add-user` (a type-ahead, then 3) | user_listed 5/5 both | 20 → 21 | 29.0 → 31.2 s |
| sum of medians | | 94 → 83 | 99.5 → 94.4 s |

Jev's per-field answers were right in every run looked at: the sidebar's Search box and the optional middle name
read `leave_empty` at 0.96 to 1.0, the fields the goal names read their keys at 0.8 to 1.0. On the two forms with a
type-ahead the batch stopped where it should (the suggestion list, then a validation line) and nothing was saved;
there the extra questions cost about 9% more input tokens for no fewer requests. `hrm-add-employee` ended
`low_confidence` once in the batch arm of the first five; alone, ten runs an arm, it did so once in each arm
(employee_saved 8/10 without, 9/10 with): the spec's own base rate today, not the option's.

So: two requests and about half a second off a plain three-field form, nothing off a form that reacts, the same
verdicts. Worth turning on in a spec whose form is plain fields; not worth making every first run pay the extra
questions.

## [0.8.0] - 2026-11-17

The first of six steps to make reruns fast without making them less correct: **replay**. Off by default; measured
against the live Jev API (`jev-1.14.0`) on the twenty-two examples (the numbers and every run are on the `dev-docs`
branch, `docs/superpowers/measurements/README.md`, section "0.8.0").

### Added
- **Replay: a passing run saves its path, and the next run walks it without asking Jev.** `run_test.py --replay`
  (spec: `"replay": true`; `run_suite.py --replay`). A run that ends `passed` writes `.jev/paths/<id>.json`: per
  action the operation, how to find the target again (role, name, text, context, link target, test ids and stable
  `id` / `name`, never its number in the table), the *key* of the value typed, and a fingerprint of the page (the
  URL's shape, the title, the word-named fields and buttons that are not rows of a table). The next run executes
  those steps with no request, each only while the page matches its fingerprint and exactly one element answers the
  target's description; the page gets the time the recorded run took to arrive. On any mismatch Jev takes the run
  from that step, and a pass writes the path again. `references/spec-format.md`, "Replay".
- **The ending is never the replay's word.** After the last saved step one request asks Jev which declared outcome
  the page shows (checks and evidence line in the same request, no operation), and the assertions run as in any
  run. `--replay-verify assert` (`replay.verify`) lets a spec with assertions pass on them alone, with no request:
  as strong as the assertions are, so it is opt-in within the opt-in.
- **A red after saved steps is run again without the path** by `run_suite.py --replay`, and that second run is the
  result (`replay_attempt`, `suite.replay`): a saved path is never the reason for a red. A single run says the same
  in `result.replay.note`.
- `result.replay` (steps replayed, where Jev took over and why, how the ending was decided, whether the path was
  saved), `REPLAY-ENDED` / `REPLAY-VERIFY` and `saved path` in the summary, `at_ms` on every step.
  `"replay": "never"` keeps a spec out of `--replay`; `--replay-record` writes a fresh path; `--replay-dir`.
- A path holds no typed value: strings are written with the run's data values, run stamp and dates as tokens
  (`{{data:first_name}}`, `{{run_stamp}}`) and filled in from the run that replays. A path is dropped when the spec
  file changes in any way, when the device, viewport, frames, shadow DOM, extra operations or files differ, or when
  the path format does. `.jev/` writes its own `.gitignore`.

### Measured
Interleaved A/B (`ab.py --b-arg=--replay`, 3 runs an arm, one run at a time per host), all 22 examples, paths
recorded beforehand, commit `8d9c8c1`:

| | without replay | with replay |
|---|---:|---:|
| Verdicts | | the same in every run of 19 specs; the 3 that moved are the two pages that are random by design (both arms) and one Jev-driven run on the shared demo (no path existed yet) |
| Jev requests, sum of the specs' medians | 190 | 53 (1 on each of the 16 specs that end in a pass and have a path) |
| Input tokens | 674,879 | 171,590 |
| Wall-clock, sum of medians | 184.6 s | 150.8 s |
| `shop-checkout` | 5.2 s, 10 requests | 3.5 s, 1 request (3.1 s and none with `verify: "assert"`) |
| `web-form-submit` | 4.9 s, 9 requests | 2.6 s, 1 request |
| `hrm-leave-assign` | 27.9 s, 23 requests | 21.4 s, 1 request |
| The 22 as two suites on one worker | 198 s (0.7.0 release check) | 158 s, 44 requests; 143 s and 24 requests with `verify: "assert"` |

What replay does not shorten is what the suite mostly spends: browser launches, page loads, logins in `setup` and
the pages' own loaders (the two loader specs take 8 s with or without it). The five specs that do not end in a
pass (two documented bugs, two expected-red, and whichever random page loses the toss) save no path and cost what
they cost. Recording costs nothing measurable (a first run with replay on: 84.7 s against 83.9 s for the 17 public
specs).

Replay stays off unless asked for: it is for reruns, and a first run or a run under investigation should be Jev's
from the first step.

## [0.7.0] - 2026-11-17

Three follow-ups from the first live day (0.5.1, 0.6.0), each measured against the live Jev API (`jev-1.14.0`; the
numbers are on the `dev-docs` branch, `docs/superpowers/measurements/README.md`, section "0.7.0").

### Added
- **Date placeholders.** `${DATE}` is the day of the run; terms after it apply left to right (`+30d`, `-7d`,
  `+wed`, `+workday`, and the same with `-`) and an optional `:format` spells the date the way the application
  wants it (`yyyy` `yy` `mm` `m` `dd` `d` `mmmm` `mmm` `dddd` `ddd`): `${DATE+2d+workday:yyyy-dd-mm}`. Anywhere in
  the spec, like `${RUN_STAMP}`. `+workday` reads the new **`calendar`** field: `workweek` (Monday to Friday unless
  given) and `holidays` (`"12-25"` every year, `"2026-12-28"` one year). `RUN_DATE=yyyy-mm-dd` in the environment
  pins the day; `spec.py` prints what each placeholder becomes; the trace has `spec.run_date` and `spec.dates`. A
  placeholder that cannot be read is a spec problem (exit 2), never text for the page. `${DATE}` is no longer read
  from an environment variable of that name; `${DATE_FROM}` and every other name still are.
- **`ab.py --a-runner <another checkout's run_test.py>`**: the A/B for two versions of the runner, so a change to
  the observer is measured the way an option is.
- **`reason.hints`** in `result.json`: for a stalled run, where the last page keeps controls the spec did not let
  the observer look at (an `<iframe>` not in `observation.frames`, shadow DOM turned off, a file field without
  `files`). The sentences the summary already printed as `hint:`.

### Fixed
- **`hrm-leave-assign` no longer goes red when its date has passed.** It typed a literal date, and a leave on a
  day that has passed is listed as Taken, not Scheduled: the first literal made the spec red in October, its
  replacement would have on 17 December. The date is now `${DATE+2d+workday:yyyy-dd-mm}` with the demo's sixteen
  holidays in `calendar`. Live: passes today (twice) and with `RUN_DATE=2026-12-17`. A first version, thirty days
  ahead, failed when pinned to 17 December: the leave fell in January and the demo's Leave List shows the current
  leave year only. Two days ahead leaves the last two to four days of December as days the spec cannot pass.
- **Shadow DOM: a control whose caption is drawn from another tree is named by it.** At 0.6.0 the Polymer shop's
  product links and MDN's Copy, Reset and Log in buttons reached Jev as `link ""` and `button ""`: `innerText`
  reads neither a nested shadow root (`<a><shop-list-item></a>`) nor a slot (`<button><slot></slot></button>`
  inside `<mdn-button>Copy</mdn-button>`). The name now follows the tree as it is rendered. What sits inside a
  link across a shadow boundary is the link, not entries of its own (the shop's list page: 17 entries with 7
  unnamed, now 10 with none; MDN: 13 unnamed, now 1), and a button is not counted as covered by a caption element
  slotted into it. A control whose content is all in its own tree is named as before: on the example specs' 15
  start pages the observation is identical before and after. A/B against the previous runner, interleaved: a flow
  that needs MDN's Copy button **1/5 before, 5/5 after** (confidence 0.35 / 0.89, 5 / 3 requests); the Polymer shop
  purchase 5/5 both; MDN's table-of-contents flow 15/15 both. The cost that was measured: on MDN Jev's confidence
  on the looks after the goal is reached fell (0.60 to 0.47 over 10 runs an arm, the click itself 0.99 in both),
  and on the shop the first click's target confidence fell from 0.97 to 0.80-0.85, because the category's image
  link now carries the same name as its Shop Now link. No ending, request count or action moved.
- **A stalled run that could not find its control on a partly unobserved page suggests `test_issue`, not `bug`.**
  Live, the Polymer shop with shadow DOM off: `low_confidence`, `control_not_on_page`, suggested verdict `bug`,
  beside a hint that named the option. With `reason.hints` present and `control_not_on_page` as the deciding
  reason the suggestion is now `test_issue` (`reason.suggestion_from: "hints"`). Every other reason keeps its
  suggestion: most pages have an `<iframe>` somewhere.

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
- **An undecided streak does not end the run on a page that moved while Jev decided.** Live, 0.6.0 suite:
  `dynamic-controls`' loader ended in the ~0.3 s between the third undecided observation and the loading-indicator
  check; the check found nothing, the limit fell from five looks to three, and the run ended `low_confidence` on a
  finished page. Before stopping, the runner now re-reads the page; if it changed, the count starts again
  (`step.moved_while_deciding`). Selftest G2.
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
