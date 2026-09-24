# Suite five hrm example specs at 6f9c5be, 1 worker, as the demo recovered (login page 0.8-2 s) 2026-09-24T13:55:47+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 860.7 s wall-clock · commit `6f9c5be`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 3/3 | 20388 ms | 3812 | 13 | 49522 | 0.93 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 32993 ms | 6402 | 21 | 110440 | 0.83 |
| `hrm-leave-assign` | **FLAKY** | 67% | leave_scheduled 2/3, undetermined 1/3 | 40868 ms | 7779 | 26 | 135977 | 0.835 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 31294 ms | 1967 | 7 | 13000 | 0.85 |
| `hrm-pim-add-employee-list` | **FLAKY** | 67% | undetermined 2/3, app_error 1/3 | 131451 ms | 7972 | 27 | 95893 | 0.78 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 19472 ms | 0 | Personal Details | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 27799 ms | 0 | Jevtest Runner | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 20388 ms | 0 | Personal Details | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 31172 ms | 0 | jevtlv72ypg | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 38504 ms | 0 | jevtlv73t68 | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 32993 ms | 0 | jevtlv74w0y | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 40868 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 31602 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | undetermined | - | low_confidence | 134418 ms | 1 |  | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 30330 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 31294 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 45182 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | app_error | bug | outcome | 91054 ms | 1 | live message: Error Invalid Parameter | `hrm-pim-add-employee-list/01/result.json` |
| 2 | undetermined | - | budget_exhausted | 154122 ms | 1 |  | `hrm-pim-add-employee-list/02/result.json` |
| 3 | undetermined | - | budget_exhausted | 131451 ms | 1 |  | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-leave-assign` (flaky), `hrm-pim-add-employee-list` (flaky)
