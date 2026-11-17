# A/B: --reuse-sessions --session-dir=runs/state/s4b-sessions-hrm

4 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--reuse-sessions --session-dir=runs/state/s4b-sessions-hrm`. 2026-11-17T17:48:46

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| hrm-add-employee | employee_saved x3 | employee_saved x3 | no | 0.85 | 0.82 | -0.025 | 13 / 14 | 23.8 / 21.1 |
| hrm-pim-add-employee-list | employee_listed x3 | employee_listed x2, employee_id_taken x1 | some runs | 0.90 | 0.89 | -0.005 | 19 / 19 | 20.5 / 18.8 |
| hrm-admin-add-user | user_listed x3 | user_listed x3 | no | 0.88 | 0.88 | +0.000 | 20 / 20 | 28.5 / 28.7 |
| hrm-leave-assign | leave_scheduled x3 | leave_scheduled x3 | no | 0.89 | 0.89 | +0.000 | 23 / 23 | 27.2 / 26.1 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
