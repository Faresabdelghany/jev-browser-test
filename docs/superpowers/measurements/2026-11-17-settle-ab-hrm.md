# A/B: --settle=network

5 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--settle=network`. 2026-11-17T16:40:54

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x5 | employee_saved x5 | no | 0.89 | 0.88 | -0.010 | 11 / 10 | 14.7 / 18.6 |
| hrm-admin-add-user | user_listed x3, undetermined:low_confidence x2 | user_listed x4 (+1 environment) | some runs | 0.84 | 0.83 | -0.010 | 22 / 19 | 36.9 / 36.4 |
| hrm-leave-assign | leave_scheduled x5 | leave_scheduled x5 | no | 0.88 | 0.90 | +0.020 | 24 / 19 | 28.5 / 29.2 |
| hrm-login | dashboard_shown x5 | dashboard_shown x5 | no | 0.96 | 0.95 | -0.010 | 5 / 5 | 5.7 / 5.4 |
| hrm-pim-add-employee-list | employee_listed x5 | employee_listed x5 | no | 0.89 | 0.95 | +0.060 | 20 / 14 | 23.5 / 24.0 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
