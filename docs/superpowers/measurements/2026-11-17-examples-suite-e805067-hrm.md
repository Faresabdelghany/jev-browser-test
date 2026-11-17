# Suite five hrm example specs at e805067 (0.6.0), 1 worker 2026-11-17T12:35:42+02:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 414.4 s wall-clock · commit `e805067`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **FLAKY** | 67% | employee_saved 2/3, undetermined 1/3 | 52043 ms | 3474 | 17 | 61550 | 0.645 |
| `hrm-admin-add-user` | **FLAKY** | 67% | user_listed 2/3, undetermined 1/3 | 31023 ms | 4716 | 22 | 114268 | 0.86 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 3/3 | 27166 ms | 5518 | 23 | 130352 | 0.88 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 6310 ms | 783 | 5 | 11717 | 0.95 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 19296 ms | 3903 | 18 | 100173 | 0.905 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 81455 ms | 1 |  | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 52043 ms | 0 | Jevtest Runnerton6i9wf | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 28731 ms | 0 | Jevtest Runnerton6jpi4 | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 30871 ms | 1 |  | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 31023 ms | 0 | Jevtest Userton6ldk8 | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 33937 ms | 0 | jevton6m8bz | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 27166 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 25692 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 27612 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 6310 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 5814 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 6521 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 19296 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 19386 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 18559 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-add-employee` (flaky), `hrm-admin-add-user` (flaky)
