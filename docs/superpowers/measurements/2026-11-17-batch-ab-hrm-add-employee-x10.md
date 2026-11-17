# A/B: --batch-fields

1 spec(s) x 10 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--batch-fields`. 2026-11-17T17:11:06

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x8, undetermined:low_confidence x1, employee_id_taken x1 | employee_saved x9, undetermined:low_confidence x1 | some runs | 0.85 | 0.69 | -0.160 ⚠ | 13 / 13 | 18.6 / 23.4 |

**0 spec(s) ended differently in every run, 1 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
