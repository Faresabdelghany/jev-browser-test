# Suite three OrangeHRM specs at f06f818, one worker, clean export 2026-09-24T05:05:27+03:00

**NOT ALL PASS** · 3 spec(s) × 3 repeat(s), 1 worker(s), 229.3 s wall-clock · commit `f06f818`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 27438 ms | 5987 | 18 | 102971 | 0.85 |
| `hrm-leave-assign` | **FLAKY** | 67% | leave_scheduled 2/3, undetermined 1/3 | 28255 ms | 7671 | 23 | 136685 | 0.79 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 19157 ms | 5568 | 17 | 97623 | 0.86 |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 28019 ms | 0 | jevtluiyqea | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 26419 ms | 0 | jevtluizi0m | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 27438 ms | 0 | jevtluj09yp | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 27376 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | undetermined | - | low_confidence | 33104 ms | 1 |  | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 28255 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 20622 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 18896 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 19157 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-leave-assign` (flaky)
