# jev-browser-test: development material

This branch holds what the skill's users do not need at run time, so that `main` stays small:

- `docs/superpowers/`: the design spec, the session plans and handoffs, and every measurement file
  (`docs/superpowers/measurements/README.md` says how each number was produced).
- `evals/`: the skill's eval prompts (`evals/evals.json`) and their input files.

It was split from `main` at commit `28a5506` (2026-09-24); the earlier history of these files is in `main`'s log.

## Working with it

Check it out beside the skill as a second worktree, so both are on disk at once:

```bash
cd jev-browser-test                       # your clone of main
git fetch origin dev-docs
git worktree add dev origin/dev-docs -B dev-docs    # -> ./dev/docs, ./dev/evals (dev/ is git-ignored on main)
```

Commit measurements, handoffs and eval changes here (`cd dev && git add ... && git commit && git push`), and code,
specs and references on `main`. The eval prompts name their input files as `evals/files/...`: run them from the `dev`
directory, or prefix the path with `dev/`.
