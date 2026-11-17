# A/B: --replay

5 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--replay`. 2026-11-17T15:41:50

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3 | employee_saved x3 | no | 0.86 | 0.90 | +0.040 | 11 / 1 | 18.0 / 13.1 |
| hrm-admin-add-user | user_listed x2 (+1 environment) | user_listed x3 | no | 0.83 | - | - | 20 / 1 | 32.2 / 23.8 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.88 | 0.76 | -0.120 ⚠ | 25 / 1 | 28.1 / 32.3 |
| hrm-login | dashboard_shown x3 | dashboard_shown x3 | no | 0.96 | - | - | 5 / 1 | 6.0 / 5.1 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x3 | no | 0.92 | - | - | 18 / 1 | 20.1 / 16.4 |

**0 spec(s) ended differently in every run, 0 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
