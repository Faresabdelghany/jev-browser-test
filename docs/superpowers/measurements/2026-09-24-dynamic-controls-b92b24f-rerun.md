# Suite  2026-09-24T16:38:39+03:00

**NOT ALL PASS** · 1 spec(s) × 3 repeat(s), 1 worker(s), 30.9 s wall-clock · commit `b92b24f`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `dynamic-controls` | **FLAKY** | 67% | both_done 2/3, undetermined 1/3 | 7991 ms | 2199 | 9 | 12894 | 0.52 |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | low_confidence | 6803 ms | 1 |  | `dynamic-controls/01/result.json` |
| 2 | both_done | pass | passed | 16095 ms | 0 | It's enabled! | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 7991 ms | 0 | It's enabled! | `dynamic-controls/03/result.json` |

Open a trace only for: `dynamic-controls` (flaky)
