# Suite three corrected specs at 9b43ae7, 2 workers 2026-11-17T11:26:36+02:00

**ALL PASS** · 3 spec(s) × 3 repeat(s), 2 worker(s), 20.0 s wall-clock · commit `9b43ae7`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `forgot-password` | **PASS** | 100% | email_sent 3/3 | 6072 ms | 582 | 4 | 4427 | 0.995 |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 3356 ms | 571 | 4 | 4033 | 0.66 |
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 3643 ms | 810 | 5 | 5862 | 0.96 |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 6214 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |
| 2 | email_sent | pass | passed | 6072 ms | 0 | Your e-mail's been sent! | `forgot-password/02/result.json` |
| 3 | email_sent | pass | passed | 3438 ms | 0 | Your e-mail's been sent! | `forgot-password/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3413 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 3356 ms | 0 |  | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 3347 ms | 0 |  | `modal-close/03/result.json` |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3643 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 4358 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 3459 ms | 0 | Delete | `add-remove-elements/03/result.json` |
