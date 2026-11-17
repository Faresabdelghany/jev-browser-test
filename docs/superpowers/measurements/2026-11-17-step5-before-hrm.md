# Suite 0.7.0: 5 hrm, 1 worker 2026-11-17T17:56:05+02:00

**ALL PASS** · 5 spec(s) × 1 repeat(s), 1 worker(s), 96.5 s wall-clock · commit `1fa29a9`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 17267 ms | 2360 | 10 | 49270 | 0.925 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 27120 ms | 4364 | 19 | 105457 | 0.87 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 27467 ms | 5455 | 23 | 133518 | 0.89 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 5675 ms | 768 | 5 | 12398 | 0.94 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 18961 ms | 3948 | 17 | 98180 | 0.92 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 17267 ms | 0 | Jevtest Runnertonlitpx | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 27120 ms | 0 | jevtonljax9 | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 27467 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 5675 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 18961 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
