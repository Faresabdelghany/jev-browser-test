# A/B: --batch-fields

3 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--batch-fields`. 2026-11-17T16:20:35

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x5 | employee_saved x3, employee_id_taken x1, undetermined:low_confidence x1 | some runs | 0.84 | 0.86 | +0.015 | 12 / 10 | 23.1 / 19.0 |
| hrm-pim-add-employee-list | employee_listed x5 | employee_listed x5 | no | 0.92 | 0.90 | -0.020 | 18 / 17 | 20.2 / 19.8 |
| hrm-admin-add-user | user_listed x5 | user_listed x5 | no | 0.87 | 0.89 | +0.020 | 20 / 21 | 29.0 / 31.2 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
