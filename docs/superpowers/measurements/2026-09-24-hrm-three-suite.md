# Suite three OrangeHRM specs at 8fea73d, one worker, clean export (round 3) 2026-09-24T05:23:11+03:00

**ALL PASS** · 3 spec(s) × 3 repeat(s), 1 worker(s), 243.0 s wall-clock · commit `8fea73d`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 33265 ms | 6601 | 19 | 98916 | 0.86 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 3/3 | 29707 ms | 7659 | 22 | 128612 | 0.87 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 18644 ms | 5016 | 16 | 84772 | 0.88 |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 33492 ms | 0 | jevtlujrw4c | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 33265 ms | 0 | jevtlujsu2i | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 31143 ms | 0 | jevtlujtrzd | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 30631 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 29707 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 27856 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 18644 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 18590 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 19694 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |
