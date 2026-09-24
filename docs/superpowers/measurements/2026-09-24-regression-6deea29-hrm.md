# Suite five hrm example specs at 6deea29, 1 worker, in a normal hour of the demo (login page 0.580125 / 0.702728 / 0.467947 s): busy confirmation looks run for navigation_timeout_ms 2026-09-24T14:42:19+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 419.9 s wall-clock · commit `6deea29`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 3/3 | 16047 ms | 3136 | 11 | 47867 | 0.9 |
| `hrm-admin-add-user` | **FLAKY** | 67% | undetermined 2/3, user_listed 1/3 | 39096 ms | 6511 | 21 | 119175 | 0.8 |
| `hrm-leave-assign` | **FLAKY** | 67% | leave_scheduled 2/3, undetermined 1/3 | 37381 ms | 7860 | 26 | 137318 | 0.86 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 7143 ms | 1282 | 5 | 11656 | 0.94 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 22880 ms | 6098 | 20 | 102809 | 0.84 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 17302 ms | 0 | Jevtest Runner | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 16047 ms | 0 | Personal Details | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 15685 ms | 0 | Jevtest Runner | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 30310 ms | 0 | jevtlv9k874 | `hrm-admin-add-user/01/result.json` |
| 2 | undetermined | - | low_confidence | 39096 ms | 1 |  | `hrm-admin-add-user/02/result.json` |
| 3 | undetermined | - | low_confidence | 41852 ms | 1 |  | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 37381 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | undetermined | - | low_confidence | 56905 ms | 1 |  | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 31630 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 7143 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 5851 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 8293 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 22880 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 20849 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 68605 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-admin-add-user` (flaky), `hrm-leave-assign` (flaky)
