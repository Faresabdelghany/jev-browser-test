# Suite after the real-app session (eecf79e) 2026-09-22T14:41:57+03:00

**ALL PASS** · 2 spec(s) × 5 repeat(s), 4 worker(s), 19.4 s wall-clock · commit `eecf79e`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `smoke-login` | **PASS** | 100% | logged_in 5/5 | 6619 ms | 2017 | 6 | 8932 | 0.95 |
| `smoke-login-badpw` | **PASS** | 100% | bad_credentials 5/5 | 6498 ms | 2021 | 6 | 9774 | 0.9 |

## `smoke-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_in | pass | passed | 6626 ms | 0 | You logged into a secure area! | `smoke-login/01/result.json` |
| 2 | logged_in | pass | passed | 6612 ms | 0 | You logged into a secure area! | `smoke-login/02/result.json` |
| 3 | logged_in | pass | passed | 6619 ms | 0 | You logged into a secure area! | `smoke-login/03/result.json` |
| 4 | logged_in | pass | passed | 6700 ms | 0 | You logged into a secure area! | `smoke-login/04/result.json` |
| 5 | logged_in | pass | passed | 6421 ms | 0 | You logged into a secure area! | `smoke-login/05/result.json` |

## `smoke-login-badpw`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bad_credentials | pass | passed | 6498 ms | 0 | Your password is invalid! | `smoke-login-badpw/01/result.json` |
| 2 | bad_credentials | pass | passed | 6506 ms | 0 | Your password is invalid! | `smoke-login-badpw/02/result.json` |
| 3 | bad_credentials | pass | passed | 6757 ms | 0 | Your password is invalid! | `smoke-login-badpw/03/result.json` |
| 4 | bad_credentials | pass | passed | 6330 ms | 0 | Your password is invalid! | `smoke-login-badpw/04/result.json` |
| 5 | bad_credentials | pass | passed | 6293 ms | 0 | Your password is invalid! | `smoke-login-badpw/05/result.json` |
