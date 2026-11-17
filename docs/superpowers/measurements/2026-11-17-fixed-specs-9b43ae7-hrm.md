# Suite two hrm specs after the spec fixes at 9b43ae7, 1 worker 2026-11-17T11:28:35+02:00

**NOT ALL PASS** · 2 spec(s) × 3 repeat(s), 1 worker(s), 138.8 s wall-clock · commit `9b43ae7`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 3/3 | 30030 ms | 5916 | 25 | 138567 | 0.87 |
| `hrm-add-employee` | **FLAKY** | 67% | employee_saved 2/3, undetermined 1/3 | 16831 ms | 2254 | 11 | 50214 | 0.87 |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 30030 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |
| 2 | leave_scheduled | pass | passed | 31849 ms | 0 | (1) Record Found | `hrm-leave-assign/02/result.json` |
| 3 | leave_scheduled | pass | passed | 26359 ms | 0 | (1) Record Found | `hrm-leave-assign/03/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 16787 ms | 0 | Jevtest Runnerton3m8qq | `hrm-add-employee/01/result.json` |
| 2 | undetermined | - | low_confidence | 16831 ms | 1 |  | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 16972 ms | 0 | Jevtest Runnerton3n6dy | `hrm-add-employee/03/result.json` |

Open a trace only for: `hrm-add-employee` (flaky)
