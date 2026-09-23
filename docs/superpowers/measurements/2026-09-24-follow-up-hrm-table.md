# Suite follow-up at 9139e22, clean export, one worker 2026-09-24T02:52:07+03:00

**ALL PASS** · 2 spec(s) × 3 repeat(s), 1 worker(s), 112.2 s wall-clock · commit `9139e22`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `hrm-add-employee` | **PASS** | 100% | employee_saved 3/3 | 20272 ms | 4830 | 10 | 47545 | 0.85 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 22778 ms | 1768 | 4 | 10035 | 0.4 |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 20272 ms | 0 | Jevtest Runner | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 21222 ms | 0 | Jevtest Runner | `hrm-add-employee/02/result.json` |
| 3 | employee_saved | pass | passed | 19034 ms | 0 | Personal Details | `hrm-add-employee/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 22778 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 5722 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 23173 ms | 0 |  | `table-sort-due/03/result.json` |
