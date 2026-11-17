# Suite  2026-11-17T11:24:17+02:00

**ALL PASS** · 2 spec(s) × 2 repeat(s), 2 worker(s), 5.3 s wall-clock · commit `28a5506`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `modal-close` | **PASS** | 100% | modal_closed 2/2 | 2437 ms | 196 | 2 | 1796 | None |
| `add-remove-elements` | **PASS** | 100% | one_delete_left 2/2 | 2817 ms | 369 | 3 | 3044 | 0.98 |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 2470 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 2404 ms | 0 |  | `modal-close/02/result.json` |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 2863 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 2771 ms | 0 | Delete | `add-remove-elements/02/result.json` |
