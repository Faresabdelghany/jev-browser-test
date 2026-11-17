# A/B: --shadow-dom

5 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--shadow-dom`. 2026-11-17T11:39:58

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x2, undetermined:low_confidence x1 | employee_saved x3 | some runs | 0.65 | 0.81 | +0.160 | 13 / 14 | 22.1 / 24.1 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.88 | 0.87 | -0.010 | 22 / 20 | 31.9 / 27.2 |
| hrm-leave-assign | leave_scheduled x2, undetermined:low_confidence x1 | leave_scheduled x3 | some runs | 0.88 | 0.88 | +0.000 | 26 / 24 | 32.8 / 27.5 |
| hrm-login | dashboard_shown x3 | dashboard_shown x3 | no | 0.95 | 0.94 | -0.010 | 5 / 6 | 5.8 / 6.2 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x2, employee_id_taken x1 | some runs | 0.89 | 0.90 | +0.010 | 17 / 18 | 19.0 / 19.0 |

**0 spec(s) ended differently in every run, 3 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
