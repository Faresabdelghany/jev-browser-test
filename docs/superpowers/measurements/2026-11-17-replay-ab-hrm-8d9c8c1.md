# A/B: --replay

5 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--replay`. 2026-11-17T15:55:45

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3 | employee_saved x2, employee_id_taken x1 | some runs | 0.84 | 0.81 | -0.030 | 12 / 10 | 17.3 / 13.4 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.87 | - | - | 21 / 1 | 30.2 / 23.7 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.87 | 0.86 | -0.010 | 23 / 1 | 27.9 / 21.4 |
| hrm-login | dashboard_shown x3 | dashboard_shown x3 | no | 0.95 | - | - | 5 / 1 | 5.9 / 5.3 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x3 | no | 0.89 | - | - | 17 / 1 | 18.9 / 17.1 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
