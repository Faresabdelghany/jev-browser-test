# Suite  2026-09-24T16:30:09+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 491.7 s wall-clock · commit `b92b24f` · **6 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 3/3 | 15027 ms | 2798 | 10 | 43879 | 0.925 |
| `hrm-admin-add-user` | **UNDETERMINED (environment/setup failures 3/3)** | 0% | - | None ms | None | None | None | None |
| `hrm-leave-assign` | **UNDETERMINED (environment/setup failures 3/3)** | 0% | - | None ms | None | None | None | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 6737 ms | 1250 | 5 | 12607 | 0.9 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 23166 ms | 7116 | 22 | 117841 | 0.88 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 14865 ms | 0 | Jevtest Runnertlvegmge | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 15027 ms | 0 | Jevtest Runnertlveh0mr | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 15716 ms | 0 | Jevtest Runnertlvehfs1 | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | setup failure | - | error | 56833 ms | 2 | setup failed: RuntimeError: setup[12] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 45000ms exceeded. Call  | `hrm-admin-add-user/01/result.json` |
| 2 | setup failure | - | error | 57189 ms | 2 | setup failed: RuntimeError: setup[12] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 45000ms exceeded. Call  | `hrm-admin-add-user/02/result.json` |
| 3 | setup failure | - | error | 52312 ms | 2 | setup failed: RuntimeError: setup[10] (wait_for) failed: TimeoutError: Timeout 45000ms exceeded. ======================= | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | setup failure | - | error | 59036 ms | 2 | setup failed: RuntimeError: setup[12] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 45000ms exceeded. Call  | `hrm-leave-assign/01/result.json` |
| 2 | setup failure | - | error | 56596 ms | 2 | setup failed: RuntimeError: setup[12] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 45000ms exceeded. Call  | `hrm-leave-assign/02/result.json` |
| 3 | setup failure | - | error | 56896 ms | 2 | setup failed: RuntimeError: setup[12] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 45000ms exceeded. Call  | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 6417 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 6737 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 8557 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 39713 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 22636 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 23166 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-admin-add-user` (undetermined), `hrm-leave-assign` (undetermined)
