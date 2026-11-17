#!/usr/bin/env bash
# live/01-sanity: is 0.5.0 alive against the real API, and what do the example sites look like to it?
# 1. the two smoke specs; 2. the examples suite once, one worker (the hrm-* specs need that); 3. the two experiment
# specs for UPLOAD_FILE and HOVER from the dev-docs branch; 4. which example pages have iframes or shadow-DOM controls.
set -u
python scripts/run_suite.py specs/smoke-login.json specs/smoke-login-badpw.json --workers 1 --out "$OUT/smoke" || true
python scripts/run_suite.py specs/examples/*.json --workers 1 --out "$OUT/examples" --junit "$OUT/examples/junit.xml" || true

git fetch -q --depth 1 origin dev-docs && git worktree add -q "$RUNNER_TEMP/dev" FETCH_HEAD
mkdir -p "$OUT/keep"
for name in upload-file hover-menu; do
  (cd "$RUNNER_TEMP/dev" && python "$GITHUB_WORKSPACE/scripts/run_test.py" "experiments/jev-driven/$name.json" --screenshots all --out "$OUT/exp-$name") || true
  mkdir -p "$OUT/keep/exp-$name" && cp -r "$OUT/exp-$name/." "$OUT/keep/exp-$name/" 2>/dev/null || true   # the trace and every picture, green or not
done

python - <<'PY'
import glob, json, os
out = os.environ["OUT"]
rows = []
for path in sorted(glob.glob(os.path.join(out, "**", "trace.json"), recursive=True)):
    try:
        t = json.load(open(path, encoding="utf-8"))
    except ValueError:
        continue
    steps = t.get("steps") or []
    flags = {k: max((s.get(k) or 0) for s in steps) if steps else 0 for k in ("shadow_hosts", "iframes", "loading_indicators", "covered_controls")}
    diag = (t.get("diagnostics") or {}).get("counts") or {}
    rows.append(f"{os.path.relpath(os.path.dirname(path), out)}\t{t.get('status')}\tshadow_hosts={flags['shadow_hosts']}\tiframes={flags['iframes']}"
                f"\tloading_indicators={flags['loading_indicators']}\tcovered={flags['covered_controls']}\tdiagnostics={ {k: v for k, v in diag.items() if v} }")
open(os.path.join(out, "keep", "observations.tsv"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("\n".join(rows))
PY
