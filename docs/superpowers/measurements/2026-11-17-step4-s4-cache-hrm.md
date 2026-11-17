# A/B: --http-cache --http-cache-dir=runs/state/s4-cache-hrm

5 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--http-cache --http-cache-dir=runs/state/s4-cache-hrm`. 2026-11-17T17:03:38

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x2, undetermined:low_confidence x1 | employee_saved x2, employee_id_taken x1 | some runs | 0.89 | 0.88 | -0.010 | 11 / 12 | 14.9 / 21.3 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.82 | 0.88 | +0.060 | 24 / 23 | 39.1 / 30.1 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.86 | 0.88 | +0.015 | 25 / 26 | 33.0 / 33.2 |
| hrm-login | dashboard_shown x3 | dashboard_shown x3 | no | 0.94 | 0.93 | -0.020 | 5 / 5 | 5.8 / 4.8 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x2, employee_id_taken x1 | some runs | 0.93 | 0.92 | -0.010 | 18 / 17 | 19.1 / 18.9 |

**0 spec(s) ended differently in every run, 2 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
