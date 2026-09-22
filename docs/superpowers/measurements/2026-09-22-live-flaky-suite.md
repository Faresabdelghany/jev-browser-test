# Suite  2026-09-22T15:51:29+03:00

**NOT ALL PASS** · 1 spec(s) × 5 repeat(s), 2 worker(s), 16.4 s wall-clock · commit `20833f2`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `notify-random` | **FLAKY** | 60% | action_successful 3/5, action_unsuccessful 2/5 | 5742 ms | 1444 | 4 | 4531 | 0.99 |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 6218 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 6143 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 4500 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |
| 4 | action_unsuccessful | bug | outcome | 4646 ms | 1 | Action unsuccesful, please try again | `notify-random/04/result.json` |
| 5 | action_successful | pass | passed | 5742 ms | 0 | Action successful | `notify-random/05/result.json` |

Open a trace only for: `notify-random` (flaky)
