# Suite  2026-09-24T16:37:59+03:00

**ALL PASS** · 2 spec(s) × 3 repeat(s), 1 worker(s), 169.5 s wall-clock · commit `152a7f5`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 26769 ms | 5352 | 18 | 99172 | 0.83 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 3/3 | 28461 ms | 6742 | 23 | 136290 | 0.85 |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 27178 ms | 0 |  | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 26769 ms | 0 | jevtlvf3ddg | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 26590 ms | 0 | jevtlvf44la | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 27479 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 28461 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 32952 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |
