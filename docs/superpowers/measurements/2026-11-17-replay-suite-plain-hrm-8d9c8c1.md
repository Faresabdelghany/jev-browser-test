# Suite 0.8.0 without replay (hrm), 8d9c8c1 2026-11-17T16:00:53+02:00

**NOT ALL PASS** · 5 spec(s) × 1 repeat(s), 1 worker(s), 152.1 s wall-clock · commit `8d9c8c1` · **1 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 14165 ms | 2071 | 10 | 44235 | 0.92 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 44759 ms | 6204 | 26 | 131637 | 0.855 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 40530 ms | 6507 | 25 | 143025 | 0.87 |
| `hrm-login` | **UNDETERMINED (environment/setup failures 1/1)** | 0% | - | None ms | None | None | None | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 20427 ms | 4013 | 17 | 99555 | 0.9 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 14165 ms | 0 | Jevtest Runnertong59kv | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 44759 ms | 0 | jevtong5nad | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 40530 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | setup failure | - | error | 32253 ms | 2 | setup failed: RuntimeError: setup[0] (wait_for) failed: TimeoutError: Locator.wait_for: Timeout 30000ms exceeded. Call l | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 20427 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

Open a trace only for: `hrm-login` (undetermined)
