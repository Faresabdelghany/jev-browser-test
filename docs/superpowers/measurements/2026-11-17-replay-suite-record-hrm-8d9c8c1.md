# Suite 0.8.0 replay on, first run (hrm), 8d9c8c1 2026-11-17T15:46:03+02:00

**NOT ALL PASS** · 5 spec(s) × 1 repeat(s), 1 worker(s), 97.6 s wall-clock · commit `8d9c8c1`

Replay: 0 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **UNDETERMINED (suggested: test_issue 1)** | 100% | undetermined 1/1 | 17294 ms | 1598 | 7 | 28172 | 0.43 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 26243 ms | 4858 | 20 | 105558 | 0.825 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 26097 ms | 5224 | 23 | 127997 | 0.92 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 8392 ms | 3501 | 5 | 12253 | 0.95 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 19530 ms | 3924 | 18 | 101188 | 0.925 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 17294 ms | 1 |  | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 26243 ms | 0 | Jevtest Usertonfijtf | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 26097 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 8392 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 19530 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

Open a trace only for: `hrm-add-employee` (undetermined)
