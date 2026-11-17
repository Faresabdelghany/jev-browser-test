# A/B: --shadow-dom

1 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--shadow-dom`. 2026-11-17T12:24:36

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x1 (+2 environment) | no | 0.88 | 0.84 | -0.035 | 27 / 31 | 75.4 / 85.7 |

**0 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it the default, as strong as the specs are varied and the repeats many.
