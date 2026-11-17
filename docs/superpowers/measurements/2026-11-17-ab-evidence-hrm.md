# A/B: --evidence=failures

5 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--evidence=failures`. 2026-11-17T11:50:57

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3 | employee_saved x3 | no | 0.89 | 0.92 | +0.025 | 11 / 10 | 14.9 / 14.4 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.84 | 0.86 | +0.020 | 22 / 20 | 33.9 / 33.7 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.87 | 0.87 | +0.000 | 25 / 23 | 29.7 / 27.9 |
| hrm-login | dashboard_shown x3 | dashboard_shown x3 | no | 0.92 | 0.92 | +0.005 | 6 / 5 | 7.1 / 9.6 |
| hrm-pim-add-employee-list | employee_listed x2, suggestion_not_found x1 | employee_listed x3 | some runs | 0.89 | 0.87 | -0.020 | 18 / 17 | 19.7 / 23.1 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
