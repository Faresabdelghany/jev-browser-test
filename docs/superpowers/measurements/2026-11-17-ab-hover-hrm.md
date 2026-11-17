# A/B: --hover

5 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--hover`. 2026-11-17T12:17:44

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x5 | employee_saved x5 | no | 0.86 | 0.90 | +0.040 | 12 / 11 | 17.7 / 15.3 |
| hrm-admin-add-user | user_listed x4, undetermined:low_confidence x1 | user_listed x5 | some runs | 0.88 | 0.91 | +0.030 | 22 / 24 | 31.4 / 29.4 |
| hrm-leave-assign | undetermined:low_confidence x2, leave_scheduled x2 (+1 environment) | leave_scheduled x3 (+2 environment) | some runs | 0.85 | 0.90 | +0.040 | 26 / 28 | 61.2 / 72.2 |
| hrm-login | dashboard_shown x5 | dashboard_shown x5 | no | 0.91 | 0.90 | -0.015 | 6 / 6 | 12.6 / 12.2 |
| hrm-pim-add-employee-list | employee_listed x5 | employee_listed x5 | no | 0.89 | 0.92 | +0.030 | 22 / 19 | 24.9 / 24.4 |

**0 spec(s) ended differently in every run, 2 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
