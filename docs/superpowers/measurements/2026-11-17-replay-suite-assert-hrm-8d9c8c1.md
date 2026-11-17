# Suite 0.8.0 replay, rerun, verify assert (hrm), 8d9c8c1 2026-11-17T15:58:21+02:00

**ALL PASS** · 5 spec(s) × 1 repeat(s), 1 worker(s), 75.8 s wall-clock · commit `8d9c8c1`

Replay: 5 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 12925 ms | 290 | 1 | 7961 | None |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 21386 ms | 0 | 0 | 0 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 21468 ms | 0 | 0 | 0 | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 4381 ms | 0 | 0 | 0 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 15581 ms | 0 | 0 | 0 | None |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved (replayed 5/5) | pass | passed | 12925 ms | 0 | Jevtest Runnertong3571 | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 12/12) | pass | passed | 21386 ms | 0 |  | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 15/15) | pass | passed | 21468 ms | 0 |  | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 4381 ms | 0 |  | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 9/9) | pass | passed | 15581 ms | 0 |  | `hrm-pim-add-employee-list/01/result.json` |
