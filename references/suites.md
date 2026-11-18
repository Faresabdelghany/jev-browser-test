# Suites: anything longer than one spec

```bash
python $SKILL/scripts/run_suite.py specs/*.json --repeat 3 --workers 2   # -> runs/suite/<ts>/results.json + results.md
```

**How many at once.** `--workers` is the total; `--per-host` (default 2) is how many runs one host sees at a time,
whatever the total. A spec can lower its host's limit with `"host_limit": 1` (a host that hands out ids, or
answers a second visitor with timeouts; the smallest value among the host's specs counts), and
`--host-limit 'HOST=N'` sets it from the command line for a name or a pattern (`'*.staging.example.com=6'`), which
beats both. So for specs spread over several hosts, `--workers 6` is as safe for each host as `--workers 2`; the
suite takes as long as its slowest host's queue. For **an application you host yourself**, say so:
`--workers 8 --per-host 8` (or `--host-limit 'app.example.com=8'`), up to what the machine and the application's
own data allow; specs that create records need unique data (`${RUN_STAMP}`) before they can run side by side.
`results.md` names each host's limit, and `results.json` (`hosts`) the most runs each host saw at once.

Launch it with the Bash tool's `run_in_background` and **do nothing until the completion notification**. Then
read `results.md`: per spec the outcome distribution, the **agreement on verdicts** (two legitimate pass endings
agree), medians, and a suite verdict: one verdict everywhere → it; a spec with `expect` whose every run matched →
`expected` (green); any disagreement → **`flaky`**, computed, never diagnosed from one run. A start URL that never
loaded or a setup step that failed is listed as an environment/setup failure and kept out of the distribution.
Exit 0 iff every spec is `pass` or `expected`. Open a trace only for a spec that is `undetermined` or `flaky`.

`--sessions` logs in once per site and account: specs that keep their login in a `login` block reuse the session
the first of them saved (`spec-format.md`, "Sessions and the HTTP cache"). `--http-cache` keeps the browser's HTTP
cache between runs. Neither changes what a run decides; both shorten what happens before the first step.

`--replay` runs every spec with its saved path (`run_test.py --replay`, see `spec-format.md`, "Replay"): the suite
for reruns. The header of `results.md` then says how many runs walked their path to the end and how many handed over
to Jev on the way. A run that ends red after saved steps is run again at once without the path, and that second run
is the one in the table, so a saved path is never the reason for a red; the first is kept under the run's
`replay_attempt`, and `suite.replay.disagreed_specs` lists the specs where the two ended differently (an application
that varies, or a path that no longer fits: read both traces). `--replay-verify assert` passes the faster ending on.

`--junit runs/junit.xml` also writes the suite as JUnit XML for a CI dashboard, one test case per spec: `pass` and
`expected` are green, any other verdict is a `<failure>` whose type is the verdict (`bug`, `flaky`, ...) with every
run's outcome and evidence line, and a spec whose every run failed before observing a page is an `<error
type="environment">`, so an unreachable host is not painted as a product failure. `run_test.py --junit FILE` does
the same for one run.

When a suite reads `flaky`, say which kind: **environment** (load timeouts, stale pages, error runs) or **an app
that varies by design** (every run a confident declared outcome, different evidence lines: a random notification,
an A/B page). The second is not noise to retry away: if the spec asserts one ending of a legitimate variation, fix
the spec (`text_in` on the element accepting either message, or an either/or pass outcome); if the product's
contract forbids the variation, it is a BUG with a measured rate. Before spending browser runs on a page you
suspect is random, sample it without a browser: a loop of plain HTTP requests to the link's target shows a
server-side coin flip in seconds and costs the demo host nothing.

For a human reader (a PR, a ticket), `python $SKILL/scripts/report.py runs/<id>/<ts>` writes a self-contained
`report.html` beside the trace (step table, probabilities, checks, screenshots inline); given a suite directory
it writes one per run. Keep specs independent (each has its own `setup`). Keep `runs/` out of version control.
