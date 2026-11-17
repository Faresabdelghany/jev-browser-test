# Suite 0.7.0 release check, 554b427, hrm 2026-11-17T14:07:22+02:00

**ALL PASS** · 5 spec(s) × 1 repeat(s), 1 worker(s), 112.5 s wall-clock · commit `554b427`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 20333 ms | 2702 | 13 | 54074 | 0.7 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 28846 ms | 4914 | 20 | 104974 | 0.87 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 35420 ms | 6314 | 26 | 146217 | 0.865 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 7542 ms | 1243 | 6 | 11945 | 0.88 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 20352 ms | 4611 | 19 | 96015 | 0.9 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 20333 ms | 0 | Jevtest Runnertonax57m | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 28846 ms | 0 | jevtonaxps6 | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 35420 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 7542 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 20352 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
