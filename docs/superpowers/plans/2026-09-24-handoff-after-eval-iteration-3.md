# Handoff after skill eval iteration 3 and the observer changes (2026-09-24, 15:24–16:45)

Fares: "can we go on with this and update readme file in github, make it simple, same as any skill". Both done: the
README is 116 lines (was 255; the examples table moved to `specs/examples/README.md`), and the skill eval ran with three
new prompts, whose findings became two runner commits and a full suite. Start with `git pull` (main is at this branch),
then the measurements README section "Skill eval iteration 3 and the observer changes".

## Commits on badlands-saguaro (main fast-forwarded, pushed; `~/Downloads/jev-browser-test` pulled; the skill symlink points there)

- `d30a966` README cut to a skill's README; `specs/examples/README.md`; evals 3–5 under `evals/` (the triage run folder
  `evals/files/triage-unverified-save/run`, the sign-up page `evals/files/fix-loop-signup/app` with its inverted e-mail
  rule in `app.js` line 22).
- `103c62f` from evals 4 and 5: scaffold `--bug name=statement`, `--after click:Text`, `--comment`; the secrets sentence
  on invented passwords; `NO-EFFECT IN-FLIGHT` in the summarizer; `result.reason.assertions_at_last_look` /
  `last_look_step` for `done_unverified`; SKILL.md (a local app's server, `(not run)` / `AUTO_DONE`, a fix shown twice,
  the control for timing questions); troubleshooting rows; `hrm-add-employee` keeps its last name unique.
- `b92b24f` from eval 3: form controls and buttons below the first screen offered marked `(below the fold)` (twelve at
  most, over the table's budget, no hit test); icon-only controls named from their class; layer controls counted only
  over the covered region (a fixed top bar above a full-page loader is blank); SCROLL_DOWN's wheel fallback
  (`executed.scroll`); `--slow` 40/480; `--step N` prints tag and position for unnamed elements; a
  `suggestion_not_found` outcome in the two autocomplete examples; selftest fixtures (`?header=1`, `?sibling=1`, the
  controls page's icon span and below-fold textarea/button/link, the wheel fallback); unit tests 142, SELFTEST OK.
- `152a7f5` `hrm-admin-add-user`'s sidebar sentinel is `a[href*="/admin/"]` (was the Leave link); runner-design on the
  observer changes.
- the docs commit after it: the measurements (three suite results), this handoff.

## The eval round (with-skill arm only, `iteration-3/`, viewer server on port 3118 (`viewer.pid`), `review.html` static)

| eval | result | tokens / time | what it asked of the skill |
|---|---|---|---|
| 3 slow-spa-candidate-search | 10/11 (8/11 as first written: the flow does not pass on the demo, BUG with a probe) | 198k / 23 min, 3 runs + 2 probes | below-fold controls, icon names, no 'no suggestion came' ending, the top bar read as a dialog |
| 4 triage-unverified-save | 11/11, FLAKY/environment after one control | 135k / 11 min | a control for timing questions, a done_unverified row, the last look's assertions in result.json, NO-EFFECT in flight |
| 5 fix-loop-signup | 9/11 (no malformed-e-mail check after the fix; secrets removed on an invented password) | 97k / 6 min, 2 runs | scaffold --bug name=, --after, --comment |

Everything the three agents asked for is in `103c62f` and `b92b24f` except: a `--project` / `--env-file` option so one
command matches the pre-approved `allowed-tools` line (SKILL.md now says to `cd` once instead), the observer naming an
unnamed control from its position in `--step N` (done) and a loading indicator that is not a layer (below).

## Results after the runner changes (all under `docs/superpowers/measurements/`)

- Seventeen non-OrangeHRM at `b92b24f`: no verdict moved except `dynamic-controls`, 1/2 then 2/3 on rerun: Jev hovers
  undecided while the Remove loader runs (text and a bar, not a layer), and once clicked Enable before it ended, which
  wipes 'It's gone!' from the finished page. Three navigation timeouts on the-internet (slow hour).
- OrangeHRM: 9/9 at `b92b24f` for the three unseeded specs; the two seeded ones failed their setup 6/6 because the
  demo's Leave module had been switched off by a visitor (restored: Admin > Configuration > Modules); 6/6 at `152a7f5`.

## Open

1. **A loading indicator that is not a layer** (`role=progressbar`, id/class loading / spinner / progress, the visible
   'Wait for it...' / 'Loading...' text) should count as `page_loading`, so undecided looks get the extra turns they get
   under a blank layer. Evidence: `2026-09-24-dynamic-controls-b92b24f-rerun` run 1 (three undecided looks in 6.8 s).
   Check the selftest's loading fixture scenarios (4d, 4e) before changing it: they pin the WAIT behaviour on a loader.
2. `dynamic-controls`' pass wording claims both messages; Enable clicked before the Remove loader ends leaves only 'It's
   enabled!' on the page. Either word the pass on the buttons' captions (Add, Disable) plus 'It's enabled!', or keep the
   spec as the example of a marginal wording and let the suite show it.
3. The public demo's modules can be switched off by anyone; a seeded setup that waits on a module link then fails 3/3.
   The admin spec no longer depends on Leave; `hrm-leave-assign` needs the module and says so in its failure (exit 2,
   `phase: setup`). If it fails that way again, look at the sidebar first.
4. The eval's three prompts are at 30/33; a further round wants prompts probed against the live site before the
   assertions are written (eval 3's PASS premise was wrong), and is Fares's call.
5. `~/Downloads/jev-browser-test-<sha>.skill` for Claude Desktop is written at the end of this session.
