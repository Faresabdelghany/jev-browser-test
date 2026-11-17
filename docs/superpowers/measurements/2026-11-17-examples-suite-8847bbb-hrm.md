# Suite five hrm example specs at 8847bbb, 1 worker 2026-11-17T11:25:23+02:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 366.0 s wall-clock · commit `8847bbb`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **FLAKY** | 67% | employee_saved 2/3, employee_id_taken 1/3 | 24073 ms | 2748 | 13 | 52960 | 0.725 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 29449 ms | 4548 | 20 | 107722 | 0.865 |
| `hrm-leave-assign` | **UNDETERMINED (suggested: test_issue 3)** | 100% | undetermined 3/3 | 40728 ms | 6671 | 29 | 158820 | 0.85 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 5941 ms | 782 | 5 | 11564 | 0.95 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 19851 ms | 3930 | 18 | 99776 | 0.895 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 36804 ms | 0 | Jevtest Runnerton385mz | `hrm-add-employee/01/result.json` |
| 2 | employee_id_taken | bug | outcome | 14876 ms | 1 | Employee Id already exists | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 24073 ms | 0 | Jevtest Runnerton39kf5 | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 29449 ms | 0 | jevton3a8we | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 27388 ms | 0 | Jevtest Userton3b2u8 | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 32139 ms | 0 | jevton3bt0d | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 38977 ms | 1 |  | `hrm-leave-assign/01/result.json` |
| 2 | undetermined | - | low_confidence | 40728 ms | 1 |  | `hrm-leave-assign/02/result.json` |
| 3 | undetermined | - | low_confidence | 41895 ms | 1 |  | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 7558 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 5824 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 5941 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 19612 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 19851 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 20891 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-add-employee` (flaky), `hrm-leave-assign` (undetermined)
