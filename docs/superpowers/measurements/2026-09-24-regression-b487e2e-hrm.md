# Suite five hrm example specs at b487e2e, 1 worker, in a slow hour of the demo (login page 3-4 s) 2026-09-24T13:31:40+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 1178.1 s wall-clock · commit `b487e2e` · **1 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **UNDETERMINED (suggested: bug 1, none 2)** | 100% | undetermined 3/3 | 91914 ms | 5164 | 18 | 54695 | 0.775 |
| `hrm-admin-add-user` | **FLAKY (environment/setup failures 1/3)** | 50% | user_listed 1/2, undetermined 1/2 | 176020 ms | 8787 | 29 | 138245 | 0.675 |
| `hrm-leave-assign` | **FLAKY** | 67% | undetermined 2/3, leave_scheduled 1/3 | 131610 ms | 9169 | 28 | 146562 | 0.785 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 14340 ms | 1622 | 6 | 12173 | 0.875 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 3/3 | 20669 ms | 5264 | 18 | 92694 | 0.85 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 90945 ms | 1 |  | `hrm-add-employee/01/result.json` |
| 2 | undetermined | - | assert_failed | 91914 ms | 1 | Personal Details | `hrm-add-employee/02/result.json` |
| 3 | undetermined | - | assert_failed | 92434 ms | 1 | Personal Details | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | setup failure | - | error | 53597 ms | 2 | setup failed: RuntimeError: setup[9] (click) failed: TimeoutError: Locator.click: Timeout 8000ms exceeded. Call log: - w | `hrm-admin-add-user/01/result.json` |
| 2 | user_listed | pass | passed | 177829 ms | 0 | jevtlv5x65x | `hrm-admin-add-user/02/result.json` |
| 3 | undetermined | - | low_confidence | 174211 ms | 1 |  | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 162332 ms | 1 |  | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 131610 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | undetermined | - | low_confidence | 93906 ms | 1 |  | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 14340 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 16272 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 10859 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 20669 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |
| 2 | employee_listed | pass | passed | 20546 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/02/result.json` |
| 3 | employee_listed | pass | passed | 26639 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-admin-add-user` (flaky), `hrm-leave-assign` (flaky), `hrm-add-employee` (undetermined)
