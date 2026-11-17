# A/B: --settle=network

5 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--settle=network`. 2026-11-17T17:33:11

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3, undetermined:low_confidence x1, employee_id_taken x1 | undetermined:low_confidence x3, employee_saved x2 | some runs | 0.87 | 0.69 | -0.175 ⚠ | 12 / 6 | 19.5 / 12.7 |
| hrm-admin-add-user | user_listed x4, undetermined:low_confidence x1 | user_listed x5 | some runs | 0.84 | 0.86 | +0.020 | 24 / 21 | 39.3 / 39.6 |
| hrm-leave-assign | leave_scheduled x5 | leave_scheduled x5 | no | 0.88 | 0.90 | +0.020 | 25 / 19 | 34.5 / 42.5 |
| hrm-login | dashboard_shown x5 | dashboard_shown x5 | no | 0.92 | 0.94 | +0.015 | 6 / 6 | 9.5 / 11.1 |
| hrm-pim-add-employee-list | employee_listed x4, no_records x1 | employee_listed x4, suggestion_not_found x1 | some runs | 0.90 | 0.91 | +0.010 | 19 / 14 | 21.8 / 19.5 |

**0 spec(s) ended differently in every run, 3 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
