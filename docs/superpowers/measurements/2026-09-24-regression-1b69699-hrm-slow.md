# Suite five hrm example specs at 1b69699, 1 worker, in a slow hour of the demo (login page 4.114028 / 2.769059 / 4.392862 s): the blank-layer deferral 2026-09-24T14:35:04+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 1121.3 s wall-clock · commit `1b69699`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **FLAKY** | 67% | employee_saved 2/3, undetermined 1/3 | 99586 ms | 5374 | 18 | 69600 | 0.82 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 152766 ms | 9628 | 30 | 152876 | 0.685 |
| `hrm-leave-assign` | **FLAKY** | 67% | leave_scheduled 2/3, undetermined 1/3 | 67541 ms | 8350 | 27 | 143831 | 0.86 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 6405 ms | 1198 | 5 | 12755 | 0.95 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 18957 ms | 4918 | 17 | 93957 | 0.83 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 104570 ms | 0 | Jevtest Runner | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 96168 ms | 0 | Jevtest Runner | `hrm-add-employee/02/result.json` |
| 3 | undetermined | - | done_unverified | 99586 ms | 1 |  | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 182337 ms | 0 | jevtlv8vnfr | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 152766 ms | 0 | jevtlv90q9b | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 144094 ms | 0 | jevtlv94ydp | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 161851 ms | 1 |  | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 67541 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 33738 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 5970 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 7089 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 6405 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 18662 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 18957 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 21483 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-add-employee` (flaky), `hrm-leave-assign` (flaky)
