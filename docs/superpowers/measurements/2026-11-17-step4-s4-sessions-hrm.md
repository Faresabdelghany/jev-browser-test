# A/B: --reuse-sessions --session-dir=runs/state/s4-sessions-hrm

4 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--reuse-sessions --session-dir=runs/state/s4-sessions-hrm`. 2026-11-17T16:52:01

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3 | employee_saved x2, undetermined:low_confidence x1 | some runs | 0.90 | 0.87 | -0.030 | 11 / 11 | 20.2 / 15.8 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x3 | no | 0.93 | 0.89 | -0.035 | 21 / 20 | 26.4 / 22.9 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.84 | 0.84 | +0.000 | 22 / 23 | 34.5 / 30.7 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.89 | 0.88 | -0.010 | 25 / 26 | 36.1 / 35.3 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
