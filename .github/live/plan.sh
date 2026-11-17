#!/usr/bin/env bash
# What the Live workflow runs. Edit this on a live/<name> branch and push it: the branch is the measurement.
# $OUT takes everything the commands write; .github/live/publish.py then picks what goes to the live-results branch.
# A command that ends non-zero (a red run, a moved A/B) must not stop the plan: the results are the point.
set -u

# The default plan: is the runner alive against the real API? The two smoke specs, once each.
python scripts/run_suite.py specs/smoke-login.json specs/smoke-login-badpw.json --workers 1 --out "$OUT/smoke" --junit "$OUT/smoke/junit.xml" || true
