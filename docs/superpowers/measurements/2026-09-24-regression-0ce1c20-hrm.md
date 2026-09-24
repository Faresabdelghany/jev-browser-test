# Suite five hrm example specs at 0ce1c20, 1 worker (login page 0.881129 0.638633 0.980043  s): the loading placeholder and the admin goal 2026-09-24T15:07:10+03:00

**ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 494.0 s wall-clock · commit `0ce1c20` · **2 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS (environment/setup failures 1/3)** | 100% | employee_saved 2/2 | 45088.5 ms | 5020.5 | 17.5 | 66038 | 0.867 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 3/3 | 38716 ms | 6366 | 21 | 106097 | 0.8 |
| `hrm-leave-assign` | **PASS (environment/setup failures 1/3)** | 100% | leave_scheduled 2/2 | 46936.5 ms | 7613 | 25 | 135724.5 | 0.85 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 6073 ms | 1192 | 5 | 12286 | 0.93 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 20161 ms | 5375 | 18 | 92504 | 0.88 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 59725 ms | 0 | Jevtest Runner | `hrm-add-employee/01/result.json` |
| 2 | setup failure | - | error | 45827 ms | 2 | setup failed: RuntimeError: setup[3] (wait_for) failed: TimeoutError: Timeout 40000ms exceeded. ======================== | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 30452 ms | 0 | Jevtest Runner | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 66107 ms | 0 | jevtlvaq0pj | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 38716 ms | 0 | jevtlvarut3 | `hrm-admin-add-user/02/result.json` |
| 3 | user_listed | pass | passed | 28555 ms | 0 | jevtlvasx57 | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 31100 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | setup failure | - | error | 51589 ms | 2 | setup failed: RuntimeError: setup[10] (wait_for) failed: TimeoutError: Timeout 45000ms exceeded. ======================= | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 62773 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 6073 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 6694 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 5772 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 20783 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 20161 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 19610 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |
