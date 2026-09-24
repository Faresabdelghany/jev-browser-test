# Suites: anything longer than one spec

```bash
python $SKILL/scripts/run_suite.py specs/*.json --repeat 3 --workers 2   # -> runs/suite/<ts>/results.json + results.md
```

Launch it with the Bash tool's `run_in_background` and **do nothing until the completion notification**. Then
read `results.md`: per spec the outcome distribution, the **agreement on verdicts** (two legitimate pass endings
agree), medians, and a suite verdict: one verdict everywhere → it; a spec with `expect` whose every run matched →
`expected` (green); any disagreement → **`flaky`**, computed, never diagnosed from one run. A start URL that never
loaded or a setup step that failed is listed as an environment/setup failure and kept out of the distribution.
Exit 0 iff every spec is `pass` or `expected`. Open a trace only for a spec that is `undetermined` or `flaky`.

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
