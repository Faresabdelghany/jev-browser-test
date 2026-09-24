# Suite three OrangeHRM specs at 989ab2f, one worker, clean export (round 2) 2026-09-24T05:13:42+03:00

**NOT ALL PASS** · 3 spec(s) × 3 repeat(s), 1 worker(s), 272.1 s wall-clock · commit `989ab2f`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 26471 ms | 6024 | 18 | 98079 | 0.855 |
| `hrm-leave-assign` | **UNDETERMINED (suggested: test_issue 3)** | 100% | undetermined 3/3 | 42729 ms | 7813 | 19 | 113616 | 0.705 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 19240 ms | 5188 | 16 | 85438 | 0.88 |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 29008 ms | 0 | jevtlujbaio | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 26444 ms | 0 | jevtlujc33l | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 26471 ms | 0 | Jevtest Usertlujctre | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 41184 ms | 1 |  | `hrm-leave-assign/01/result.json` |
| 2 | undetermined | - | low_confidence | 42729 ms | 1 |  | `hrm-leave-assign/02/result.json` |
| 3 | undetermined | - | low_confidence | 50611 ms | 1 |  | `hrm-leave-assign/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 19498 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 16859 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 19240 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-leave-assign` (undetermined)
