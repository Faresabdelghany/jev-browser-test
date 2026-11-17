# A/B: --replay --reuse-sessions

3 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--replay --reuse-sessions`. 2026-11-17T18:36:47

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| login-logout | logged_out x5 | logged_out x5 | no | 0.98 | - | - | 6 / 1 | 4.7 / 3.5 |
| shop-checkout | order_complete x5 | order_complete x5 | no | 0.99 | - | - | 10 / 1 | 5.2 / 2.9 |
| hrm-pim-add-employee-list | employee_listed x5 | employee_listed x5 | no | 0.90 | - | - | 18 / 1 | 19.7 / 14.7 |

**0 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it the default, as strong as the specs are varied and the repeats many.
