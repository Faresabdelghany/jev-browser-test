# Suite five hrm example specs at 9edd768, 1 worker 2026-09-24T12:33:09+03:00

**NOT ALL PASS** · 5 spec(s) × 3 repeat(s), 1 worker(s), 1254.5 s wall-clock · commit `9edd768`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **UNDETERMINED (suggested: test_issue 2, none 1)** | 100% | undetermined 3/3 | 73237 ms | 3581 | 12 | 36394 | 0.65 |
| `hrm-admin-add-user` | **UNDETERMINED (suggested: test_issue 3)** | 100% | undetermined 3/3 | 102932 ms | 2742 | 9 | 47895 | 0.545 |
| `hrm-leave-assign` | **UNDETERMINED (suggested: test_issue 3)** | 100% | undetermined 3/3 | 100392 ms | 3160 | 10 | 49903 | 0.41 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 3/3 | 28292 ms | 1703 | 7 | 12984 | 0.85 |
| `hrm-pim-add-employee-list` | **UNDETERMINED (suggested: test_issue 3)** | 100% | undetermined 3/3 | 113849 ms | 4398 | 15 | 49677 | 0.615 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 68520 ms | 1 |  | `hrm-add-employee/01/result.json` |
| 2 | undetermined | - | low_confidence | 73237 ms | 1 |  | `hrm-add-employee/02/result.json` |
| 3 | undetermined | - | assert_failed | 75925 ms | 1 |  | `hrm-add-employee/03/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 96643 ms | 1 |  | `hrm-admin-add-user/01/result.json` |
| 2 | undetermined | - | low_confidence | 102932 ms | 1 |  | `hrm-admin-add-user/02/result.json` |
| 3 | undetermined | - | low_confidence | 104755 ms | 1 |  | `hrm-admin-add-user/03/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 100392 ms | 1 |  | `hrm-leave-assign/01/result.json` |
| 2 | undetermined | - | low_confidence | 119187 ms | 1 |  | `hrm-leave-assign/02/result.json` |
| 3 | undetermined | - | low_confidence | 95581 ms | 1 |  | `hrm-leave-assign/03/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 31816 ms | 0 | PIM | `hrm-login/01/result.json` |
| 2 | dashboard_shown | pass | passed | 27085 ms | 0 | PIM | `hrm-login/02/result.json` |
| 3 | dashboard_shown | pass | passed | 28292 ms | 0 | PIM | `hrm-login/03/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 126470 ms | 1 |  | `hrm-pim-add-employee-list/01/result.json` |
| 2 | undetermined | - | low_confidence | 113849 ms | 1 |  | `hrm-pim-add-employee-list/02/result.json` |
| 3 | undetermined | - | low_confidence | 89822 ms | 1 |  | `hrm-pim-add-employee-list/03/result.json` |

Open a trace only for: `hrm-add-employee` (undetermined), `hrm-admin-add-user` (undetermined), `hrm-leave-assign` (undetermined), `hrm-pim-add-employee-list` (undetermined)
