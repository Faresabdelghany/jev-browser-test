# Deciding the defaults for shadow DOM, uploads and hover (written 2026-11-16, for a session with a TypeSafe key)

Pull request #3 (0.5.0) lets Jev drive three things it could not: controls inside shadow DOM
(`observation.shadow_dom`), file uploads (`files` → `UPLOAD_FILE`) and hover menus (`extra_operations: ["HOVER"]`).
All three are off unless a spec asks. This note is how to find out, with the key, (1) whether Jev actually uses them
and (2) which of them could be on for every spec. Nothing below was run: the session that wrote it could reach
neither the API nor the demo sites.

Run everything from the dev-docs worktree's parent, i.e. a clone of main with this branch at `dev/`
(`git worktree add dev origin/dev-docs -B dev-docs`), with `python` the skill's interpreter.

## What is already settled without a key

| | Asked of a spec that does not opt in | Why |
|---|---|---|
| shadow DOM | nothing new | with the flag off every query is the document-only call it was; the observation was compared field by field with 0.4.0's on 80 page states: identical |
| shadow DOM, flag ON, page without shadow roots | nothing new either | the same comparison with the flag on: identical. So the flag can only change a run on a page that has open shadow roots |
| uploads | nothing new | `UPLOAD_FILE` and the hidden file inputs appear only when the spec declares `files` |
| hover | nothing new | `HOVER` appears only when the spec lists it |

So only two questions need Jev: does it choose the new operations sensibly, and what does offering HOVER on every
step cost a flow that never hovers. The second is the same question the standing rules failed (median operation
confidence 0.95 → 0.50–0.57, `2026-09-22-track1-ab-*`).

## Step 1: shadow DOM as a default (about 35 minutes, ~130 runs)

```bash
python scripts/ab.py specs/examples/*.json --b-arg=--shadow-dom --repeat 3 --out runs/ab/shadow
grep -l '"shadow_hosts"' runs/ab/shadow/*/a*/trace.json     # which example sites have shadow-DOM controls at all
```

Run the `hrm-*` specs in a normal hour; `ab.py` is sequential, so the one-worker rule is kept. If the `grep` finds
nothing, no example page has controls in shadow DOM and arm B was sent byte-identical requests: any difference
between the arms is the host's noise, and **`shadow_dom` can default to true** (one line in `spec.DEFAULTS`, and
`--no-shadow-dom` for the way back). If it finds some, those specs are the interesting ones: read their two traces
side by side at step 1 (`summarize_trace.py ... --step 1`).

## Step 2: hover as a default (about an hour, ~220 runs)

```bash
python scripts/ab.py specs/examples/*.json --b-arg=--hover --repeat 5 --out runs/ab/hover
```

Read `runs/ab/hover/ab.md`. The decision:

| ab.md says | then |
|---|---|
| no spec moved, no confidence fell (no ⚠) | HOVER can be offered by default; do it in its own commit and rerun the examples suite once |
| confidence fell on some specs, endings unchanged | keep it opt-in; the fall is the cost, and a spec pays it only when it asks |
| a spec moved in every run | keep it opt-in, and open that spec's two arms at the step where arm B chose HOVER: the description in `policy.OPERATION_DESCRIPTIONS["HOVER"]` may be drawing it ("to reveal a menu" reads as an invitation on a page with a nav bar) |
| a spec moved in some runs | rerun that spec alone, `--repeat 10`, before reading anything into it |

My expectation, for what an untested expectation is worth: HOVER stays opt-in. An operation that applies to every
link on every page competes with CLICK on every step.

## Step 3: does Jev use them (about 10 minutes)

```bash
python scripts/run_test.py dev/experiments/jev-driven/upload-file.json --screenshots all     # from the clone's root: adjust the file path, or cd dev
python scripts/ab.py dev/experiments/jev-driven/hover-menu.json --a-arg=--screenshots=all --b-arg=--screenshots=all --repeat 5   # see below
```

- **upload-file** (the-internet `/upload`). Pass = step 1 is `UPLOAD_FILE` into the form's field with `<- file sample`,
  then `CLICK` Upload, `File Uploaded!`. The page has a second, hidden file input (the drag-and-drop library's): if
  Jev picks that one the run ends `server_error` (declared, a test issue): that is the finding, and the fix to try
  is in the observer (name a hidden input from the element that owns it) before it is in the spec's notes.
- **hover-menu** (the-internet `/jqueryui/menu`). The spec lists HOVER itself, so to compare with and without it copy
  the spec without `extra_operations` and run both, or use `ab.py` on the copy with `--b-arg=--hover`. Both arms may
  pass: this menu also opens on click. What to read is whether arm B's first action is HOVER on Enabled and whether
  it costs steps.
- **shadow DOM**: no spec is written, on purpose. I know of pages that keep their controls in open shadow roots
  (the Polymer shop demo at shop.polymer-project.org, the books demo at books-pwakit.appspot.com, the practice page
  at practice.expandtesting.com/shadowdom) but could not open any of them, and eval 3 showed what a spec written
  from memory is worth. Probe first: scaffold a spec for one of them with `--shadow-dom`, run it once with a
  two-step budget, and read the table (`summarize_trace.py <trace> --step 1`): the controls inside the components
  should be listed with their labels, and none flagged `COVERED`. Then write the outcome from what the page says.

Both experiment specs were written from memory of those pages. Treat their outcomes as drafts until one run each
has been read.

## After the measurements

- Record the `ab.md` files under `docs/superpowers/measurements/` with the commit they were run at.
- If a default flips, the self-test's equivalence claim changes with it: say so in the changelog.
- Still not Jev-driven: drag and drop (scripted `drag`), and hovering over something that is not a control (an
  avatar image with no role or pointer cursor is not in the table, so it cannot be a `hover_target`).
